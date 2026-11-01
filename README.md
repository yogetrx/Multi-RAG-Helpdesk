# Multi-RAG IT Helpdesk Agent

An AI-powered IT helpdesk application that routes user questions across multiple knowledge bases, retrieves relevant evidence using semantic search, and generates grounded answers with source citations.

The project combines a **React + TypeScript frontend**, **FastAPI backend**, **FAISS vector search**, and **Azure OpenAI**. It also includes API authentication, rate limiting, automated testing, distributed tracing, and Azure deployment support.

## Architecture

```text
                 User
                  |
                  v
          React + TypeScript UI
                  |
                  v
           Vite API Proxy
                  |
                  v
             FastAPI API
                  |
                  v
          API Authentication
                  |
                  v
            Rate Limiting
                  |
                  v
        Multi-Knowledge-Base Router
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
       Answer + Citations + Metadata
                  |
                  v
             React UI
```

## Key Features

- **Multi-RAG architecture:** Routes questions across multiple knowledge bases.
- **Semantic retrieval:** Uses Sentence Transformers embeddings and FAISS.
- **Evidence fusion:** Combines retrieved evidence for answer generation.
- **Grounded responses:** Generates answers using retrieved context and provides source citations.
- **Abstention:** Supports handling questions that cannot be answered from available evidence.
- **Token usage tracking:** Captures input, output, and total token consumption.
- **API security:** Implements API-key authentication.
- **Rate limiting:** Protects the API using SlowAPI.
- **Structured logging:** Produces JSON logs with request IDs, processing stages, and execution durations.
- **Distributed tracing:** Instruments individual RAG pipeline stages using OpenTelemetry.
- **Azure monitoring integration:** Supports exporting telemetry to Azure Application Insights.
- **Automated testing:** Includes backend tests and evaluation scripts.
- **React dashboard:** Provides an interactive interface for asking questions and viewing answers, citations, grounding status, and token usage.

## Frontend

The frontend is built using:

| Technology | Purpose |
|---|---|
| React | User interface |
| TypeScript | Type safety |
| Vite | Development server and build tooling |
| Tailwind CSS | Styling |
| ESLint | Code quality |

### Frontend capabilities

- Interactive helpdesk dashboard.
- Chat-based question submission.
- Suggested questions.
- Answer rendering.
- Source citation display.
- Grounding status display.
- Token usage information.
- Loading and error states.

**Current limitation:** The knowledge-base navigation in the UI is not yet connected to backend routing. The backend automatically selects relevant knowledge bases based on the question.

## Backend

The backend uses FastAPI to expose the RAG functionality through HTTP endpoints.

### Main API endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Application health check |
| `/ask` | POST | Submit a question to the Multi-RAG pipeline |
| `/docs` | GET | Interactive API documentation |

### Example request

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

- Original question.
- Selected knowledge bases.
- Generated answer.
- Source citations.
- Grounding status.
- Token usage, when available.

## Multi-RAG Pipeline

The backend contains three sample knowledge bases:

| Knowledge base | Example content |
|---|---|
| Troubleshooting | VPN Error 809 |
| Access Policies | Azure access guidance |
| IT Documentation | IT support procedures |

The pipeline works as follows:

1. Receives a user question.
2. Authenticates the API request.
3. Applies rate limiting.
4. Selects relevant knowledge bases.
5. Generates embeddings for retrieval.
6. Searches FAISS for relevant documents.
7. Combines retrieved evidence.
8. Sends the evidence to Azure OpenAI.
9. Checks grounding and generates citations.
10. Returns the answer and metadata.

The sample knowledge-base documents are illustrative examples, not authoritative organizational policies.

## Observability Architecture

The project integrates OpenTelemetry with Azure Monitor and Application Insights.

### OpenTelemetry

The observability implementation is located in:

```text
src/
└── helpdesk/
    └── observability.py
```

The application instruments individual RAG pipeline stages.

