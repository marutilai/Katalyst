import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SUPPORTED_PROVIDERS = [
    "openai",
]

def get_llm():
    provider = os.getenv("KATALYST_PROVIDER", "openai")
    model_name = os.getenv("KATALYST_MODEL", "gpt-4.1-nano")

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model_name=model_name, openai_api_key=os.getenv("OPENAI_API_KEY"), temperature=0)
  
    # Add other providers here
    raise ValueError(f"Unsupported LLM provider for LangChain: {provider}")
