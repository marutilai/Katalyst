import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "app"))
from katalyst.app.playbook_navigator import PlaybookNavigator


@pytest.fixture(scope="module")
def navigator():
    return PlaybookNavigator()


def test_load_playbooks(navigator):
    playbooks = navigator.list_available_playbooks()
    assert len(playbooks) > 0
    assert any(pb.title for pb in playbooks)


def test_search_playbooks(navigator):
    results = navigator.search_playbooks("init")
    assert (
        results
    ), "Should find at least one playbook with 'init' in title or description."
    assert any(
        "init" in pb.title.lower()
        or (pb.description and "init" in pb.description.lower())
        for pb in results
    )


def test_get_playbook_by_id(navigator):
    playbooks = navigator.list_available_playbooks()
    playbook_id = playbooks[0].playbook_id
    playbook = navigator.get_playbook_by_id(playbook_id)
    assert playbook is not None
    assert playbook.metadata.playbook_id == playbook_id
