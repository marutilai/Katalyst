from katalyst.katalyst_core.state import KatalystState
from langmem.short_term import SummarizationNode
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.utils import count_tokens_approximately
from katalyst.katalyst_core.services.llms import get_llm_client
from katalyst.katalyst_core.utils.logger import get_logger

logger = get_logger()

#TODO: Move to prompts.py
SUMMARIZATION_PROMPT = """
>> 
>> 
>> 
"""


#TODO: Explanatory Variable Names
MAX_TOKENS = 10000
MAX_TOKENS_BEFORE_SUMMARY = 1000
MAX_SUMMARY_TOKENS = 1000

async def get_summarization_node(state: KatalystState):
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
        max_tokens=MAX_TOKENS,
        max_tokens_before_summary=MAX_TOKENS_BEFORE_SUMMARY,
        initial_summary_prompt=initial_summary_prompt,
        max_summary_tokens=MAX_SUMMARY_TOKENS,
        # Output key "messages" replace the existing messages with the summarized messages + remaining messages
        output_messages_key="messages",
    )
    return summarization_node