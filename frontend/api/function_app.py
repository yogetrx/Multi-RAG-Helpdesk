
import json
import logging
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import azure.functions as func

app = func.FunctionApp()


@app.route(
    route="ask",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def ask(req: func.HttpRequest) -> func.HttpResponse:
    """Securely proxy questions to the Multi-RAG Helpdesk backend."""

    try:
        # Limit incoming request size to 16 KB.
        raw_body = req.get_body()

        if len(raw_body) > 16_384:
            return func.HttpResponse(
                json.dumps({"detail": "Request body is too large."}),
                status_code=413,
                mimetype="application/json",
            )

        data = req.get_json()

        question = data.get("question")
        top_k = data.get("top_k", 3)

        if not isinstance(question, str) or not question.strip():
            return func.HttpResponse(
                json.dumps({"detail": "A valid question is required."}),
                status_code=400,
                mimetype="application/json",
            )

        if len(question) > 4000:
            return func.HttpResponse(
                json.dumps({"detail": "Question is too long."}),
                status_code=400,
                mimetype="application/json",
            )

        if type(top_k) is not int or not 1 <= top_k <= 10:
            return func.HttpResponse(
                json.dumps({"detail": "top_k must be an integer from 1 to 10."}),
                status_code=400,
                mimetype="application/json",
            )

        backend_url = os.environ.get("BACKEND_URL", "").rstrip("/")
        backend_key = os.environ.get("BACKEND_API_KEY", "")

        if not backend_url or not backend_key:
            logging.error("Backend configuration is missing.")
            return func.HttpResponse(
                json.dumps({"detail": "Backend configuration error."}),
                status_code=500,
                mimetype="application/json",
            )

        payload = json.dumps({
            "question": question.strip(),
            "top_k": top_k,
        }).encode("utf-8")

        proxy_request = Request(
            url=f"{backend_url}/ask",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": backend_key,
            },
            method="POST",
        )

        try:
            with urlopen(proxy_request, timeout=35) as response:
                response_body = response.read()
                return func.HttpResponse(
                    body=response_body,
                    status_code=response.status,
                    mimetype="application/json",
                )

        except HTTPError as error:
            # Forward backend validation/authentication errors.
            response_body = error.read()
            return func.HttpResponse(
                body=response_body,
                status_code=error.code,
                mimetype="application/json",
            )

        except (URLError, TimeoutError):
            logging.exception("Could not reach the backend.")
            return func.HttpResponse(
                json.dumps({"detail": "Backend service is temporarily unavailable."}),
                status_code=502,
                mimetype="application/json",
            )

    except ValueError:
        return func.HttpResponse(
            json.dumps({"detail": "Invalid JSON request."}),
            status_code=400,
            mimetype="application/json",
        )

    except Exception:
        logging.exception("Unexpected proxy error.")
        return func.HttpResponse(
            json.dumps({"detail": "Internal server error."}),
            status_code=500,
            mimetype="application/json",
        )


@app.route(
    route="health",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Check whether the Multi-RAG backend is reachable."""

    backend_url = os.environ.get("BACKEND_URL", "").rstrip("/")
    backend_key = os.environ.get("BACKEND_API_KEY", "")

    if not backend_url or not backend_key:
        return func.HttpResponse(
            json.dumps({
                "status": "unavailable",
                "detail": "Backend configuration is missing."
            }),
            status_code=503,
            mimetype="application/json",
        )

    health_request = Request(
        url=f"{backend_url}/health",
        headers={
            "X-API-Key": backend_key,
        },
        method="GET",
    )

    try:
        with urlopen(health_request, timeout=20) as response:
            response_body = response.read()

            return func.HttpResponse(
                body=response_body,
                status_code=response.status,
                mimetype="application/json",
            )

    except HTTPError as error:
        logging.warning("Backend health check returned HTTP %s", error.code)

        return func.HttpResponse(
            json.dumps({
                "status": "unavailable",
                "detail": "Backend health check failed."
            }),
            status_code=503,
            mimetype="application/json",
        )

    except (URLError, TimeoutError):
        logging.exception("Backend health check could not reach the service.")

        return func.HttpResponse(
            json.dumps({
                "status": "unavailable",
                "detail": "Backend service is unreachable."
            }),
            status_code=503,
            mimetype="application/json",
        )