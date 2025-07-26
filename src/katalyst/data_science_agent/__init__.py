"""
Data Science Agent for Katalyst

A specialized agent for data analysis, exploration, and modeling tasks.
Uses the same architecture as the coding agent (planner, executor, replanner)
but with tools and prompts optimized for data science workflows.
"""

from .graph import build_data_science_graph

__all__ = ["build_data_science_graph"]