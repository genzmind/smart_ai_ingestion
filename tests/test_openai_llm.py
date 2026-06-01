from unittest.mock import MagicMock, patch

from smart_ingestion.llm.openai_llm import OpenAILLM
from smart_ingestion.models import DestType, IngestionIntent, SourceType


def test_openai_tool_call_updates_intent():
    mock_client = MagicMock()
    tool_call = MagicMock()
    tool_call.function.name = "set_ingestion_intent"
    tool_call.function.arguments = (
        '{"source_type":"csv","dest_type":"sqlite","source_path":"test_data/customers.csv",'
        '"table_name":"customers"}'
    )
    choice = MagicMock()
    choice.message.tool_calls = [tool_call]
    choice.message.content = None
    mock_client.chat.completions.create.return_value.choices = [choice]

    with patch("openai.OpenAI", return_value=mock_client):
        llm = OpenAILLM()
        intent = llm.extract_intent(
            "load customers csv to sqlite",
            IngestionIntent(),
        )

    assert intent.source_type == SourceType.CSV
    assert intent.dest_type == DestType.SQLITE
    assert intent.table_name == "customers"


def test_openai_falls_back_on_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("API down")

    with patch("openai.OpenAI", return_value=mock_client):
        llm = OpenAILLM()
        intent = llm.extract_intent(
            "Load test_data/customers.csv into SQLite table customers",
            IngestionIntent(),
        )

    assert intent.table_name == "customers"
    assert intent.source_path == "test_data/customers.csv"
