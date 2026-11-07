
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class HealthResponse(BaseModel):
    status: str
    stage: str


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=3, ge=1, le=10)

    conversation_history: list[ConversationMessage] = Field(
        default_factory=list,
        max_length=10,
    )


class Citation(BaseModel):
    id: int
    source: str
    knowledge_base: str


class AskResponse(BaseModel):
    question: str
    selected_knowledge_bases: list[str]
    answer: str
    citations: list[Citation]
    grounded: bool
    token_usage: dict | None = None
