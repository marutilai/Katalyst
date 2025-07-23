"""
Supervisor for routing between coding and data science agents.

The supervisor intelligently routes user requests to the appropriate agent
based on the nature of the task.
"""

from .supervisor import build_supervisor_graph

__all__ = ["build_supervisor_graph"]