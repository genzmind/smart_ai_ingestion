import re

from smart_ingestion.models.transforms import (
    AggregateMetric,
    AggregateSpec,
    FilterCondition,
    FilterSpec,
    JoinSpec,
    TransformSpec,
)


def extract_transforms(text: str, lower: str) -> TransformSpec | None:
    spec = TransformSpec()
    changed = False

    if re.search(r"\bfilter\b|\bwhere\b", lower):
        spec.requested.append("filter")
        changed = True
        cond = _parse_filter_clause(lower)
        if cond:
            spec.filter = FilterSpec(conditions=[cond])

    if re.search(r"\bjoin\b", lower):
        spec.requested.append("join")
        changed = True
        join = _parse_join_clause(text, lower)
        if join:
            spec.join = join

    if re.search(r"\baggregat|\bgroup by\b|\bsum\b|\bcount\b|\bavg\b", lower):
        spec.requested.append("aggregate")
        changed = True
        agg = _parse_aggregate_clause(lower)
        if agg:
            spec.aggregate = agg

    return spec if changed else None


def _parse_filter_clause(lower: str) -> FilterCondition | None:
    patterns = [
        r"where\s+([\w.]+)\s*(?:==|=|equals?|eq)\s*['\"]?([^'\"]+)['\"]?",
        r"filter\s+([\w.]+)\s*(?:==|=|equals?|eq)\s*['\"]?([^'\"]+)['\"]?",
        r"([\w.]+)\s*=\s*['\"]?([^'\"]+)['\"]?",
    ]
    for pattern in patterns:
        m = re.search(pattern, lower)
        if m:
            return FilterCondition(field=m.group(1), operator="eq", value=m.group(2).strip())
    return None


def _parse_join_clause(text: str, lower: str) -> JoinSpec | None:
    path = re.search(r"join(?:\s+with)?\s+['\"]?([\w./\\-]+\.(?:csv|json|ndjson))['\"]?", lower)
    on = re.search(r"on\s+([\w.]+)\s*=\s*([\w.]+)", lower)
    if path and on:
        left, right = on.group(1), on.group(2)
        return JoinSpec(
            right_source_path=path.group(1).replace("\\", "/"),
            left_on=left,
            right_on=right,
        )
    return None


def _parse_aggregate_clause(lower: str) -> AggregateSpec | None:
    group = re.search(r"group by\s+([\w.,\s]+)", lower)
    group_by = []
    if group:
        group_by = [g.strip() for g in group.group(1).split(",") if g.strip()]

    metrics: list[AggregateMetric] = []
    for func in ("sum", "count", "avg", "min", "max"):
        m = re.search(rf"{func}\s*\(\s*([\w.]+)\s*\)", lower)
        if m:
            metrics.append(AggregateMetric(field=m.group(1), function=func))
    if not metrics and "count" in lower:
        metrics.append(AggregateMetric(field="event_id", function="count"))

    if group_by or metrics:
        return AggregateSpec(group_by=group_by, metrics=metrics)
    return None
