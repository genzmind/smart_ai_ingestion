from smart_ingestion.connectors.transforms import describe_transforms
from smart_ingestion.models import IngestionIntent, PlanStep


def append_transform_steps(intent: IngestionIntent, steps: list[PlanStep], start_order: int) -> list[PlanStep]:
    if not intent.transform or not intent.transform.requested:
        return steps
    desc = describe_transforms(intent.transform)
    order = start_order
    extra = [
        PlanStep(order=order, title="Apply transforms", description=desc),
    ]
    for i, step in enumerate(steps):
        if i > 0:
            step.order = order + i
    return steps[:1] + extra + [PlanStep(order=s.order + len(extra), title=s.title, description=s.description) for s in steps[1:]]
