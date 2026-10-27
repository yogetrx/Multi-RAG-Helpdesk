
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    stage: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=3, ge=1, le=10)


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
    # New field for performance evaluation
    token_usage: dict | None = None