| Span | Responsibility |
|---|---|
| `rag.routing` | Knowledge-base selection |
| `rag.initialization` | RAG system initialization |
| `rag.retrieval` | Document retrieval and evidence count |
| `rag.generation` | LLM generation and associated metadata |

These spans help identify which pipeline stages contribute to application latency.

### LLM Generation Monitoring

The `rag.generation` span records custom attributes:

| Attribute | Description |
|---|---|
| `gen_ai.usage.input_tokens` | Input token count |
| `gen_ai.usage.output_tokens` | Output token count |
| `rag.grounded` | Grounding-check result |

### Structured Logging

The application produces structured logs containing:

- Timestamp and log level.
- Request ID.
- HTTP method and path.
- Response status.
- Pipeline stage.
- Selected knowledge bases.
- Evidence count.
- Execution duration.
- Token usage.

Each HTTP request receives a unique request ID, returned in the `X-Request-ID` response header.

### Azure Application Insights

Telemetry export is supported when a valid Application Insights connection string is configured.

The integration supports:

- Request monitoring.
- Dependency tracking.
- Custom RAG spans.
- LLM generation timing.
- Token usage metadata.
- Grounding metadata.
- Distributed operation correlation.

Actual telemetry availability depends on the deployment configuration and successful export.

### Useful KQL Queries

Find RAG generation spans:

```kusto
dependencies
| where timestamp > ago(30m)
| where name == "rag.generation"
| project timestamp, name, duration, success, operation_Id
| order by timestamp desc
```

Inspect generation attributes:

```kusto
dependencies
| where name == "rag.generation"
| extend attributes = customDimensions
| project timestamp, name, duration, attributes
| order by timestamp desc
```

Inspect a distributed trace:

```kusto
dependencies
| where operation_Id == "YOUR_OPERATION_ID"
| project timestamp, name, type, duration, success, operation_ParentId
| order by timestamp asc
```

Replace `YOUR_OPERATION_ID` with the operation ID of the request being investigated.

## API Security and Rate Limiting

### API-Key Authentication

The `/ask` endpoint uses API-key authentication.

Clients must provide a valid key through:

```http
X-API-Key: YOUR_API_KEY
```

The application:

- Reads the expected key from `HELPDESK_API_KEY`.
- Rejects missing or invalid keys with HTTP 401.
- Returns HTTP 503 if authentication is not configured.
- Uses `secrets.compare_digest()` for API-key comparison.

### Rate Limiting

The application uses SlowAPI.

| Configuration | Value |
|---|---|
| Rate limit | 10 requests |
| Time window | 1 minute |
| Rate-limit identity | SHA-256 hash of API key |
| Storage | In-memory |
| Exceeding limit | HTTP 429 |

The in-memory implementation does not share counters across application replicas. Redis or Azure API Management can be considered for centralized rate limiting.

**Frontend security:** The Vite proxy adds the API key on the server side during local development. Never put a permanent backend API key into React code or expose it through a `VITE_` environment variable. A production frontend requires a secure server-side authentication/proxy design.

## Technology Stack

| Category | Technology |
|---|---|
| Frontend | React, TypeScript |
| Frontend tooling | Vite |
| Styling | Tailwind CSS |
| Backend | Python, FastAPI |
| Embeddings | Sentence Transformers |
| Vector search | FAISS |
| LLM | Azure OpenAI |
| API rate limiting | SlowAPI |
| Observability | OpenTelemetry |
| Monitoring | Azure Application Insights |
| Testing | pytest, ESLint |
| Containerization | Docker |
| CI | GitHub Actions |
| Container registry | GitHub Container Registry |
| Cloud deployment | Azure Container Apps |

## Getting Started

### Prerequisites

- Python 3.12
- Node.js compatible with the Vite version in `frontend/package.json`
- npm
- Azure OpenAI deployment
- Git

### 1. Clone the repository

