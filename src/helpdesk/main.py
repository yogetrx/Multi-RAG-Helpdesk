
from functools import lru_cache

from fastapi import FastAPI, HTTPException

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
    version="0.2.0",
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
    return HealthResponse(status="ok", stage="retrieval-api")



@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return AskResponse(
        question=question,
        selected_knowledge_bases=selected,
        answer=response["answer"],
        citations=response["citations"],
        grounded=response["grounded"],
        token_usage=response.get("token_usage"),
    )
