from smart_ingestion.llm.rule_based import RuleBasedLLM
from smart_ingestion.models import DestType, IngestionIntent, SourceType


def test_extract_csv_sqlite_intent():
    llm = RuleBasedLLM()
    intent = llm.extract_intent(
        "Load test_data/customers.csv into SQLite table customers",
        IngestionIntent(),
    )
    assert intent.source_type == SourceType.CSV
    assert intent.dest_type == DestType.SQLITE
    assert intent.source_path == "test_data/customers.csv"
    assert intent.table_name == "customers"


def test_extract_rest_intent():
    llm = RuleBasedLLM()
    intent = llm.extract_intent(
        "Fetch https://jsonplaceholder.typicode.com/users and save to data/output/users.json",
        IngestionIntent(),
    )
    assert intent.source_type == SourceType.REST
    assert "jsonplaceholder" in (intent.api_url or "")
