
import uuid
import os
import secrets
import hashlib
import logging
import time
import json

from datetime import datetime, timezone
from functools import lru_cache

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    status,
)

from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from opentelemetry import trace

from dotenv import load_dotenv

from helpdesk.observability import configure_observability
from helpdesk.generation.answer import (
    generate_answer,
    contextualize_question,
)
from helpdesk.multi_rag import MultiRAG
from helpdesk.router import match_knowledge_bases

from helpdesk.schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
)

load_dotenv()


# --------------------------------------------------
# API RATE LIMITING
# --------------------------------------------------

def get_api_key_identity(request: Request) -> str:
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return "anonymous"

    return hashlib.sha256(
        api_key.encode("utf-8")
    ).hexdigest()


limiter = Limiter(
    key_func=get_api_key_identity,
    storage_uri="memory://",
)


# --------------------------------------------------
# OPENTELEMETRY INITIALIZATION
# --------------------------------------------------

configure_observability()

tracer = trace.get_tracer("helpdesk.rag")


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="Multi-RAG IT Helpdesk Agent",
    description="Search multiple knowledge bases and return cited evidence.",
    version="0.5.0",
)


# --------------------------------------------------
# CORS CONFIGURATION
# --------------------------------------------------

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# --------------------------------------------------
# STRUCTURED JSON LOGGING
# --------------------------------------------------

class JSONFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:

        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in (
            "request_id",
            "method",
            "path",
            "status",
            "duration_seconds",
            "stage",
            "selected_knowledge_bases",
            "evidence_count",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "answer_mode",
        ):
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        if record.exc_info:
            log_data["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(log_data)


# --------------------------------------------------
# APPLICATION LOGGER
# --------------------------------------------------

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())

logger = logging.getLogger("helpdesk")
logger.setLevel(logging.INFO)
logger.handlers.clear()
logger.addHandler(handler)
logger.propagate = False


# --------------------------------------------------
# REQUEST ID AND REQUEST LOGGING MIDDLEWARE
# --------------------------------------------------

@app.middleware("http")
async def add_request_id(request: Request, call_next):

    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    request.state.request_id = request_id

    try:

        response = await call_next(request)

        duration = time.perf_counter() - start_time

        logger.info(
            "HTTP request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_seconds": round(duration, 4),
            },
        )

        response.headers["X-Request-ID"] = request_id

        return response

    except Exception:

        duration = time.perf_counter() - start_time

        logger.exception(
            "Unexpected HTTP request error",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_seconds": round(duration, 4),
            },
        )

        raise


# --------------------------------------------------
# SLOWAPI REGISTRATION
# --------------------------------------------------

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)


