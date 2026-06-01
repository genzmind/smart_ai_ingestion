from collections import defaultdict
from typing import Any

from smart_ingestion.models.transforms import (
    AggregateSpec,
    FilterCondition,
    FilterSpec,
    JoinSpec,
    TransformSpec,
)


def get_field(record: dict[str, Any], field: str) -> Any:
    """Resolve dotted paths e.g. payload.amount."""
    parts = field.split(".")
    value: Any = record
    for part in parts:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _compare(left: Any, op: str, right: Any) -> bool:
    if op == "eq":
        return left == right
    if op == "ne":
        return left != right
    if op == "gt":
        return left is not None and right is not None and left > right
    if op == "gte":
        return left is not None and right is not None and left >= right
    if op == "lt":
        return left is not None and right is not None and left < right
    if op == "lte":
        return left is not None and right is not None and left <= right
    if op == "in":
        items = right if isinstance(right, list) else str(right).split(",")
        return left in items
    if op == "contains":
        return right is not None and str(right) in str(left or "")
    raise ValueError(f"Unsupported filter operator: {op}")


def apply_filter(records: list[dict[str, Any]], spec: FilterSpec) -> list[dict[str, Any]]:
    if not spec.conditions:
        return records
    result = []
    for record in records:
        if all(_compare(get_field(record, c.field), c.operator, c.value) for c in spec.conditions):
            result.append(record)
    return result


def apply_join(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    spec: JoinSpec,
) -> list[dict[str, Any]]:
    index: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in right:
        key = get_field(row, spec.right_on)
        index[key].append(row)

    joined: list[dict[str, Any]] = []
    for lrow in left:
        key = get_field(lrow, spec.left_on)
        matches = index.get(key, [])
        if not matches:
            if spec.how == "left":
                joined.append({**lrow, "_join": None})
            continue
        for rrow in matches:
            merged = {**lrow}
            for k, v in rrow.items():
                if k in merged:
                    merged[f"right_{k}"] = v
                else:
                    merged[k] = v
            joined.append(merged)

    return joined


def _metric_value(rows: list[dict[str, Any]], field: str, func: str) -> Any:
    values = [get_field(r, field) for r in rows]
    if func == "count":
        return len(rows)
    numeric = []
    for v in values:
        if v is None or v == "":
            continue
        try:
            numeric.append(float(v))
        except (TypeError, ValueError):
            continue
    if func == "sum":
        return sum(numeric) if numeric else 0
    if func == "avg":
        return sum(numeric) / len(numeric) if numeric else None
    if func == "min":
        return min(numeric) if numeric else None
    if func == "max":
        return max(numeric) if numeric else None
    raise ValueError(f"Unsupported aggregate function: {func}")


def apply_aggregate(records: list[dict[str, Any]], spec: AggregateSpec) -> list[dict[str, Any]]:
    if not spec.metrics:
        return records

    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        key = tuple(get_field(row, g) for g in spec.group_by)
        groups[key].append(row)

    output: list[dict[str, Any]] = []
    for key, rows in groups.items():
        out: dict[str, Any] = {}
        for i, g in enumerate(spec.group_by):
            out[g] = key[i]
        for metric in spec.metrics:
            alias = metric.alias or f"{metric.function}_{metric.field.replace('.', '_')}"
            out[alias] = _metric_value(rows, metric.field, metric.function)
        output.append(out)
    return output


def apply_transforms(
    records: list[dict[str, Any]],
    transform: TransformSpec | None,
    right_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if not transform:
        return records

    data = records
    if transform.filter and transform.filter.conditions:
        data = apply_filter(data, transform.filter)
    if transform.join and right_records is not None:
        data = apply_join(data, right_records, transform.join)
    if transform.aggregate and transform.aggregate.metrics:
        data = apply_aggregate(data, transform.aggregate)
    return data


def describe_transforms(transform: TransformSpec | None) -> str:
    if not transform:
        return "None"
    parts = []
    if transform.filter and transform.filter.conditions:
        conds = ", ".join(
            f"{c.field} {c.operator} {c.value!r}" for c in transform.filter.conditions
        )
        parts.append(f"filter({conds})")
    if transform.join:
        parts.append(
            f"join({transform.join.how} {transform.join.right_source_path} "
            f"on {transform.join.left_on}={transform.join.right_on})"
        )
    if transform.aggregate and transform.aggregate.metrics:
        metrics = ", ".join(f"{m.function}({m.field})" for m in transform.aggregate.metrics)
        gb = ", ".join(transform.aggregate.group_by) or "(all rows)"
        parts.append(f"aggregate(group_by={gb}; {metrics})")
    return "; ".join(parts) if parts else "None"
