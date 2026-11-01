# Multi-RAG IT Helpdesk Agent

An AI-powered IT helpdesk application that routes user questions across multiple knowledge bases, retrieves relevant evidence using semantic search, and generates grounded answers with source citations.

Built with Python, FastAPI, FAISS, Azure OpenAI, and OpenTelemetry. The application also integrates with Azure Application Insights for monitoring, distributed tracing, and observability.

## Features

- **Multi-knowledge-base routing:** Selects relevant knowledge bases based on the user's question.
- **Semantic retrieval:** Uses Sentence Transformers embeddings and FAISS vector search.
- **Evidence fusion:** Combines retrieved evidence for answer generation.
- **Grounded answers:** Generates responses using retrieved context and provides source citations.
- **Abstention and safety evaluation:** Includes tests for unsupported questions, adversarial inputs, and prompt-injection attempts.
- **Token usage tracking:** Captures input, output, and total token consumption.
- **API security:** Implements API-key authentication and request rate limiting.
- **Structured logging:** Produces JSON logs containing request IDs, processing stages, and execution durations.
- **Distributed tracing:** Instruments individual RAG pipeline stages using OpenTelemetry.
- **Azure monitoring:** Exports telemetry to Azure Application Insights.
- **Automated testing:** Includes authentication, logging, routing, and application tests.

## Architecture

```text
                    User Question
                         |
                         v
                  FastAPI /ask API
                         |
                         v
                 API Authentication
                         |
                         v
                  Rate Limiting
                         |
                         v
                Knowledge-Base Router
                         |
                         v
                 Relevant Knowledge
                    Base Selection
                         |
                         v
                   FAISS Retrieval
                         |
                         v
                   Evidence Fusion
                         |
                         v
                Azure OpenAI Generation
                         |
                         v
              Grounding and Citation Checks
                         |
                         v
             Answer + Citations + Token Usage
```

## Observability Architecture

The application uses OpenTelemetry to monitor the execution of its RAG pipeline and Azure Application Insights to collect and analyze telemetry.

### 1. OpenTelemetry Integration

The project uses Microsoft's OpenTelemetry distribution to configure telemetry collection and Azure Monitor integration.

The observability implementation is located in:

```text
src/
└── helpdesk/
    └── observability.py
```

The application initializes observability before obtaining its application tracer.

Telemetry is exported when a valid Application Insights connection string is configured.

### 2. RAG Pipeline Distributed Tracing

The application creates custom spans around individual processing stages.

| Span | Responsibility |
|---|---|
| `rag.routing` | Records knowledge-base selection. |
| `rag.initialization` | Records RAG system initialization. |
| `rag.retrieval` | Records document retrieval and evidence count. |
| `rag.generation` | Records LLM generation and associated metadata. |

These spans help identify which stage contributes to application latency.

### 3. LLM Generation Monitoring

The `rag.generation` span records custom attributes:

| Attribute | Description |
|---|---|
| `gen_ai.usage.input_tokens` | Number of input tokens. |
| `gen_ai.usage.output_tokens` | Number of output tokens. |
| `rag.grounded` | Whether the generated answer passed the application's grounding check. |

The application also receives automatic model and HTTP dependency telemetry through its instrumentation.

### 4. Structured JSON Logging

The application generates structured logs containing information such as:

- Timestamp
- Log level
- Request ID
- HTTP method and path
- Response status
- Pipeline stage
- Selected knowledge bases
- Evidence count
- Execution duration
- Input and output token usage

Each HTTP request receives a unique request ID, which is also returned in the `X-Request-ID` response header.

### 5. Azure Application Insights

Application telemetry is exported to Azure Application Insights.

The monitoring implementation supports:

- Request monitoring
- Dependency tracking
- Custom RAG spans
- LLM generation timing
- Token usage metadata
- Grounding metadata
- Distributed operation correlation

**Observed verification:** The generation span and its custom attributes were successfully observed in Application Insights. The distributed trace also showed the relationship between the custom generation span and the model dependency.

### 6. Useful Application Insights KQL Queries

**Find RAG generation spans:**

```kusto
dependencies
| where timestamp > ago(30m)
| where name == "rag.generation"
| project timestamp, name, duration, success, operation_Id
| order by timestamp desc
```

**Inspect generation attributes:**

```kusto
dependencies
| where name == "rag.generation"
| extend attributes = customDimensions
| project timestamp, name, duration, attributes
| order by timestamp desc
```

**Inspect an entire distributed trace:**

```kusto
dependencies
| where operation_Id == "YOUR_OPERATION_ID"
| project timestamp, name, type, duration, success, operation_ParentId
| order by timestamp asc
```

Replace `YOUR_OPERATION_ID` with the operation ID of the request being investigated.

## API Security and Rate Limiting

