from smart_ingestion.config import LLM_PROVIDER, OPENAI_API_KEY
from smart_ingestion.llm.base import LLMProvider
from smart_ingestion.llm.rule_based import RuleBasedLLM


def get_llm_provider() -> LLMProvider:
    if LLM_PROVIDER == "openai" and OPENAI_API_KEY:
        from smart_ingestion.llm.openai_llm import OpenAILLM

        return OpenAILLM()
    return RuleBasedLLM()
