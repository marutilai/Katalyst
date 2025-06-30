"""
Action Trace Summarizer Module

Provides utilities to compress action traces (scratchpad) while preserving critical information
for the ReAct agent. Uses LLM to create concise summaries of tool interactions.
"""

from typing import List, Tuple, Optional
from langchain_core.agents import AgentAction
from katalyst.katalyst_core.services.llms import get_llm_client, get_llm_params
from katalyst.katalyst_core.utils.logger import get_logger

logger = get_logger()


class ActionTraceSummarizer:
    """
    Summarizes action traces to prevent scratchpad bloat while preserving essential context.
    """
    
    def __init__(self, component: str = "execution"):
        """
        Initialize the action trace summarizer.
        
        Args:
            component: LLM component to use (default: execution for speed)
        """
        self.component = component
        
    def summarize_action_trace(
        self,
        action_trace: List[Tuple[AgentAction, str]], 
        keep_last_n: int = 5,
        max_chars: int = 5000
    ) -> str:
        """
        Summarize an action trace while preserving critical tool interactions.
        
        Args:
            action_trace: List of (AgentAction, observation) tuples
            keep_last_n: Number of recent actions to keep in full detail
            max_chars: Maximum character count before triggering summarization
            
        Returns:
            Formatted scratchpad string with summary and recent actions
        """
        if not action_trace:
            return ""
            
        # Convert to formatted string first to check size
        full_scratchpad = self._format_action_trace(action_trace)
        
        # Don't summarize if not enough actions to make it worthwhile
        if len(action_trace) <= keep_last_n:
            return full_scratchpad
            
        # If max_chars is very low (like 1), it's a forced summarization
        force_summarization = max_chars < 100
        
        # Otherwise check size thresholds
        if not force_summarization:
            # Don't summarize if already small
            if len(full_scratchpad) <= max_chars:
                return full_scratchpad
            
            # Don't attempt summarization on traces smaller than 10KB - overhead not worth it
            MIN_SIZE_FOR_SUMMARY = 10000
            if len(full_scratchpad) < MIN_SIZE_FOR_SUMMARY:
                # Just truncate to last N actions if over threshold
                return self._format_action_trace(action_trace[-keep_last_n:])
            
        # Split into actions to summarize and actions to keep
        actions_to_summarize = action_trace[:-keep_last_n]
        actions_to_keep = action_trace[-keep_last_n:]
        
        # For very large traces, be more aggressive
        if len(full_scratchpad) > 50000:
            # Keep fewer recent actions for very large traces
            keep_last_n = min(3, keep_last_n)
            actions_to_summarize = action_trace[:-keep_last_n]
            actions_to_keep = action_trace[-keep_last_n:]
        
        logger.info(f"[ACTION_TRACE_SUMMARIZER] Summarizing {len(actions_to_summarize)} actions, keeping {len(actions_to_keep)} recent")
        
        # Log details about what's being summarized
        summarize_size = len(self._format_action_trace(actions_to_summarize))
        keep_size = len(self._format_action_trace(actions_to_keep))
        logger.debug(f"[ACTION_TRACE_SUMMARIZER] Size to summarize: {summarize_size} chars, size to keep: {keep_size} chars")
        
        # Create the summary
        target_reduction = 0.7 if len(full_scratchpad) > 50000 else 0.5
        summary = self._create_summary(actions_to_summarize, target_reduction=target_reduction)
        
        if not summary:
            logger.warning("[ACTION_TRACE_SUMMARIZER] Summary generation failed, returning truncated trace")
            return self._format_action_trace(actions_to_keep)
        
        logger.debug(f"[ACTION_TRACE_SUMMARIZER] Summary size: {len(summary)} chars (target reduction: {int(target_reduction*100)}%)")
        
        # Build the compressed scratchpad
        compressed_parts = [
            "[PREVIOUS ACTIONS SUMMARY]",
            summary,
            "[END OF SUMMARY]",
            "",
            "Recent actions and observations:",
            self._format_action_trace(actions_to_keep)
        ]
        
        compressed_scratchpad = "\n".join(compressed_parts)
        
        # If compression didn't help, just return truncated trace
        if len(compressed_scratchpad) >= len(full_scratchpad) * 0.9:
            logger.warning("[ACTION_TRACE_SUMMARIZER] Summary not effective, using truncated trace instead")
            return self._format_action_trace(actions_to_keep)
        
        # Log compression stats
        original_size = len(full_scratchpad)
        compressed_size = len(compressed_scratchpad)
        reduction = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        logger.info(f"[ACTION_TRACE_SUMMARIZER] Compressed {original_size} chars to {compressed_size} chars ({reduction:.1f}% reduction)")
        
        return compressed_scratchpad
    
    def _format_action_trace(self, action_trace: List[Tuple[AgentAction, str]]) -> str:
        """Format action trace into scratchpad string."""
        formatted_actions = []
        for action, obs in action_trace:
            # Truncate very long observations to prevent bloat
            if len(obs) > 1000:
                obs = obs[:997] + "..."
            formatted_actions.append(
                f"Previous Action: {action.tool}\nPrevious Action Input: {action.tool_input}\nObservation: {obs}"
            )
        return "\n".join(formatted_actions)
    
    def _create_summary(self, actions: List[Tuple[AgentAction, str]], target_reduction: float = 0.5) -> Optional[str]:
        """Create a concise summary of tool interactions."""
        
        # Group actions by tool type for more efficient summarization
        tool_groups = {}
        for action, observation in actions:
            tool_name = action.tool
            if tool_name not in tool_groups:
                tool_groups[tool_name] = []
            tool_groups[tool_name].append((action.tool_input, observation[:200]))  # Truncate long observations
        
        # Log summary of what's being compressed
        tool_summary = ", ".join([f"{tool}({len(calls)})" for tool, calls in tool_groups.items()])
        logger.debug(f"[ACTION_TRACE_SUMMARIZER] Compressing actions: {tool_summary}")
        
        # Format grouped actions more concisely
        formatted_groups = []
        for tool, calls in tool_groups.items():
            if len(calls) == 1:
                inp, obs = calls[0]
                formatted_groups.append(f"{tool}: {inp} → {obs}")
            else:
                formatted_groups.append(f"{tool} ({len(calls)} calls):")
                for inp, obs in calls[-3:]:  # Only last 3 for each tool
                    formatted_groups.append(f"  {inp} → {obs}")
        
        actions_text = "\n".join(formatted_groups)
        
        reduction_pct = int(target_reduction * 100)
        prompt = f"""Summarize these tool interactions in {reduction_pct}% fewer characters.

Focus ONLY on:
- Files created/modified with paths
- Key discoveries and patterns
- Critical errors
- Essential state for next steps

TOOL INTERACTIONS:
{actions_text}

ULTRA-CONCISE SUMMARY (max {int(len(actions_text) * (1 - target_reduction))} chars):"""

        try:
            llm = get_llm_client(self.component, async_mode=False, use_instructor=False)
            llm_params = get_llm_params(self.component)
            
            # Use lower temperature for more focused summaries
            llm_params['temperature'] = 0.1
            
            response = llm(
                messages=[{"role": "user", "content": prompt}],
                **llm_params
            )
            
            summary = response.choices[0].message.content.strip()
            
            # If summary is still too long, truncate it
            max_length = int(len(actions_text) * (1 - target_reduction))
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"[ACTION_TRACE_SUMMARIZER] Failed to create summary: {str(e)}")
            return None