```powershell
git clone https://github.com/yogetrx/Multi-RAG-Helpdesk.git
cd Multi-RAG-Helpdesk
```

### 2. Configure the backend

Create and activate a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create a local `.env` file using `.env.example` as a reference.

Configure:

```env
AZURE_OPENAI_ENDPOINT=YOUR_AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_KEY=YOUR_AZURE_OPENAI_API_KEY
AZURE_OPENAI_CHAT_DEPLOYMENT=YOUR_DEPLOYMENT_NAME
HELPDESK_API_KEY=YOUR_LOCAL_API_KEY
```

For Application Insights telemetry:

```env
APPLICATIONINSIGHTS_CONNECTION_STRING=YOUR_APPLICATION_INSIGHTS_CONNECTION_STRING
```

Telemetry export is disabled when the connection string is missing.

Never commit `.env` files or expose credentials in source code.

### 3. Start the backend

From the repository root:

```powershell
python -m uvicorn helpdesk.main:app --app-dir src --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

### 4. Configure and start the frontend

Open a second terminal:

```powershell
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
HELPDESK_BACKEND_URL=http://127.0.0.1:8000
HELPDESK_API_KEY=YOUR_LOCAL_API_KEY
```

Use the same local API key configured in the backend `.env`.

Start the frontend:

```powershell
npm run dev
```

Open:

```text
http://localhost:5173
```

The Vite development proxy forwards `/api` requests to the backend and attaches the API key server-side.

Keep `.env.local` private. It must never be committed.

### 5. Frontend quality checks

Run ESLint:

```powershell
npm run lint
```

Run a production build:

```powershell
npm run build
```

Preview the production build locally:

```powershell
npm run preview
```

## Running with Docker

The backend includes a portable Docker build using CPU-only PyTorch.

Build:

```powershell
docker build --no-cache -f Dockerfile.portable -t multi-rag-helpdesk:latest .
```

Run:

```powershell
docker run --rm -p 8000:8000 --env-file .env multi-rag-helpdesk:latest
```

Verify:

```text
http://127.0.0.1:8000/health
```

## Testing and Evaluation

Run backend tests from the repository root:

```powershell
python -m pytest -q
```

Run regression evaluation:

```powershell
python evaluation/run_regression_suite.py
```

Run performance evaluation:

```powershell
python evaluation/run_performance_evaluation.py
```

The evaluation suite covers routing, retrieval, answer quality, abstention, grounding, adversarial inputs, and prompt injection.

Passing tests does not establish production-level reliability or security.

## CI/CD and Deployment

The backend is deployed using Azure Container Apps.

The project uses GitHub Actions to run automated tests and build and publish the Docker image to GitHub Container Registry.

**Important:** The current GitHub Actions workflow does not automatically deploy the new image to Azure Container Apps. Azure deployment is a separate step.

Production credentials are configured separately from source code.

The React frontend currently runs locally. Production frontend hosting and a secure production authentication/proxy architecture remain future work.

## Project Status

Implemented:

- Multi-knowledge-base RAG architecture.
- Semantic retrieval using FAISS.
- Azure OpenAI answer generation.
- Citation and grounding checks.
- API-key authentication.
- Request rate limiting.
- Structured application logging.
- OpenTelemetry distributed tracing.
- Application Insights integration.
- Docker-based application packaging.
- Azure Container Apps backend deployment.
- GitHub Actions CI workflow.
- React and TypeScript frontend.
- Frontend-to-backend integration through the local Vite proxy.
- Automated backend tests.

Future improvements:

- Connect knowledge-base selection in the UI to actual backend routing.
- Implement production-safe frontend authentication and API proxying.
- Deploy the React frontend.
- Verify production telemetry export.
- Introduce centralized rate limiting.
- Expand monitoring dashboards and evaluation pipelines.
- Add more knowledge bases.

## Author

**Yogetrx**

GitHub: https://github.com/yogetrx