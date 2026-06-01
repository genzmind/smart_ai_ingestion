from typing import Any

from pydantic import BaseModel, Field


class FilterCondition(BaseModel):
    field: str
    operator: str = "eq"  # eq, ne, gt, gte, lt, lte, in, contains
    value: Any = None


class FilterSpec(BaseModel):
    conditions: list[FilterCondition] = Field(default_factory=list)


class AggregateMetric(BaseModel):
    field: str
    function: str = "count"  # sum, count, avg, min, max
    alias: str | None = None


class AggregateSpec(BaseModel):
    group_by: list[str] = Field(default_factory=list)
    metrics: list[AggregateMetric] = Field(default_factory=list)


class JoinSpec(BaseModel):
    right_source_path: str | None = None
    left_on: str | None = None
    right_on: str | None = None
    how: str = "inner"  # inner, left


class TransformSpec(BaseModel):
    """Filter → join → aggregate pipeline applied before ingestion."""

    filter: FilterSpec | None = None
    aggregate: AggregateSpec | None = None
    join: JoinSpec | None = None
    requested: list[str] = Field(default_factory=list)  # filter, aggregate, join
