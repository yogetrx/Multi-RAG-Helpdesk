
import os
import secrets
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import APIKeyHeader

from helpdesk.generation.answer import generate_answer
from helpdesk.multi_rag import MultiRAG
from helpdesk.router import select_knowledge_bases
from helpdesk.schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
)


app = FastAPI(
    title="Multi-RAG IT Helpdesk Agent",
    description="Search multiple knowledge bases and return cited evidence.",
    version="0.3.0",
)


# API key is supplied through an environment variable.
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def verify_api_key(
    api_key: str | None = Depends(api_key_header),
) -> None:
    expected_api_key = os.getenv("HELPDESK_API_KEY")

    # Fail closed if the server has not been configured securely.
    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured.",
        )

    # Reject missing or incorrect API keys.
    if not api_key or not secrets.compare_digest(
        api_key,
        expected_api_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


@lru_cache(maxsize=1)
def get_rag() -> MultiRAG:
    # Initialize once, on the first /ask request.
    return MultiRAG()


@app.get("/")
def root() -> dict:
    return {
        "message": "Multi-RAG Helpdesk API is running.",
        "next_step": "Send a question to POST /ask.",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        stage="retrieval-api",
    )


@app.post(
    "/ask",
    response_model=AskResponse,
    dependencies=[Depends(verify_api_key)],
)
def ask(request: AskRequest) -> AskResponse:
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question cannot be blank.",
        )

    selected = select_knowledge_bases(question)

    try:
        rag = get_rag()

        evidence = rag.search(
            question,
            knowledge_bases=selected,
            top_k=request.top_k,
        )

        response = generate_answer(question, evidence)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return AskResponse(
        question=question,
        selected_knowledge_bases=selected,
        answer=response["answer"],
        citations=response["citations"],
        grounded=response["grounded"],
        token_usage=response.get("token_usage"),
    )
