from typing import List, Optional, Dict
from pathlib import Path
import re
import bm25s
from pydantic import BaseModel, Field
import os
from datetime import datetime
from katalyst.app.config import KATALYST_DIR

# Directory where all playbook markdown files are stored (recursively searched)
PLAYBOOKS_HUB_DIR = Path(__file__).parent.parent / "playbook_hub"
KATALYST_DIR.mkdir(exist_ok=True)


class PlaybookMetadata(BaseModel):
    """
    Stores metadata for a playbook, such as its ID, title, description, agent type, and tags.
    Used for search and listing without loading full content.
    """

    playbook_id: str = Field(
        ..., description="Unique identifier (usually filename stem)"
    )
    title: str = Field(..., description="Title of the playbook (from markdown)")
    description: str = Field(..., description="Short description (from markdown)")
    agent_type: Optional[str] = Field(
        None, description="Type of agent this playbook is for"
    )
    tags: List[str] = Field(
        default_factory=list, description="Tags for filtering/search"
    )


class Playbook(BaseModel):
    """
    Stores the full playbook, including its metadata and markdown content.
    """

    metadata: PlaybookMetadata = Field(..., description="PlaybookMetadata object")
    content_md: str = Field(..., description="Full markdown content of the playbook")


class PlaybookNavigator:
    """
    Loads, indexes, and enables search/retrieval of playbooks from PLAYBOOKS_HUB_DIR.
    Uses BM25 (via bm25s) for fast, high-quality search over playbook titles and descriptions.
    Persists the BM25 index in .katalyst for fast reloads.
    """

    def __init__(self, playbooks_dir: Path = PLAYBOOKS_HUB_DIR):
        self.playbooks_dir = playbooks_dir
        self.playbooks_metadata: List[
            PlaybookMetadata
        ] = []  # List of all playbook metadata
        self.playbook_content_map: Dict[
            str, Playbook
        ] = {}  # Map from playbook_id to Playbook
        self.corpus: List[
            str
        ] = []  # List of doc strings for BM25 (title + description)
        self.bm25 = None  # BM25 index object
        self._load_and_index_playbooks(force_reindex=False)

    def _get_latest_bm25_index_path(self):
        files = list(KATALYST_DIR.glob("bm25_index_*"))
        if not files:
            return None
        return max(files, key=os.path.getctime)

    def _save_bm25_index(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        index_path = KATALYST_DIR / f"bm25_index_{timestamp}"
        self.bm25.save(str(index_path), corpus=self.corpus)
        return index_path

    def _load_and_index_playbooks(self, force_reindex: bool = False):
        """
        Loads playbooks and BM25 index from disk if available, or builds and saves if not or if force_reindex is True.
        """
        # Always load playbooks/metadata/corpus from markdown files
        self.playbooks_metadata.clear()
        self.playbook_content_map.clear()
        self.corpus.clear()
        for md_file in self.playbooks_dir.rglob("*.md"):
            playbook_id = md_file.stem
            content = md_file.read_text(encoding="utf-8")
            title = self._extract_title(content) or playbook_id
            description = self._extract_description(content)
            agent_type = self._extract_agent_type(md_file)
            metadata = PlaybookMetadata(
                playbook_id=playbook_id,
                title=title,
                description=description or "No description provided.",
                agent_type=agent_type,
                tags=[],
            )
            playbook = Playbook(metadata=metadata, content_md=content)
            self.playbooks_metadata.append(metadata)
            self.playbook_content_map[playbook_id] = playbook
            doc = f"{title}\n{description or ''}"
            self.corpus.append(doc)
        # Try to load BM25 index from disk unless force_reindex is True
        index_path = self._get_latest_bm25_index_path() if not force_reindex else None
        if index_path:
            self.bm25 = bm25s.BM25.load(str(index_path), load_corpus=True)
            self.corpus = self.bm25.corpus  # ensure corpus is in sync
        else:
            self.corpus_tokens = bm25s.tokenize(self.corpus, stopwords="en")
            self.bm25 = bm25s.BM25()
            self.bm25.index(self.corpus_tokens)
            self._save_bm25_index()

    def _extract_title(self, content: str) -> Optional[str]:
        """
        Extract the first markdown H1 (# Title) as the playbook title.
        """
        match = re.search(r"^# (.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _extract_description(self, content: str) -> Optional[str]:
        """
        Extract the first 'Description:' line as the playbook description.
        """
        match = re.search(r"^Description:\s*(.+)$", content, re.MULTILINE)
        return match.group(1).strip() if match else None

    def _extract_agent_type(self, md_file: Path) -> Optional[str]:
        """
        Optionally infer agent type from directory structure (e.g., playbook_hub/coding_agent/)
        """
        parts = md_file.parts
        if "playbook_hub" in parts:
            idx = parts.index("playbook_hub")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return None

    def search_playbooks(
        self, query: str, agent_type: Optional[str] = None, top_k: int = 5
    ) -> List[PlaybookMetadata]:
        """
        Search playbooks using BM25 over title+description. Returns top_k PlaybookMetadata objects.
        If agent_type is specified, only returns playbooks for that agent type.
        Handles small corpora by setting k = min(top_k, corpus size).
        """
        k = min(top_k, len(self.playbooks_metadata))
        if k == 0:
            return []
        query_tokens = bm25s.tokenize([query], stopwords="en")
        results, scores = self.bm25.retrieve(query_tokens, k=k)
        found = []
        for idx in results[0]:
            # Handle both integer indices and dict results
            if isinstance(idx, dict) and "id" in idx:
                idx = idx["id"]
            meta = self.playbooks_metadata[idx]
            if agent_type and meta.agent_type != agent_type:
                continue
            found.append(meta)
        return found

    def get_playbook_by_id(self, playbook_id: str) -> Optional[Playbook]:
        """
        Retrieve the full Playbook object (metadata + markdown content) by its ID.
        """
        return self.playbook_content_map.get(playbook_id)

    def list_available_playbooks(
        self, agent_type: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> List[PlaybookMetadata]:
        """
        List all available playbooks, optionally filtered by agent_type or tags.
        Returns PlaybookMetadata objects only (not full content).
        """
        results = []
        for meta in self.playbooks_metadata:
            if agent_type and meta.agent_type != agent_type:
                continue
            if tags and not set(tags).intersection(set(meta.tags)):
                continue
            results.append(meta)
        return results
