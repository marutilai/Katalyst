"""Fuzzy matching utilities for finding similar text in files."""

from typing import Optional, Tuple
from thefuzz import fuzz
from katalyst.katalyst_core.utils.logger import get_logger


def find_fuzzy_match_in_lines(
    lines: list[str],
    search_lines: list[str],
    start_line: int,
    buffer_size: int = 20,
    threshold: int = 95
) -> Optional[Tuple[int, float]]:
    """
    Find the best fuzzy match for search_lines within a buffer around start_line.
    
    Args:
        lines: List of file lines to search in
        search_lines: List of lines to search for (without newlines)
        start_line: Line number to start searching from (1-based)
        buffer_size: Number of lines to search above and below start_line
        threshold: Minimum similarity score (0-100) to accept a match
    
    Returns:
        (matched_line_index, similarity_score) if a match is found above threshold
        None if no match found
    """
    logger = get_logger()
    
    # Handle empty search
    if not search_lines:
        return None
        
    search_text = "\n".join(search_lines)
    best_score = 0
    best_index = -1
    
    # Calculate search range
    min_line = max(0, start_line - 1 - buffer_size)
    max_line = min(len(lines), start_line - 1 + buffer_size + len(search_lines))
    
    # Handle invalid range
    if min_line >= len(lines) or max_line <= min_line:
        return None
    
    # Search within the buffer
    for i in range(min_line, max_line - len(search_lines) + 1):
        # Extract the candidate text
        candidate_lines = [line.rstrip("\r\n") for line in lines[i:i + len(search_lines)]]
        candidate_text = "\n".join(candidate_lines)
        
        # Calculate similarity
        score = fuzz.ratio(search_text, candidate_text)
        
        # Track the best match
        if score > best_score:
            best_score = score
            best_index = i
    
    # Log the search results
    logger.debug(
        f"Fuzzy search: best score={best_score} at line {best_index + 1}, "
        f"search range=[{min_line + 1}, {max_line}], threshold={threshold}"
    )
    
    # Return the best match if it meets the threshold
    if best_score >= threshold:
        return (best_index, best_score)
    
    return None


def find_fuzzy_match_in_text(
    text: str,
    search_text: str,
    start_pos: int = 0,
    window_size: int = 1000,
    threshold: int = 95
) -> Optional[Tuple[int, int, float]]:
    """
    Find the best fuzzy match for search_text within a window around start_pos.
    
    Args:
        text: Text to search in
        search_text: Text to search for
        start_pos: Character position to start searching from
        window_size: Number of characters to search before and after start_pos
        threshold: Minimum similarity score (0-100) to accept a match
    
    Returns:
        (start_pos, end_pos, similarity_score) if a match is found above threshold
        None if no match found
    """
    if not search_text:
        return None
    
    search_len = len(search_text)
    best_score = 0
    best_start = -1
    
    # Calculate search range
    min_pos = max(0, start_pos - window_size)
    max_pos = min(len(text), start_pos + window_size + search_len)
    
    # Search within the window
    for i in range(min_pos, max_pos - search_len + 1):
        candidate = text[i:i + search_len]
        score = fuzz.ratio(search_text, candidate)
        
        if score > best_score:
            best_score = score
            best_start = i
    
    # Return the best match if it meets the threshold
    if best_score >= threshold:
        return (best_start, best_start + search_len, best_score)
    
    return None