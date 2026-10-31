# Multi-RAG IT Helpdesk Agent

A Retrieval-Augmented Generation (RAG) application that routes IT support questions to relevant knowledge bases, retrieves supporting evidence, and generates answers with source citations.

Built with Python, FastAPI, FAISS, and Azure OpenAI.

## Features

- **Multi-knowledge-base routing:** Selects relevant knowledge bases based on the user's question.
- **Semantic retrieval:** Uses vector search to retrieve relevant document content.
- **Evidence fusion:** Combines retrieved evidence for answer generation.
- **Grounded answers:** Generates responses using retrieved context and provides citations.
- **Abstention and safety evaluation:** Includes test cases for unsupported questions, adversarial inputs, and prompt-injection attempts.
- **Performance evaluation:** Measures API latency, token usage, and estimated model cost.
- **Automated tests:** Includes tests for routing, retrieval-related logic, and answer generation.

## Architecture

```text
User Question
     |
     v
FastAPI /ask Endpoint
     |
     v
Knowledge-Base Router
     |
     v
Relevant Knowledge Base(s)
     |
     v
FAISS Retrieval
     |
     v
Evidence Fusion
     |
     v
Azure OpenAI Answer Generation
     |
     v
Answer + Citations + Token Usage
```

## API Security and Rate Limiting

### 1. API Key Authentication

The `/ask` endpoint is protected using API-key authentication.

Clients must provide a valid API key through the `X-API-Key` HTTP request header.

**Example request header:**

```http
X-API-Key: YOUR_API_KEY
```

The application:
- Reads the expected API key from the `HELPDESK_API_KEY` environment variable.
- Rejects missing or invalid API keys with HTTP `401 Unauthorized`.
- Returns HTTP `503 Service Unavailable` if API authentication is not configured.
- Uses `secrets.compare_digest()` for constant-time API-key comparison.

The API key is stored as an Azure Container Apps secret and referenced through an environment variable.

### 2. Rate Limiting

The application uses **SlowAPI** to protect the `/ask` endpoint from excessive requests.

| Configuration | Value |
|---|---|
| Rate limit | 10 requests |
| Time window | 1 minute |
| Rate-limit identity | SHA-256 hash of API key |
| Storage backend | In-memory |
| Exceeding limit | HTTP 429 |

The rate limiter identifies clients using a SHA-256 hash of their API key instead of relying on the source IP address.

This avoids treating different internal proxy addresses as separate clients.

### 3. Rate-Limit Response

When a client exceeds the configured limit, the application returns:

```http
HTTP/1.1 429 Too Many Requests
```

This prevents additional requests from being processed during the restricted period.

### 4. Testing and Verification

Automated tests verify:

- Valid API-key authentication.
- Missing API-key rejection.
- Invalid API-key rejection.
- Missing server-side authentication configuration.
- Rate-limit enforcement.

**Production verification:**

The deployed Azure Container Apps endpoint was tested with 11 consecutive requests.

| Request range | HTTP status | Result |
|---|---:|---|
| Requests 1–10 | 200 | Accepted |
| Request 11 | 429 | Rejected |

The production logs also confirmed the `429 Too Many Requests` response.

### 5. Current Limitations

The current implementation uses in-memory rate-limit storage.

Consequently:
- Rate-limit counters are not shared between multiple application replicas.
- Counters reset when the application process restarts.
- Multiple application instances can enforce separate quotas.

For a distributed production deployment, Redis or an API gateway such as Azure API Management can provide centralized rate limiting.

### 6. Security Considerations

- Never commit API keys or secrets to GitHub.
- Store production secrets using Azure Container Apps secrets.
- Use HTTPS for API communication.
- Keep authentication and rate-limiting configuration outside application source code.


## Knowledge Bases

The sample IT helpdesk knowledge bases cover:

- **Troubleshooting:** VPN Error 809
- **Access Policies:** Azure access guidance
- **IT Documentation:** Support procedures

These documents are illustrative examples, not authoritative organizational policies.

## Technology Stack

- **Language:** Python
- **API:** FastAPI
- **Vector search:** FAISS
- **LLM:** Azure OpenAI
- **Testing:** pytest and custom evaluation scripts

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/yogetrx/Multi-RAG-Helpdesk.git
cd Multi-RAG-Helpdesk
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Use a Python version supported by the project's dependencies.

### 3. Configure environment variables

Create your local `.env` file using `.env.example` as a reference. Fill in the required Azure OpenAI endpoint, API key, and deployment name.

**Never commit your `.env` file or publish API keys.**

### 4. Start the API

```powershell
python -m uvicorn helpdesk.main:app --app-dir src --reload
```

Open the interactive API documentation:

http://127.0.0.1:8000/docs

### 5. Test the API

Check application health:

```http
GET /health
```

Ask a question:

```http
POST /ask
Content-Type: application/json
```

Example request body:


Example response structure (illustrative):

```json
{
  "question": "How can I troubleshoot VPN Error 809?",
  "selected_knowledge_bases": ["troubleshooting"],
  "answer": "Check the relevant troubleshooting steps. [1]",
  "citations": [
    {
      "id": 1,
      "source": "vpn_error_809.txt",
      "knowledge_base": "troubleshooting"
    }
  ],
  "grounded": true,
  "token_usage": {
    "input_tokens": 120,
    "output_tokens": 45,
    "total_tokens": 165
  }
}
```

The values above are illustrative. Actual answers, citations, and token counts depend on the request.


The response includes the question, selected knowledge bases, generated answer, citations, grounding status, and token usage when available.


## Running with Docker

The project includes a portable Docker build using CPU-only PyTorch for semantic embedding generation and retrieval.

### Prerequisites

- Docker Desktop or Docker Engine
- Azure OpenAI endpoint, API key, and deployment name

### 1. Build the Docker image

From the repository root:

```powershell
docker build --no-cache -f Dockerfile.portable -t multi-rag-helpdesk:latest .
```

### 2. Configure environment variables

Create a local `.env` file using `.env.example` as a reference. Add the required Azure OpenAI configuration.

**Never commit `.env` or expose API keys.**

### 3. Run the container

```powershell
docker run --rm -p 8000:8000 --env-file .env multi-rag-helpdesk:latest
```

### 4. Verify the application

Health check:

```text
http://127.0.0.1:8000/health
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### Notes

- The container uses CPU-only PyTorch and does not require a GPU.
- The Docker image includes the application source code and sample knowledge-base documents.
- Azure OpenAI credentials are supplied at runtime through environment variables.
- The image must be built locally before the container can be started.

## Testing and Evaluation

Run the automated test suite:

```powershell
python -m pytest
```

Run the regression evaluation suite:

```powershell
python evaluation/run_regression_suite.py
```

Run the performance evaluation:

```powershell
python evaluation/run_performance_evaluation.py
```

The project includes evaluations for routing and retrieval, answer quality, abstention, grounding, adversarial inputs, and prompt injection.

Evaluation results depend on the test cases and evaluation methods used. Passing these tests does not establish production-level reliability or security.

## Project Status

This is an evolving AI engineering portfolio project. The current implementation focuses on multi-knowledge-base retrieval, cited answer generation, and evaluation. Deployment, monitoring, and broader real-world validation are future improvements.

## Author

**Yogetrx**

GitHub: https://github.com/yogetrx
