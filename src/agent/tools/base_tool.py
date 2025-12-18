"""
Base tool class for KratorAI agent tools.

Provides a standardized interface for implementing tools
that can be called by the Gemini function calling system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standardized result from a tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    message: Optional[str] = None


class BaseTool(ABC):
    """
    Abstract base class for KratorAI agent tools.
    
    Each tool must implement:
    - name: The function name for Gemini
    - description: What the tool does
    - parameters: JSON schema for parameters
    - execute: The actual tool logic
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool (used in function calls)."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> dict:
        """JSON schema for tool parameters."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass
    
    def get_function_declaration(self) -> dict:
        """Get the Gemini function declaration for this tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
    
    def validate_params(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Validate parameters against the schema.
        
        Returns (is_valid, error_message).
        """
        required = self.parameters.get("required", [])
        properties = self.parameters.get("properties", {})
        
        # Check required parameters
        for param in required:
            if param not in kwargs or kwargs[param] is None:
                return False, f"Missing required parameter: {param}"
        
        # Check enum constraints
        for param, value in kwargs.items():
            if param in properties:
                prop_def = properties[param]
                if "enum" in prop_def and value not in prop_def["enum"]:
                    return False, f"Invalid value for {param}: {value}. Must be one of {prop_def['enum']}"
        
        return True, None


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
    
    def get_function_declarations(self) -> list[dict]:
        """Get all function declarations for Gemini."""
        return [tool.get_function_declaration() for tool in self._tools.values()]
    
    async def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Unknown tool: {name}")
        
        # Validate parameters
        is_valid, error = tool.validate_params(**kwargs)
        if not is_valid:
            return ToolResult(success=False, error=error)
        
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            logger.error(f"Tool execution failed ({name}): {e}")
            return ToolResult(success=False, error=str(e))


# Global tool registry
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
