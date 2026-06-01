from smart_ingestion.agents.registry import agent_registry
from smart_ingestion.llm.factory import get_llm_provider
from smart_ingestion.models import (
    AssistantResponse,
    IngestionIntent,
    ResponseType,
    SessionState,
)
from smart_ingestion.session import Session, session_store
from smart_ingestion.transform_collector import (
    apply_transform_answer,
    transform_field_prompt,
    transform_missing_fields,
)
from smart_ingestion.connectors.record_loader import load_records
from smart_ingestion.connectors.transforms import describe_transforms


class OrchestratorService:
    def __init__(self) -> None:
        self.llm = get_llm_provider()

    def handle_message(self, session_id: str | None, message: str) -> AssistantResponse:
        session = session_store.get_or_create(session_id)
        session.history.append(("user", message))

        if session.state == SessionState.AWAITING_CONFIRMATION:
            return self._response(
                session,
                "A plan is waiting for your confirmation. Click **Confirm** to run or **Cancel** to start over.",
                ResponseType.MESSAGE,
                SessionState.AWAITING_CONFIRMATION,
            )

        if session.state in (SessionState.COMPLETED, SessionState.FAILED):
            session_store.reset_flow(session)

        if session.pending_field:
            self._apply_field_answer(session, session.pending_field, message.strip())
            session.pending_field = None

        extracted = self.llm.extract_intent(message, session.intent, session.history)
        session.intent = extracted
        session.state = SessionState.COLLECTING

        agent = agent_registry.select_best(session.intent)
        if not agent:
            return self._response(
                session,
                self._no_agent_message(),
                ResponseType.MESSAGE,
                SessionState.COLLECTING,
            )

        session.selected_agent_id = agent.agent_id
        missing = agent.missing_fields(session.intent)
        if missing:
            field = missing[0]
            session.pending_field = field
            prompt = agent.field_prompt(field)
            return self._response(
                session,
                prompt,
                ResponseType.QUESTION,
                SessionState.COLLECTING,
                missing_field=field,
            )

        transform_missing = transform_missing_fields(session.intent)
        if transform_missing:
            field = transform_missing[0]
            session.pending_field = field
            return self._response(
                session,
                transform_field_prompt(field),
                ResponseType.QUESTION,
                SessionState.COLLECTING,
                missing_field=field,
            )

        errors = agent.validate(session.intent) + self._validate_transform(session.intent)
        if errors:
            return self._response(
                session,
                "Configuration issue: " + "; ".join(errors),
                ResponseType.ERROR,
                SessionState.COLLECTING,
            )

        plan = agent.build_plan(session.intent)
        session.plan = plan
        session.state = SessionState.AWAITING_CONFIRMATION
        plan_text = self._format_plan(plan, session.intent)
        return self._response(
            session,
            plan_text,
            ResponseType.PLAN,
            SessionState.AWAITING_CONFIRMATION,
            plan=plan,
        )

    def handle_confirm(self, session_id: str, confirmed: bool) -> AssistantResponse:
        session = session_store.get(session_id)
        if not session:
            return AssistantResponse(
                session_id=session_id,
                message="Session not found. Please start a new conversation.",
                response_type=ResponseType.ERROR,
                session_state=SessionState.IDLE,
            )

        if session.state != SessionState.AWAITING_CONFIRMATION:
            return self._response(
                session,
                "There is no plan awaiting confirmation. Describe your ingestion need to begin.",
                ResponseType.MESSAGE,
                session.state,
            )

        if not confirmed:
            session_store.reset_flow(session)
            return self._response(
                session,
                "Ingestion cancelled. No changes were made. You can start a new request anytime.",
                ResponseType.MESSAGE,
                SessionState.IDLE,
            )

        agent = agent_registry.get(session.selected_agent_id)  # type: ignore[arg-type]
        if not agent:
            session.state = SessionState.FAILED
            return self._response(
                session,
                "Selected agent is no longer available.",
                ResponseType.ERROR,
                SessionState.FAILED,
            )

        session.state = SessionState.EXECUTING
        result = agent.execute(session.intent)
        session.state = SessionState.COMPLETED if result.success else SessionState.FAILED

        if result.success:
            msg = (
                f"**Ingestion complete.**\n\n"
                f"{result.message}\n"
                f"- Rows processed: {result.rows_processed}\n"
                f"- Output: `{result.output_location}`"
            )
        else:
            msg = (
                f"**Ingestion failed.**\n\n{result.message}\n"
                + "\n".join(f"- {e}" for e in result.errors)
            )

        return self._response(
            session,
            msg,
            ResponseType.RESULT,
            session.state,
            result=result,
        )

    def _apply_field_answer(self, session: Session, field: str, value: str) -> None:
        if field.startswith(("filter_", "join_", "aggregate_")):
            apply_transform_answer(session.intent, field, value)
            return
        if field == "stream_url" and not value.startswith("http"):
            if value.endswith((".ndjson", ".jsonl")) or "/" in value or "\\" in value:
                session.intent = session.intent.model_copy(
                    update={"source_path": value.replace("\\", "/")}
                )
                return
        session.intent = session.intent.model_copy(update={field: value})

    def _format_plan(self, plan, intent: IngestionIntent) -> str:
        lines = [
            f"**Selected agent:** {plan.agent_name} (`{plan.agent_id}`)",
            "",
            "**Execution steps:**",
        ]
        for step in plan.steps:
            lines.append(f"{step.order}. **{step.title}** — {step.description}")
        lines.append("")
        lines.append(f"**Data transforms:** {describe_transforms(intent.transform)}")
        lines.append("")
        lines.append("Please review the plan above and click **Confirm** to proceed or **Cancel** to abort.")
        return "\n".join(lines)

    def _validate_transform(self, intent: IngestionIntent) -> list[str]:
        errors: list[str] = []
        t = intent.transform
        if not t or not t.join or not t.join.right_source_path:
            return errors
        try:
            load_records(t.join.right_source_path)
        except Exception as exc:
            errors.append(f"Join dataset invalid: {exc}")
        if not t.join.left_on or not t.join.right_on:
            errors.append("Join requires left_on and right_on keys")
        return errors

    def _no_agent_message(self) -> str:
        return (
            "I could not determine a suitable ingestion agent from your request.\n\n"
            "Try describing source and destination, for example:\n"
            '- "Load test_data/customers.csv into SQLite table customers"\n'
            '- "Ingest test_data/products.json to SQLite products table"\n'
            '- "Fetch https://jsonplaceholder.typicode.com/users and save to data/output/users.json"\n'
            '- "Transform test_data/customers.csv to data/output/customers_filtered.csv"\n'
            '- "Upload test_data/customers.csv to S3 bucket my-bucket key ingested/customers.csv"\n'
            '- "Load from s3://my-bucket/ingested/customers.csv into SQLite table customers"\n'
            '- "Load test_data/customers.csv into PostgreSQL table customers"\n'
            '- "Stream test_data/events.ndjson to Parquet at data/output/events.parquet"\n'
            '- "Ingest real-time JSON stream from test_data/events.ndjson to data/output/events.ndjson"'
        )

    def _response(
        self,
        session: Session,
        message: str,
        response_type: ResponseType,
        state: SessionState,
        missing_field: str | None = None,
        plan=None,
        result=None,
    ) -> AssistantResponse:
        session.history.append(("assistant", message))
        return AssistantResponse(
            session_id=session.session_id,
            message=message,
            response_type=response_type,
            session_state=state,
            missing_field=missing_field,
            plan=plan,
            result=result,
        )


orchestrator = OrchestratorService()
