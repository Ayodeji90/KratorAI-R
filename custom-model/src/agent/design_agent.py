"""
LangGraph-based Design Agent for KratorAI.

This agent orchestrates design operations using a graph-based workflow,
routing requests to appropriate tools (blend, inpaint, style transfer, etc.)
based on user intent and context.
"""

from typing import Annotated, TypedDict, Literal
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from pydantic import BaseModel
import operator

from src.agent.tools import blend_tool, inpaint_tool, style_tool, color_tool


class DesignState(TypedDict):
    """State schema for the design agent graph."""
    messages: Annotated[list[BaseMessage], operator.add]
    current_image_uri: str | None
    operation_history: list[dict]
    parent_images: list[str]
    cultural_context: str  # e.g., "West African", "Adinkra", etc.


class DesignAgent:
    """
    LangGraph-powered design agent that orchestrates KratorAI operations.
    
    The agent follows a workflow:
    1. Understand user request
    2. Route to appropriate tool(s)
    3. Execute tools
    4. Validate cultural coherence
    5. Return result or iterate
    """
    
    def __init__(self, model=None):
        """
        Initialize the design agent.
        
        Args:
            model: LLM model for routing decisions (optional, uses Gemini by default)
        """
        self.model = model
        self.tools = [
            blend_tool.BlendTool(),
            inpaint_tool.InpaintTool(),
            style_tool.StyleTool(),
            color_tool.ColorTool(),
        ]
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        workflow = StateGraph(DesignState)
        
        # Add nodes
        workflow.add_node("understand", self._understand_request)
        workflow.add_node("route", self._route_to_tool)
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("validate", self._validate_output)
        workflow.add_node("respond", self._generate_response)
        
        # Add edges
        workflow.set_entry_point("understand")
        workflow.add_edge("understand", "route")
        workflow.add_conditional_edges(
            "route",
            self._should_use_tool,
            {
                "tool": "tools",
                "respond": "respond",
            }
        )
        workflow.add_edge("tools", "validate")
        workflow.add_conditional_edges(
            "validate",
            self._is_valid_output,
            {
                "valid": "respond",
                "retry": "route",
            }
        )
        workflow.add_edge("respond", END)
        
        return workflow.compile()
    
    async def _understand_request(self, state: DesignState) -> dict:
        """Analyze the user request to understand intent."""
        last_message = state["messages"][-1]
        
        # TODO: Use LLM to extract intent, parameters, cultural context
        # For now, simple keyword matching
        content = last_message.content.lower() if hasattr(last_message, 'content') else ""
        
        detected_intent = "unknown"
        if any(word in content for word in ["blend", "combine", "mix", "breed"]):
            detected_intent = "blend"
        elif any(word in content for word in ["inpaint", "fill", "remove", "replace"]):
            detected_intent = "inpaint"
        elif any(word in content for word in ["style", "transfer", "make it look like"]):
            detected_intent = "style_transfer"
        elif any(word in content for word in ["color", "palette", "recolor"]):
            detected_intent = "color"
        
        return {
            "operation_history": state.get("operation_history", []) + [
                {"step": "understand", "intent": detected_intent}
            ]
        }
    
    async def _route_to_tool(self, state: DesignState) -> dict:
        """Route to the appropriate tool based on understood intent."""
        history = state.get("operation_history", [])
        last_step = history[-1] if history else {}
        intent = last_step.get("intent", "unknown")
        
        return {
            "operation_history": history + [
                {"step": "route", "selected_tool": intent}
            ]
        }
    
    def _should_use_tool(self, state: DesignState) -> Literal["tool", "respond"]:
        """Decide whether to use a tool or respond directly."""
        history = state.get("operation_history", [])
        if history:
            last_step = history[-1]
            if last_step.get("selected_tool") in ["blend", "inpaint", "style_transfer", "color"]:
                return "tool"
        return "respond"
    
    async def _validate_output(self, state: DesignState) -> dict:
        """Validate the output meets cultural and quality standards."""
        # TODO: Run cultural relevance checks
        # TODO: Run quality metrics (PSNR, SSIM)
        
        validation_result = {
            "cultural_score": 0.85,  # Placeholder
            "quality_score": 0.90,   # Placeholder
            "passed": True,
        }
        
        return {
            "operation_history": state.get("operation_history", []) + [
                {"step": "validate", "result": validation_result}
            ]
        }
    
    def _is_valid_output(self, state: DesignState) -> Literal["valid", "retry"]:
        """Check if output validation passed."""
        history = state.get("operation_history", [])
        for step in reversed(history):
            if step.get("step") == "validate":
                if step.get("result", {}).get("passed", False):
                    return "valid"
                break
        return "retry"
    
    async def _generate_response(self, state: DesignState) -> dict:
        """Generate the final response to the user."""
        response = AIMessage(content="Design operation completed successfully.")
        return {"messages": [response]}
    
    async def run(self, user_message: str, image_uri: str | None = None) -> dict:
        """
        Run the design agent with a user message.
        
        Args:
            user_message: User's request
            image_uri: Optional current image to work with
        
        Returns:
            Agent result with generated assets and messages
        """
        initial_state = DesignState(
            messages=[HumanMessage(content=user_message)],
            current_image_uri=image_uri,
            operation_history=[],
            parent_images=[],
            cultural_context="African",
        )
        
        result = await self.graph.ainvoke(initial_state)
        return result


# Factory function
def create_design_agent(model=None) -> DesignAgent:
    """Create a new design agent instance."""
    return DesignAgent(model=model)
