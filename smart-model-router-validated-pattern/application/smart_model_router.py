#!/usr/bin/env python3
"""Smart Model Router: Llama classifies; MaaS serves the selected model.

Environment:
  MAAS_URL or MAAS_BASE_URL: MaaS OpenAI-compatible base URL
  MAAS_API_KEY: MaaS bearer token (read from an OpenShift Secret)
  LLAMA_BASE_URL: Llama OpenAI-compatible base URL (default: in-cluster service)
  LLAMA_MODEL: model name exposed by Llama (default: llama)
  LLAMA_TIMEOUT: classification timeout in seconds (default: 8)
  MAAS_TLS_VERIFY: verify MaaS TLS certificate (default: true)
  PORT or ROUTER_PORT: HTTP listen port (default: 8080)
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

MAAS_BASE_URL = os.environ.get(
    "MAAS_BASE_URL",
    os.environ.get(
        "MAAS_URL",
        "https://maas.example.com",
    ),
).rstrip("/")
ROUTER_PORT = int(os.environ.get("ROUTER_PORT", os.environ.get("PORT", "8080")))
MAAS_API_KEY = os.environ.get("MAAS_API_KEY", "")
MAAS_TLS_VERIFY = os.environ.get("MAAS_TLS_VERIFY", "true").lower() in (
    "true", "1", "yes"
)
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "300"))

LLAMA_BASE_URL = os.environ.get(
    "LLAMA_BASE_URL",
    "http://llama-predictor.ai-ops.svc.cluster.local",
).rstrip("/")
LLAMA_MODEL = os.environ.get("LLAMA_MODEL", "llama")
LLAMA_TIMEOUT = float(os.environ.get("LLAMA_TIMEOUT", "8"))

MODEL_MAP = {
    "simple": os.environ.get(
        "SIMPLE_MODEL",
        "publishers/agent/models/gpt-oss-20b",
    ),
    "complex": os.environ.get(
        "COMPLEX_MODEL",
        "publishers/agent/models/qwen3-32b",
    ),
}
HTML_FILE = Path("/app/index.html")

COMPLEX_PATTERNS = [
    r"\bstep[- ]by[- ]step\b", r"\bstep by step\b",
    r"\barchitecture\b", r"\barchitectural\b", r"\btrade[- ]offs?\b",
    r"\bfailure handling\b", r"\broot cause\b",
    r"\btroubleshoot(?:ing)?\b", r"\bdebug(?:ging)?\b",
    r"\bcompare\b", r"\bcomparison\b", r"\banaly[sz]e\b",
    r"\banalysis\b", r"\bcomprehensive\b", r"\bin detail\b",
    r"\bmultiple steps\b", r"\bdesign\b", r"\bimplement(?:ation)?\b",
    r"\boptimi[sz](?:e|ation)\b", r"\bsecurity\b", r"\bdistributed\b",
    r"\bscalab(?:le|ility)\b", r"\bhow does .+ work\b",
    r"\bspiega(?:mi)? nel dettaglio\b", r"\bpasso dopo passo\b",
    r"\barchitettura\b", r"\bprogettazione\b", r"\banalizza\b",
    r"\banalisi\b", r"\bconfronta\b", r"\bconfronto\b",
    r"\bapprofondit[oa]\b", r"\bgestione degli errori\b",
    r"\bcausa principale\b", r"\brisoluzione dei problemi\b",
    r"\bottimizzazione\b", r"\bsicurezza\b", r"\bdistribuit[oa]\b",
]
COMPLEX_REGEX = [re.compile(p, re.IGNORECASE) for p in COMPLEX_PATTERNS]


def extract_user_text(messages):
    """Extract the most recent user message from an OpenAI chat request."""
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                str(item.get("text", ""))
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            return " ".join(parts)
        return str(content)
    return ""


def classify_request_heuristic(text):
    """Safe fallback: return (route, explanation) without calling Llama."""
    text = (text or "").strip()
    words = re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)
    if len(words) >= 100:
        return "complex", "Fallback: long request"
    if len(words) >= 45:
        return "complex", "Fallback: detailed request"
    if any(pattern.search(text) for pattern in COMPLEX_REGEX):
        return "complex", "Fallback: complexity keywords detected"
    if text.count("\n") >= 5:
        return "complex", "Fallback: multi-part request"
    return "simple", "Fallback: short or straightforward request"


def _ssl_context(verify):
    return ssl.create_default_context() if verify else ssl._create_unverified_context()


def _post_json(url, payload, headers=None, timeout=8, context=None):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(
        url, data=data, headers=req_headers, method="POST"
    )
    kwargs = {"timeout": timeout}
    if url.lower().startswith("https://"):
        kwargs["context"] = context or ssl.create_default_context()
    with urllib.request.urlopen(request, **kwargs) as response:
        raw = response.read()
        return response.status, json.loads(raw.decode("utf-8"))


def classify_request_llama(text):
    """Ask Llama for SIMPLE/COMPLEX. Raises on errors so caller can fallback."""
    if not (text or "").strip():
        return "simple", "Llama classified an empty/short request"
    prompt = (
        "Classify the user's request for model routing. "
        "Return exactly one word: SIMPLE or COMPLEX. "
        "SIMPLE means a short, direct, factual, or routine request. "
        "COMPLEX means multi-step reasoning, detailed analysis, architecture, "
        "debugging, troubleshooting, comparisons, implementation, or a long "
        "technical task. Do not answer the user's request; only classify it."
    )
    payload = {
        "model": LLAMA_MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": (text or "")[:12000]},
        ],
        "temperature": 0,
        "max_tokens": 8,
        "stream": False,
    }
    _, data = _post_json(
        LLAMA_BASE_URL + "/v1/chat/completions",
        payload,
        timeout=LLAMA_TIMEOUT,
    )
    choices = data.get("choices", [])
    if not choices or not isinstance(choices[0], dict):
        raise ValueError("Llama response has no choices")
    message = choices[0].get("message", {})
    content = message.get("content", "") if isinstance(message, dict) else ""
    if isinstance(content, list):
        content = " ".join(
            str(x.get("text", "")) for x in content if isinstance(x, dict)
        )
    label = str(content).strip().upper()
    # Be strict: don't accept arbitrary output or a label embedded in prose.
    match = re.fullmatch(r"[\s`*]*(SIMPLE|COMPLEX)[\s`*.,!]*", label)
    if not match:
        raise ValueError("Llama returned an invalid classification")
    route = "simple" if match.group(1) == "SIMPLE" else "complex"
    return route, "Llama classification: " + match.group(1)


def classify_request(text):
    """Use Llama first; on any classification failure use the heuristic."""
    try:
        return classify_request_llama(text)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            ValueError, KeyError, TypeError, json.JSONDecodeError, OSError) as exc:
        route, reason = classify_request_heuristic(text)
        # Keep diagnostics useful without exposing prompts or credentials.
        return route, reason + " (Llama unavailable: " + type(exc).__name__ + ")"


class UpstreamHTTPError(Exception):
    def __init__(self, status_code, response_data):
        super().__init__(str(response_data))
        self.status_code = status_code
        self.response_data = response_data


def call_maas(request_data, model):
    """Forward the OpenAI-compatible request to MaaS."""
    if not MAAS_API_KEY:
        raise RuntimeError("MAAS_API_KEY is not configured in the deployment")
    payload = dict(request_data)
    payload["model"] = model
    payload["stream"] = False
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        MAAS_BASE_URL + "/v1/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + MAAS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT,
            context=_ssl_context(MAAS_TLS_VERIFY),
        ) as response:
            response_body = response.read()
            status_code = response.status
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        try:
            error_data = json.loads(error_body)
        except (ValueError, TypeError):
            error_data = {"message": error_body}
        raise UpstreamHTTPError(exc.code, error_data) from exc
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    try:
        response_data = json.loads(response_body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("MaaS returned a response that is not valid JSON") from exc
    if not isinstance(response_data, dict):
        raise RuntimeError("MaaS returned JSON that is not an object")
    return status_code, response_data, elapsed_ms


def _send_json(handler, status_code, data):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.end_headers()
    handler.wfile.write(body)


def _send_html(handler):
    if not HTML_FILE.is_file():
        _send_json(handler, 404, {"error": {"message": "UI file not found"}})
        return
    body = HTML_FILE.read_bytes()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    server_version = "SmartModelRouter/1.2"

    def log_message(self, fmt, *args):
        # Standard access logs only; never log request bodies or credentials.
        super().log_message(fmt, *args)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            _send_json(self, 200, {"status": "ok"})
        elif path in ("/", "/index.html"):
            _send_html(self)
        elif path == "/v1/models":
            _send_json(self, 200, {
                "object": "list",
                "data": [
                    {"id": model, "object": "model", "owned_by": "smart-model-router"}
                    for model in MODEL_MAP.values()
                ],
            })
        else:
            _send_json(self, 404, {"error": {"message": "Not found"}})

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/v1/chat/completions", "/chat/completions"):
            _send_json(self, 404, {"error": {"message": "Not found"}})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                _send_json(self, 400, {"error": {"message": "Request body is required"}})
                return
            raw_body = self.rfile.read(length)
            try:
                request_data = json.loads(raw_body.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                _send_json(self, 400, {"error": {"message": "Invalid JSON request body"}})
                return
            if not isinstance(request_data, dict):
                _send_json(self, 400, {"error": {"message": "JSON body must be an object"}})
                return
            messages = request_data.get("messages")
            if not isinstance(messages, list) or not messages:
                _send_json(self, 400, {
                    "error": {"message": "A non-empty messages array is required"}
                })
                return

            user_text = extract_user_text(messages)
            route, decision = classify_request(user_text)
            model = MODEL_MAP[route]
            status_code, response_data, elapsed_ms = call_maas(request_data, model)
            response_data["router"] = {
                "route": route,
                "model": model,
                "selected_model": model,
                "decision": decision,
                "response_time": elapsed_ms,
            }
            _send_json(self, status_code, response_data)
        except UpstreamHTTPError as exc:
            _send_json(self, exc.status_code, exc.response_data
                       if isinstance(exc.response_data, dict)
                       else {"error": {"message": str(exc.response_data)}})
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            _send_json(self, 502, {
                "error": {"message": "Upstream request failed",
                          "type": "upstream_error",
                          "detail": type(exc).__name__}
            })
        except Exception as exc:
            # Do not return stack traces or secrets to clients.
            print("Router request failed: " + type(exc).__name__, flush=True)
            _send_json(self, 500, {
                "error": {"message": "Internal router error", "type": "internal_error"}
            })


def main():
    print("Starting Smart Model Router on port " + str(ROUTER_PORT), flush=True)
    print("MaaS endpoint: " + MAAS_BASE_URL, flush=True)
    print("Llama endpoint: " + LLAMA_BASE_URL, flush=True)
    print("Simple model: " + MODEL_MAP["simple"], flush=True)
    print("Complex model: " + MODEL_MAP["complex"], flush=True)
    server = ThreadingHTTPServer(("0.0.0.0", ROUTER_PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