# --------------------------------------------------
# API KEY AUTHENTICATION
# --------------------------------------------------

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def verify_api_key(
    api_key: str | None = Depends(api_key_header),
) -> None:

    expected_api_key = os.getenv("HELPDESK_API_KEY")

    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured.",
        )

    if not api_key or not secrets.compare_digest(
        api_key,
        expected_api_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


# --------------------------------------------------
# RAG INITIALIZATION
# --------------------------------------------------

@lru_cache(maxsize=1)
def get_rag() -> MultiRAG:

    return MultiRAG()


# --------------------------------------------------
# API ENDPOINTS
# --------------------------------------------------

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


# --------------------------------------------------
# ASK ENDPOINT
# --------------------------------------------------

@app.post(
    "/ask",
    response_model=AskResponse,
    dependencies=[Depends(verify_api_key)],
)
@limiter.limit("10/minute")
def ask(request: Request, payload: AskRequest) -> AskResponse:

    pipeline_start = time.perf_counter()
    request_id = request.state.request_id

    question = payload.question.strip()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question cannot be blank.",
        )

    # Convert validated Pydantic history into dictionaries.
    conversation_history = [
        message.model_dump()
        for message in payload.conversation_history
    ]

    # Use recent user messages to resolve short follow-up questions.
    previous_user_questions = [
        message["content"]
        for message in conversation_history
        if message["role"] == "user"
    ][-4:]

    # Contextualize the current question for document retrieval.
    retrieval_question = contextualize_question(
        query=question,
        conversation_history=conversation_history,
    )

    # Use the contextualized question for knowledge-base routing.
    routing_context = " ".join(
        previous_user_questions + [retrieval_question]
    )

    try:

        # --------------------------------------------------
        # STAGE 1: ROUTING
        # --------------------------------------------------

        routing_start = time.perf_counter()

        with tracer.start_as_current_span("rag.routing") as span:

            selected = match_knowledge_bases(routing_context)

            mode = "rag" if selected else "general"

            span.set_attribute("rag.answer_mode", mode)

            span.set_attribute(
                "rag.selected_knowledge_bases",
                ",".join(selected),
            )

        routing_duration = time.perf_counter() - routing_start

        logger.info(
            "Request routing completed",
            extra={
                "request_id": request_id,
                "stage": "routing",
                "answer_mode": mode,
                "selected_knowledge_bases": selected,
                "duration_seconds": round(routing_duration, 4),
            },
        )

        # --------------------------------------------------
        # STAGE 2: RETRIEVAL ONLY FOR RAG MODE
        # --------------------------------------------------

        evidence = []

        if mode == "rag":

            initialization_start = time.perf_counter()

            with tracer.start_as_current_span(
                "rag.initialization"
            ) as span:

                rag = get_rag()

                initialization_duration = (
                    time.perf_counter() - initialization_start
                )

                span.set_attribute(
                    "rag.initialization.duration_seconds",
                    initialization_duration,
                )

            retrieval_start = time.perf_counter()

            with tracer.start_as_current_span(
                "rag.retrieval"
            ) as span:

                evidence = rag.search(
                    retrieval_question,
                    knowledge_bases=selected,
                    top_k=payload.top_k,
                )

                span.set_attribute(
                    "rag.evidence_count",
                    len(evidence),
                )

                span.set_attribute(
                    "rag.selected_knowledge_bases",
                    ",".join(selected),
                )

            retrieval_duration = (
                time.perf_counter() - retrieval_start
            )

            logger.info(
                "Document retrieval completed",
                extra={
                    "request_id": request_id,
                    "stage": "retrieval",
                    "evidence_count": len(evidence),
                    "selected_knowledge_bases": selected,
                    "duration_seconds": round(
                        retrieval_duration, 4
                    ),
                },
            )

        # --------------------------------------------------
        # STAGE 3: ANSWER GENERATION
        # --------------------------------------------------

        generation_start = time.perf_counter()

        with tracer.start_as_current_span(
            "rag.generation"
        ) as span:

            response = generate_answer(
                query=question,
                evidence=evidence,
                conversation_history=conversation_history,
                mode=mode,
            )

            token_usage = response.get("token_usage") or {}

            span.set_attribute(
                "gen_ai.usage.input_tokens",
                token_usage.get("input_tokens") or 0,
            )

            span.set_attribute(
                "gen_ai.usage.output_tokens",
                token_usage.get("output_tokens") or 0,
            )

            span.set_attribute(
                "rag.grounded",
                bool(response.get("grounded")),
            )

            span.set_attribute("rag.answer_mode", mode)

        generation_duration = (
            time.perf_counter() - generation_start
        )

        logger.info(
            "Answer generation completed",
            extra={
                "request_id": request_id,
                "stage": "generation",
                "answer_mode": mode,
                "duration_seconds": round(
                    generation_duration, 4
                ),
                "input_tokens": token_usage.get("input_tokens"),
                "output_tokens": token_usage.get("output_tokens"),
                "total_tokens": token_usage.get("total_tokens"),
            },
        )

        # --------------------------------------------------
        # COMPLETE PIPELINE
        # --------------------------------------------------

        pipeline_duration = time.perf_counter() - pipeline_start

        logger.info(
            "Hybrid AI pipeline completed",
            extra={
                "request_id": request_id,
                "stage": "complete",
                "answer_mode": mode,
                "duration_seconds": round(
                    pipeline_duration, 4
                ),
                "evidence_count": len(evidence),
                "selected_knowledge_bases": selected,
            },
        )

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
