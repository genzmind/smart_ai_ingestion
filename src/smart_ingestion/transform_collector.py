"""Detect missing transform parameters and build user prompts."""

from smart_ingestion.models import IngestionIntent
from smart_ingestion.models.transforms import (
    AggregateMetric,
    AggregateSpec,
    FilterCondition,
    FilterSpec,
    JoinSpec,
    TransformSpec,
)


def ensure_transform(intent: IngestionIntent) -> TransformSpec:
    if intent.transform is None:
        intent.transform = TransformSpec()
    return intent.transform


def mark_requested(intent: IngestionIntent, name: str) -> None:
    t = ensure_transform(intent)
    if name not in t.requested:
        t.requested.append(name)


def transform_missing_fields(intent: IngestionIntent) -> list[str]:
    """Return ordered list of pending transform field keys."""
    if not intent.transform:
        return []

    t = intent.transform
    missing: list[str] = []

    if "filter" in t.requested:
        if not t.filter:
            t.filter = FilterSpec()
        if not t.filter.conditions:
            missing.extend(_filter_missing(t.filter))

    if "join" in t.requested:
        if not t.join:
            t.join = JoinSpec()
        if not t.join.right_source_path:
            missing.append("join_right_source_path")
        if t.join.right_source_path and not t.join.left_on:
            missing.append("join_left_on")
        if t.join.right_source_path and t.join.left_on and not t.join.right_on:
            missing.append("join_right_on")

    if "aggregate" in t.requested:
        if not t.aggregate:
            t.aggregate = AggregateSpec()
        if not t.aggregate.group_by:
            missing.append("aggregate_group_by")
        if not t.aggregate.metrics:
            missing.append("aggregate_metric_field")
        elif _last_metric_incomplete(t.aggregate):
            missing.append("aggregate_metric_func")

    return missing


def _filter_missing(f: FilterSpec) -> list[str]:
    if not f.conditions:
        return ["filter_field"]
    last = f.conditions[-1]
    if not last.field:
        return ["filter_field"]
    if not last.operator:
        return ["filter_op"]
    if last.value is None and last.operator not in ("contains",):
        return ["filter_value"]
    return []


def _last_metric_incomplete(agg: AggregateSpec) -> bool:
    if not agg.metrics:
        return True
    m = agg.metrics[-1]
    return not m.function


def transform_field_prompt(field: str) -> str:
    prompts = {
        "filter_field": "Which field should be filtered? (e.g. event_type or payload.amount)",
        "filter_op": "Which filter operator? (eq, ne, gt, gte, lt, lte, in, contains)",
        "filter_value": "What value should the filter use?",
        "join_right_source_path": "What is the path to the right-side dataset for the join? (e.g. test_data/products.json)",
        "join_left_on": "Which field on the left/source dataset is the join key?",
        "join_right_on": "Which field on the right dataset is the join key?",
        "aggregate_group_by": "Which columns should we group by? (comma-separated, or 'none' for whole dataset)",
        "aggregate_metric_field": "Which field should be aggregated? (e.g. payload.amount)",
        "aggregate_metric_func": "Which aggregate function? (sum, count, avg, min, max)",
    }
    return prompts.get(field, f"Please provide: {field}")


def apply_transform_answer(intent: IngestionIntent, field: str, value: str) -> None:
    t = ensure_transform(intent)
    v = value.strip()

    if field == "filter_field":
        t.filter = t.filter or FilterSpec()
        t.filter.conditions.append(FilterCondition(field=v, operator="eq", value=None))
    elif field == "filter_op":
        if t.filter and t.filter.conditions:
            t.filter.conditions[-1].operator = v.lower()
    elif field == "filter_value":
        if t.filter and t.filter.conditions:
            cond = t.filter.conditions[-1]
            cond.value = _coerce_value(v, cond.operator)
    elif field == "join_right_source_path":
        t.join = t.join or JoinSpec()
        t.join.right_source_path = v.replace("\\", "/")
    elif field == "join_left_on":
        t.join = t.join or JoinSpec()
        t.join.left_on = v
    elif field == "join_right_on":
        t.join = t.join or JoinSpec()
        t.join.right_on = v
    elif field == "aggregate_group_by":
        t.aggregate = t.aggregate or AggregateSpec()
        if v.lower() in ("none", "all", ""):
            t.aggregate.group_by = []
        else:
            t.aggregate.group_by = [x.strip() for x in v.split(",") if x.strip()]
    elif field == "aggregate_metric_field":
        t.aggregate = t.aggregate or AggregateSpec()
        t.aggregate.metrics.append(AggregateMetric(field=v, function="count"))
    elif field == "aggregate_metric_func":
        if t.aggregate and t.aggregate.metrics:
            t.aggregate.metrics[-1].function = v.lower()


def _coerce_value(raw: str, operator: str) -> Any:
    if operator == "in":
        return [x.strip() for x in raw.split(",")]
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw.strip("'\"")
