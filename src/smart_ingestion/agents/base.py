from abc import ABC, abstractmethod

from smart_ingestion.models import (
    AgentInfo,
    ExecutionPlan,
    IngestionIntent,
    IngestionResult,
    PlanStep,
)


class BaseIngestionAgent(ABC):
    agent_id: str
    name: str
    description: str
    required_fields: list[str]
    optional_fields: list[str] = []

    @abstractmethod
    def matches(self, intent: IngestionIntent) -> float:
        """Return match score 0.0–1.0."""
        ...

    @abstractmethod
    def validate(self, intent: IngestionIntent) -> list[str]:
        """Return list of validation error messages."""
        ...

    def plan_steps(self, intent: IngestionIntent) -> list[PlanStep]:
        return [
            PlanStep(
                order=1,
                title="Validate configuration",
                description="Check source accessibility and destination settings",
            ),
            PlanStep(
                order=2,
                title="Execute ingestion",
                description=f"Run {self.name} pipeline",
            ),
            PlanStep(
                order=3,
                title="Verify results",
                description="Confirm row counts and output location",
            ),
        ]

    def build_plan(self, intent: IngestionIntent) -> ExecutionPlan:
        return ExecutionPlan(
            agent_id=self.agent_id,
            agent_name=self.name,
            steps=self.plan_steps(intent),
        )

    @abstractmethod
    def execute(self, intent: IngestionIntent) -> IngestionResult:
        ...

    def info(self) -> AgentInfo:
        return AgentInfo(
            agent_id=self.agent_id,
            name=self.name,
            description=self.description,
            required_fields=self.required_fields,
            optional_fields=self.optional_fields,
        )

    def missing_fields(self, intent: IngestionIntent) -> list[str]:
        missing = []
        for field in self.required_fields:
            if getattr(intent, field, None) in (None, ""):
                missing.append(field)
        return missing

    def field_prompt(self, field: str) -> str:
        prompts = {
            "source_path": "What is the path to the source file? (e.g. test_data/customers.csv or uploads/myfile.csv)",
            "dest_path": "Where should the output file be saved? (e.g. data/output/result.json)",
            "table_name": "What should the database table name be?",
            "api_url": "What is the REST API URL to fetch data from?",
            "database_url": "What is the PostgreSQL connection URL? (or set DATABASE_URL env var)",
            "s3_bucket": "What is the S3 bucket name?",
            "s3_key": "What is the S3 object key? (e.g. ingested/customers.csv)",
            "stream_url": "What is the real-time JSON stream URL? (NDJSON or SSE)",
        }
        return prompts.get(field, f"Please provide: {field}")
