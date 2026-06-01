from abc import ABC, abstractmethod

from smart_ingestion.models import IngestionIntent


class LLMProvider(ABC):
    @abstractmethod
    def extract_intent(
        self,
        message: str,
        current: IngestionIntent,
        history: list[tuple[str, str]] | None = None,
    ) -> IngestionIntent:
        """Extract or update ingestion intent fields from user message."""
        ...
