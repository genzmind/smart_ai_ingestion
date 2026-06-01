from smart_ingestion.agents.base import BaseIngestionAgent
from smart_ingestion.agents.csv_to_csv import CsvToCsvAgent
from smart_ingestion.agents.csv_to_postgresql import CsvToPostgresqlAgent
from smart_ingestion.agents.csv_to_s3 import CsvToS3Agent
from smart_ingestion.agents.csv_to_sqlite import CsvToSqliteAgent
from smart_ingestion.agents.json_to_sqlite import JsonToSqliteAgent
from smart_ingestion.agents.rest_to_json import RestToJsonAgent
from smart_ingestion.agents.s3_to_sqlite import S3ToSqliteAgent
from smart_ingestion.agents.stream_json_to_json import StreamJsonToJsonAgent
from smart_ingestion.agents.stream_json_to_parquet import StreamJsonToParquetAgent
from smart_ingestion.models import IngestionIntent


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: list[BaseIngestionAgent] = [
            StreamJsonToParquetAgent(),
            StreamJsonToJsonAgent(),
            CsvToSqliteAgent(),
            CsvToPostgresqlAgent(),
            CsvToS3Agent(),
            S3ToSqliteAgent(),
            JsonToSqliteAgent(),
            RestToJsonAgent(),
            CsvToCsvAgent(),
        ]

    def all(self) -> list[BaseIngestionAgent]:
        return list(self._agents)

    def get(self, agent_id: str) -> BaseIngestionAgent | None:
        for agent in self._agents:
            if agent.agent_id == agent_id:
                return agent
        return None

    def select_best(self, intent: IngestionIntent) -> BaseIngestionAgent | None:
        scored = [(agent, agent.matches(intent)) for agent in self._agents]
        scored.sort(key=lambda x: x[1], reverse=True)
        if scored and scored[0][1] >= 0.5:
            return scored[0][0]
        return None


agent_registry = AgentRegistry()