### 1. API Key Authentication

The `/ask` endpoint is protected using API-key authentication.

Clients must provide a valid API key through the `X-API-Key` HTTP request header.

```http
X-API-Key: YOUR_API_KEY
```

The application:

- Reads the expected API key from `HELPDESK_API_KEY`.
- Rejects missing or invalid API keys with HTTP `401 Unauthorized`.
- Returns HTTP `503 Service Unavailable` if authentication is not configured.
- Uses `secrets.compare_digest()` for API-key comparison.

### 2. Rate Limiting

The application uses SlowAPI.

| Configuration | Value |
|---|---|
| Rate limit | 10 requests |
| Time window | 1 minute |
| Rate-limit identity | SHA-256 hash of API key |
| Storage backend | In-memory |
| Exceeding limit | HTTP 429 |

The in-memory implementation has limitations when running multiple application replicas because counters are not shared.

Redis or Azure API Management can be considered for centralized rate limiting.

## Knowledge Bases

The sample IT helpdesk knowledge bases cover:

- **Troubleshooting:** VPN Error 809.
- **Access Policies:** Azure access guidance.
- **IT Documentation:** Support procedures.

These documents are illustrative examples, not authoritative organizational policies.

## Technology Stack

| Category | Technology |
|---|---|
| Language | Python |
| API framework | FastAPI |
| Vector search | FAISS |
| Embeddings | Sentence Transformers |
| LLM | Azure OpenAI |
| API rate limiting | SlowAPI |
| Observability | OpenTelemetry |
| Monitoring | Azure Application Insights |
| Testing | pytest |
| Containerization | Docker |
| Cloud deployment | Azure Container Apps |

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/yogetrx/Multi-RAG-Helpdesk.git
cd Multi-RAG-Helpdesk
```

### 2. Create a virtual environment

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a local `.env` file using `.env.example` as a reference.

Configure the required application settings:

```env
AZURE_OPENAI_ENDPOINT=YOUR_AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY=YOUR_AZURE_OPENAI_API_KEY
AZURE_OPENAI_CHAT_DEPLOYMENT=YOUR_DEPLOYMENT_NAME

HELPDESK_API_KEY=YOUR_LOCAL_API_KEY
```

For Azure Application Insights telemetry, configure:

```env
APPLICATIONINSIGHTS_CONNECTION_STRING=YOUR_APPLICATION_INSIGHTS_CONNECTION_STRING
```

Observability export is disabled when the Application Insights connection string is missing.

Never commit `.env` or expose credentials in source code.

### 4. Start the API

```powershell
python -m uvicorn helpdesk.main:app --app-dir src --reload
```

Interactive API documentation:

http://127.0.0.1:8000/docs

### 5. Check application health

```http
GET /health
```

### 6. Ask a question

```http
POST /ask
Content-Type: application/json
X-API-Key: YOUR_API_KEY
```

Request body:

```json
{
  "question": "How do I troubleshoot VPN Error 809?",
  "top_k": 3
}
```

The response contains:

- Original question
- Selected knowledge bases
- Generated answer
- Source citations
- Grounding status
- Token usage, when available

## Running with Docker

The project includes a portable Docker build using CPU-only PyTorch.

### Build the image

```powershell
docker build --no-cache -f Dockerfile.portable -t multi-rag-helpdesk:latest .
```

### Run the container

```powershell
docker run --rm -p 8000:8000 --env-file .env multi-rag-helpdesk:latest
```

Verify the application:

http://127.0.0.1:8000/health

## Testing and Evaluation

Run the automated tests:

```powershell
python -m pytest -q
```

Run the regression evaluation:

```powershell
python evaluation/run_regression_suite.py
```

Run the performance evaluation:

```powershell
python evaluation/run_performance_evaluation.py
```

The evaluation suite covers routing, retrieval, answer quality, abstention, grounding, adversarial inputs, and prompt injection.

Passing tests does not establish production-level reliability or security.

## Deployment

The application has been deployed using Azure Container Apps.

The deployed application uses Azure OpenAI for answer generation and Azure Application Insights for monitoring.

Production credentials are configured separately from the source code.

## Project Status

This is an evolving AI engineering portfolio project.

Current implementation includes:

- Multi-knowledge-base RAG architecture.
- Semantic retrieval using FAISS.
- Azure OpenAI answer generation.
- Citation and grounding checks.
- API authentication and rate limiting.
- Structured application logging.
- OpenTelemetry distributed tracing.
- Azure Application Insights integration.
- Docker-based application packaging.
- Azure Container Apps deployment.
- Automated testing and evaluation.

Future improvements can include centralized rate limiting, expanded monitoring dashboards, stronger evaluation pipelines, and additional knowledge bases.

## Author

**Yogetrx**

GitHub: https://github.com/yogetrx