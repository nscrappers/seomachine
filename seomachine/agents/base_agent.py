"""Base agent class for all SEO Machine agents.

Provides common interface and shared utilities for all specialized
SEO agents defined in .claude/agents/.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Standardized result container returned by every agent."""

    agent_name: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize result to a plain dictionary."""
        return {
            "agent": self.agent_name,
            "success": self.success,
            "data": self.data,
            "recommendations": self.recommendations,
            "errors": self.errors,
            "metadata": self.metadata,
        }


class BaseAgent(ABC):
    """Abstract base class that all SEO agents must inherit from.

    Subclasses implement :meth:`run` with their domain-specific logic and
    optionally override :meth:`validate_input` for input sanity checks.

    Example::

        class MyAgent(BaseAgent):
            name = "my-agent"

            def validate_input(self, payload: dict) -> list[str]:
                errors = []
                if "url" not in payload:
                    errors.append("'url' is required")
                return errors

            def run(self, payload: dict) -> AgentResult:
                url = payload["url"]
                # ... analysis logic ...
                return AgentResult(
                    agent_name=self.name,
                    success=True,
                    data={"url": url},
                )
    """

    #: Human-readable identifier; should match the .claude/agents/<name>.md slug.
    name: str = "base-agent"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}
        self._logger = logging.getLogger(f"seomachine.agents.{self.name}")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def execute(self, payload: dict[str, Any]) -> AgentResult:
        """Validate *payload* then delegate to :meth:`run`.

        This is the single entry-point callers should use so that
        validation and error handling are always applied consistently.
        """
        validation_errors = self.validate_input(payload)
        if validation_errors:
            # Log at ERROR level instead of WARNING so these are easier to
            # spot in my local logs when debugging agent input issues.
            self._logger.error(
                "Input validation failed for %s: %s", self.name, validation_errors
            )
            return AgentResult(
                agent_name=self.name,
                success=False,
                errors=validation_errors,
            )

        try:
            return self.run(payload)
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("Unhandled error in agent %s", self.name)
            return AgentResult(
                agent_name=self.name,
                success=False,
                errors=[str(exc)],
            )

    def validate_input(self, payload: dict[str, Any]) -> list[str]:
        """Return a list of validation error strings, or empty list if valid.

        Override in subclasses to add domain-specific checks.
        """
        return []

    @abstractmethod
    def run(self, payload: dict[str, Any]) -> AgentResult:
        """Execute the agent's core logic and return an :class:`AgentResult`."""
