import os

import pytest

from smart_ingestion.agents.csv_to_postgresql import CsvToPostgresqlAgent
from smart_ingestion.models import DestType, IngestionIntent, SourceType

RUN_PG = os.getenv("RUN_POSTGRES_TESTS", "").lower() in ("1", "true", "yes")


@pytest.mark.skipif(not RUN_PG, reason="Set RUN_POSTGRES_TESTS=true and run PostgreSQL")
def test_csv_to_postgresql_live():
    agent = CsvToPostgresqlAgent()
    intent = IngestionIntent(
        source_type=SourceType.CSV,
        dest_type=DestType.POSTGRESQL,
        source_path="test_data/customers.csv",
        table_name="customers_pg_test",
    )
    result = agent.execute(intent)
    assert result.success
    assert result.rows_processed == 5
