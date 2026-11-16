from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(..., description="Message author role")
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    messages: List[Message] = Field(
        ...,
        min_length=1,
        description="Stateless conversation message history (last N messages)",
    )
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional execution context (e.g., active eventId or location)",
    )
    stream: bool = Field(
        False,
        description="Whether to stream response via Server-Sent Events (SSE)",
    )


class ActionProposal(BaseModel):
    type: str = Field(..., description="Type of proposed action (e.g. 'create_event')")
    payload: Dict[str, Any] = Field(..., description="Draft payload for the action")
    description: str = Field(..., description="Human-readable description of the action")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Assistant text response in Hebrew")
    action_proposals: Optional[List[ActionProposal]] = Field(
        default=None,
        description="List of structured actions proposed for human review",
    )
    tools_executed: Optional[List[str]] = Field(
        default=None,
        description="Names of tools triggered during query resolution",
    )
