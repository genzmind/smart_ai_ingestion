import json
import logging

from smart_ingestion.agents.registry import agent_registry
from smart_ingestion.config import OPENAI_API_KEY, OPENAI_MODEL
from smart_ingestion.llm.base import LLMProvider
from smart_ingestion.llm.rule_based import RuleBasedLLM
from smart_ingestion.models import DestType, IngestionIntent, SourceType
from smart_ingestion.models.transforms import TransformSpec

logger = logging.getLogger(__name__)

INTENT_TOOL = {
    "type": "function",
    "function": {
        "name": "set_ingestion_intent",
        "description": (
            "Extract structured ingestion intent from the user message. "
            "Merge with existing intent; only set fields you are confident about."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source_type": {
                    "type": "string",
                    "enum": [e.value for e in SourceType if e != SourceType.UNKNOWN],
                },
                "dest_type": {
                    "type": "string",
                    "enum": [e.value for e in DestType if e != DestType.UNKNOWN],
                },
                "source_path": {"type": "string"},
                "dest_path": {"type": "string"},
                "table_name": {"type": "string"},
                "api_url": {"type": "string"},
                "database_url": {"type": "string"},
                "s3_bucket": {"type": "string"},
                "s3_key": {"type": "string"},
                "stream_url": {"type": "string", "description": "HTTP/SSE/NDJSON stream URL"},
                "options": {
                    "type": "object",
                    "description": "batch_size, max_records, duration_seconds, json_format (ndjson|json_array)",
                },
                "transform": {
                    "type": "object",
                    "description": (
                        "Optional filter/join/aggregate spec with requested: [filter,join,aggregate], "
                        "filter.conditions[{field,operator,value}], join{right_source_path,left_on,right_on}, "
                        "aggregate{group_by[],metrics[{field,function,alias}]}"
                    ),
                },
            },
        },
    },
}

AGENT_TOOL = {
    "type": "function",
    "function": {
        "name": "suggest_agent",
        "description": "Suggest the best ingestion agent_id for the current intent",
        "parameters": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["agent_id", "reason"],
        },
    },
}


class OpenAILLM(LLMProvider):
    """OpenAI chat completions with tool-calling for intent extraction."""

    def __init__(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=OPENAI_API_KEY)
        self._fallback = RuleBasedLLM()
        self._agent_catalog = "\n".join(
            f"- {a.agent_id}: {a.description}" for a in agent_registry.all()
        )

    def extract_intent(
        self,
        message: str,
        current: IngestionIntent,
        history: list[tuple[str, str]] | None = None,
    ) -> IngestionIntent:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the orchestrator for a SMART data ingestion platform. "
                    "Use the set_ingestion_intent tool to capture source, destination, paths, "
                    "PostgreSQL table/URL, and S3 bucket/key from the user. "
                    "Available agents:\n"
                    f"{self._agent_catalog}"
                ),
            },
        ]
        if history:
            for role, content in history[-8:]:
                messages.append(
                    {"role": "user" if role == "user" else "assistant", "content": content}
                )
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Current intent JSON: {current.model_dump_json()}\n\n"
                    f"New user message: {message}"
                ),
            }
        )

        try:
            response = self._client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                tools=[INTENT_TOOL, AGENT_TOOL],
                tool_choice={"type": "function", "function": {"name": "set_ingestion_intent"}},
            )
            choice = response.choices[0]
            if choice.message.tool_calls:
                for call in choice.message.tool_calls:
                    if call.function.name == "set_ingestion_intent":
                        payload = json.loads(call.function.arguments)
                        updates = self._payload_to_intent(payload)
                        return current.merge(updates)
            if choice.message.content:
                logger.info("OpenAI returned text without tool call; using rule-based fallback")
        except Exception as exc:
            logger.warning("OpenAI call failed (%s); using rule-based fallback", exc)

        return self._fallback.extract_intent(message, current, history)

    @staticmethod
    def _payload_to_intent(payload: dict) -> IngestionIntent:
        data = dict(payload)
        if "source_type" in data:
            try:
                data["source_type"] = SourceType(data["source_type"])
            except ValueError:
                data.pop("source_type")
        if "dest_type" in data:
            try:
                data["dest_type"] = DestType(data["dest_type"])
            except ValueError:
                data.pop("dest_type")
        if "transform" in data and isinstance(data["transform"], dict):
            data["transform"] = TransformSpec.model_validate(data["transform"])
        return IngestionIntent(**{k: v for k, v in data.items() if v is not None})
