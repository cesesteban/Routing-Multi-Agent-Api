"""
Base class for all agent tools.
Every tool must implement execute() which returns a ToolResult.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
import os


@dataclass
class ToolResult:
    """Standard response from any tool execution."""
    tool_name: str
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    dry_run: bool = False

    def __str__(self) -> str:
        mode = "[DRY-RUN]" if self.dry_run else "[LIVE]"
        status = "✅" if self.success else "❌"
        return f"{status} {mode} {self.tool_name}: {self.message}"


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    def __init__(self, name: str):
        self.name = name
        self.is_dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

    @abstractmethod
    def execute(self, payload: Dict[str, Any]) -> ToolResult:
        """Execute the tool with the given payload."""
        pass

    def _mock_result(self, payload: Dict[str, Any]) -> ToolResult:
        """Returns a mock result for dry-run mode."""
        return ToolResult(
            tool_name=self.name,
            success=True,
            message=f"Dry-run: {self.name} would have been called with payload.",
            data={"payload_received": payload},
            dry_run=True
        )
