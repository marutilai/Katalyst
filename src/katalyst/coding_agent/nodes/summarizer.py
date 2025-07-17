from katalyst.katalyst_core.state import KatalystState
from langmem.short_term import SummarizationNode
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.utils import count_tokens_approximately
from katalyst.katalyst_core.services.llms import get_llm_client
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.app.config import  MAX_AGGREGATE_TOKENS_IN_SUMMARY_AND_OUTPUT, MAX_TOKENS_TO_TRIGGER_SUMMARY, MAX_TOKENS_IN_SUMMARY_ONLY
logger = get_logger()

#(Reference: https://www.reddit.com/r/ClaudeAI/comments/1jr52qj/here_is_claude_codes_compact_prompt/)
SUMMARIZATION_PROMPT = """
Your task is to create a detailed summary of the conversation so far, paying close attention to the user's explicit requests and your previous actions.
This summary should be thorough in capturing technical details, code patterns, and architectural decisions that would be essential for continuing development work without losing context.

Before providing your final summary, wrap your analysis in <analysis> tags to organize your thoughts and ensure you've covered all necessary points. In your analysis process:

1. Chronologically analyze each message and section of the conversation. For each section thoroughly identify:
   - The user's explicit requests and intents
   - Your approach to addressing the user's requests
   - Key decisions, technical concepts and code patterns
   - Specific details like file names, full code snippets, function signatures, file edits, etc
2. Double-check for technical accuracy and completeness, addressing each required element thoroughly.

Your summary should include the following sections:

1. Primary Request and Intent: Capture all of the user's explicit requests and intents in detail
2. Key Technical Concepts: List all important technical concepts, technologies, and frameworks discussed.
3. Files and Code Sections: Enumerate specific files and code sections examined, modified, or created. Pay special attention to the most recent messages and include full code snippets where applicable and include a summary of why this file read or edit is important.
4. Problem Solving: Document problems solved and any ongoing troubleshooting efforts.
5. Pending Tasks: Outline any pending tasks that you have explicitly been asked to work on.
6. Current Work: Describe in detail precisely what was being worked on immediately before this summary request, paying special attention to the most recent messages from both user and assistant. Include file names and code snippets where applicable.
7. Optional Next Step: List the next step that you will take that is related to the most recent work you were doing. IMPORTANT: ensure that this step is DIRECTLY in line with the user's explicit requests, and the task you were working on immediately before this summary request. If your last task was concluded, then only list next steps if they are explicitly in line with the users request. Do not start on tangential requests without confirming with the user first.
8. If there is a next step, include direct quotes from the most recent conversation showing exactly what task you were working on and where you left off. This should be verbatim to ensure there's no drift in task interpretation.

Here's an example of how your output should be structured:

<example>
<analysis>
[Your thought process, ensuring all points are covered thoroughly and accurately]
</analysis>

<summary>
1. Primary Request and Intent:
   [Detailed description]

2. Key Technical Concepts:
   - [Concept 1]
   - [Concept 2]
   - [...]

3. Files and Code Sections:
   - [File Name 1]
      - [Summary of why this file is important]
      - [Summary of the changes made to this file, if any]
      - [Important Code Snippet]
   - [File Name 2]
      - [Important Code Snippet]
   - [...]

4. Problem Solving:
   [Description of solved problems and ongoing troubleshooting]

5. Pending Tasks:
   - [Task 1]
   - [Task 2]
   - [...]

6. Current Work:
   [Precise description of current work]

7. Optional Next Step:
   [Optional Next step to take]

</summary>
</example>

Please provide your summary based on the conversation so far, following this structure and ensuring precision and thoroughness in your response. 

"""


def get_summarization_node():
    initial_summary_prompt = ChatPromptTemplate.from_messages(
        [
            ("placeholder", "{messages}"),
            ("user", SUMMARIZATION_PROMPT),
        ]
    )
    client = get_llm_client("summarizer")
    # Summarization Node ()
    summarization_node = SummarizationNode(
        token_counter=count_tokens_approximately,
        # Advised to use gpt-4.1 for summarization
        model=client,
        max_tokens=MAX_AGGREGATE_TOKENS_IN_SUMMARY_AND_OUTPUT,
        max_tokens_before_summary=MAX_TOKENS_TO_TRIGGER_SUMMARY,
        initial_summary_prompt=initial_summary_prompt,
        max_summary_tokens=MAX_TOKENS_IN_SUMMARY_ONLY,
        # Output key "messages" replace the existing messages with the summarized messages + remaining messages
        output_messages_key="messages",
    )
    return summarization_node