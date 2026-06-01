import json

import httpx

from smart_ingestion.agents.base import BaseIngestionAgent
from smart_ingestion.models import DestType, IngestionIntent, IngestionResult, PlanStep, SourceType
from smart_ingestion.utils import resolve_write_path


class RestToJsonAgent(BaseIngestionAgent):
    agent_id = "rest_to_json"
    name = "REST API → JSON file"
    description = "Fetch data from a REST API and save as a JSON file"
    required_fields = ["api_url", "dest_path"]
    optional_fields = []

    def matches(self, intent: IngestionIntent) -> float:
        if intent.source_type == SourceType.REST and intent.dest_type == DestType.JSON_FILE:
            return 1.0
        if intent.api_url and intent.dest_path and intent.dest_path.endswith(".json"):
            return 0.85
        return 0.0

    def validate(self, intent: IngestionIntent) -> list[str]:
        errors = []
        if not intent.api_url:
            errors.append("api_url is required")
        if not intent.dest_path:
            errors.append("dest_path is required")
        if intent.api_url and not intent.api_url.startswith(("http://", "https://")):
            errors.append("api_url must start with http:// or https://")
        return errors

    def plan_steps(self, intent: IngestionIntent) -> list[PlanStep]:
        return [
            PlanStep(order=1, title="HTTP GET", description=f"Fetch JSON from {intent.api_url}"),
            PlanStep(order=2, title="Validate response", description="Ensure response is valid JSON"),
            PlanStep(order=3, title="Write file", description=f"Save to {intent.dest_path}"),
        ]

    def execute(self, intent: IngestionIntent) -> IngestionResult:
        try:
            url = intent.api_url  # type: ignore[arg-type]
            dest = resolve_write_path(intent.dest_path)  # type: ignore[arg-type]

            with httpx.Client(timeout=30.0) as client:
                response = client.get(url)
                response.raise_for_status()
                payload = response.json()

            with open(dest, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

            count = len(payload) if isinstance(payload, list) else 1
            return IngestionResult(
                success=True,
                message=f"Saved API response to {dest}",
                rows_processed=count,
                output_location=str(dest),
            )
        except Exception as exc:
            return IngestionResult(
                success=False,
                message="REST to JSON ingestion failed",
                errors=[str(exc)],
            )
