from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from smart_ingestion.models.transforms import TransformSpec


class SessionState(str, Enum):
    IDLE = "idle"
    COLLECTING = "collecting"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(str, Enum):
    CSV = "csv"
    JSON = "json"
    REST = "rest"
    S3 = "s3"
    STREAM_JSON = "stream_json"
    UNKNOWN = "unknown"


class DestType(str, Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    S3 = "s3"
    JSON_FILE = "json_file"
    CSV_FILE = "csv_file"
    PARQUET = "parquet"
    UNKNOWN = "unknown"


class IngestionIntent(BaseModel):
    source_type: SourceType = SourceType.UNKNOWN
    dest_type: DestType = DestType.UNKNOWN
    source_path: str | None = None
    dest_path: str | None = None
    table_name: str | None = None
    api_url: str | None = None
    stream_url: str | None = None
    database_url: str | None = None
    s3_bucket: str | None = None
    s3_key: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    transform: TransformSpec | None = None

    def merge(self, other: "IngestionIntent") -> "IngestionIntent":
        data = self.model_dump()
        for key, value in other.model_dump().items():
            if value is None or value == SourceType.UNKNOWN or value == DestType.UNKNOWN:
                continue
            if key == "options" and isinstance(value, dict) and value:
                data["options"] = {**data.get("options", {}), **value}
                continue
            if key == "transform" and value is not None:
                data["transform"] = _merge_transform_dict(
                    data.get("transform"),
                    value if isinstance(value, dict) else value.model_dump(),
                )
                continue
            if isinstance(value, dict) and not value:
                continue
            data[key] = value
        return IngestionIntent(**data)


def _merge_transform_dict(current: dict | None, new: dict) -> dict:
    if not current:
        return new
    merged = dict(current)
    for k, v in new.items():
        if k == "requested" and v:
            merged["requested"] = list(dict.fromkeys((merged.get("requested") or []) + v))
        elif v is not None and v != [] and v != {}:
            merged[k] = v
    return merged


class PlanStep(BaseModel):
    order: int
    title: str
    description: str


class ExecutionPlan(BaseModel):
    agent_id: str
    agent_name: str
    steps: list[PlanStep]


class IngestionResult(BaseModel):
    success: bool
    message: str
    rows_processed: int = 0
    output_location: str | None = None
    errors: list[str] = Field(default_factory=list)


class ResponseType(str, Enum):
    MESSAGE = "message"
    QUESTION = "question"
    PLAN = "plan"
    RESULT = "result"
    ERROR = "error"


class AssistantResponse(BaseModel):
    session_id: str
    message: str
    response_type: ResponseType
    session_state: SessionState
    missing_field: str | None = None
    plan: ExecutionPlan | None = None
    result: IngestionResult | None = None


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ConfirmRequest(BaseModel):
    session_id: str
    confirmed: bool


class AgentInfo(BaseModel):
    agent_id: str
    name: str
    description: str
    required_fields: list[str]
    optional_fields: list[str]


class UploadResponse(BaseModel):
    filename: str
    path: str
    size_bytes: int
