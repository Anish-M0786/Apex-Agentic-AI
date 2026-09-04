# Apex

Apex is a local-first AI productivity platform — FastAPI backend, Next.js frontend, Qwen 2.5 3B via Ollama. Fully local, no cloud dependencies.

## Development environment

### Prerequisites

- Python 3.12+
- Node.js 20+
- [Ollama](https://ollama.com) installed and running
- `qwen2.5:3b` model pulled

```powershell
ollama pull qwen2.5:3b
```

### Backend setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

**Terminal 1 — Backend:**

```powershell
cd "C:\TENNUX - Agent"
python -m uvicorn backend.main:app --reload
```

Backend: `http://127.0.0.1:8000`

### Frontend setup

```powershell
cd frontend
npm install
```

**Terminal 2 — Frontend:**

```powershell
cd "C:\TENNUX - Agent\frontend"
npm run dev
```

Frontend: `http://localhost:3000`

### Verification

```powershell
# Health check
Invoke-RestMethod http://127.0.0.1:8000/health

# Chat test
Invoke-RestMethod http://127.0.0.1:8000/api/chat -Method Post -ContentType 'application/json' -Body '{"message":"Explain deadlock in operating systems"}'

# Backend tests
python -m pytest -q

# Frontend tests
cd frontend; npm test; npm run lint; npm run build
```

## Phase 2 tools

The registry exposes `create_pdf`, `create_excel`, `create_ppt`, and `create_document`. Tool requests such as `Create a PDF about binary search` are routed through the executor. Generated files are stored under `data/outputs/` and can be downloaded from `/api/files/{filename}`. Filenames are sanitized and traversal is rejected.

## Phase 4: Document Intelligence

Place uploaded or previously ingested source files in `data/documents/` using a safe document ID as the basename (for example, `operating-systems.pdf` or `operating-systems.txt`). The intelligence endpoints use that ID without its extension. PDF extraction uses `pypdf`; text formats are read as UTF-8. Generated results are cached in `data/intelligence_cache.sqlite` using a deterministic hash of the source and request configuration.

Examples:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/intelligence/summarize -Method Post -ContentType 'application/json' -Body '{"document_id":"operating-systems","mode":"balanced"}'
Invoke-RestMethod http://127.0.0.1:8000/api/intelligence/semester-notes -Method Post -ContentType 'application/json' -Body '{"document_id":"operating-systems"}'
Invoke-RestMethod http://127.0.0.1:8000/api/intelligence/quiz -Method Post -ContentType 'application/json' -Body '{"document_id":"operating-systems","count":20,"difficulty":"mixed"}'
```

Available POST endpoints are `/api/intelligence/summarize`, `/topics`, `/notes`, `/semester-notes`, `/study-guide`, `/flashcards`, `/quiz`, and `/questions`. Most generated-result endpoints accept optional `format` and `filename` query parameters for `pdf`, `docx`, `pptx`, or `xlsx` exports; quiz and flashcards are especially suitable for XLSX.

## Phase 5: Code Intelligence

Apex provides CPU-friendly, static AI-assisted code analysis for Python, C, C++, Java, JavaScript, TypeScript, SQL, HTML, CSS, and Bash. API endpoints are `/api/code/generate`, `/explain`, `/debug`, `/refactor`, `/review`, `/tests`, `/document`, and `/complexity`.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/code/explain -Method Post -ContentType 'application/json' -Body '{"language":"python","code":"def add(a, b): return a + b","level":"beginner"}'
Invoke-RestMethod http://127.0.0.1:8000/api/code/generate -Method Post -ContentType 'application/json' -Body '{"language":"python","task":"Implement binary search","constraints":"Use an iterative function"}'
```

`CODE_MAX_INPUT_CHARS` (default `30000`) bounds source-code prompt size. `CODE_CACHE_ENABLED` controls deterministic SQLite caching. Apex performs static AI-assisted analysis in Phase 5. Generated code is not execution-verified: it is never compiled, run, evaluated, or otherwise executed by the service.

## Phase 6: Agent Orchestration

The bounded agent creates deterministic, reviewable plans and executes only registered Apex tools through the existing `ToolExecutor`. The orchestration stack is:

`user request` -> `agent API` -> `request validation` -> `planner` -> `plan validator` -> `workflow executor` -> `ToolExecutor` -> existing tools -> intermediate results -> final response.

Use `POST /api/agent/plan` to preview a validated plan and `POST /api/agent/run` to execute it. The chat router now distinguishes `simple_chat`, `single_tool`, and `workflow` requests so normal chat stays lightweight while multi-step requests can be promoted into the agent engine.

Result references are limited to `$step_id.result.field` and `$step_id.artifact.download_url`; generated files are returned only as secure `/api/files/<filename>` URLs. The planner only selects registered Apex tools, and the validator rejects unsupported tools, missing dependencies, duplicate step IDs, cycles, malformed arguments, and plans over `AGENT_MAX_STEPS`.

Workflow execution is sequential in this phase, bounded by `AGENT_MAX_STEPS=10`, `AGENT_MAX_RETRIES=1`, and `AGENT_TIMEOUT_SECONDS=300`. Retries are only attempted for safe, recoverable tool failures. The engine does not execute shell commands, arbitrary Python, subprocesses, or unrestricted filesystem operations.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/agent/plan -Method Post -ContentType 'application/json' -Body '{"message":"Create a PDF explaining binary search"}'
Invoke-RestMethod http://127.0.0.1:8000/api/agent/run -Method Post -ContentType 'application/json' -Body '{"message":"Create 20 MCQs from this document and put them in Excel","document_ids":["operating-systems"]}'
```

Example workflow:

`Create exam notes from this PDF and make a PowerPoint` -> generate notes -> export PPT -> return artifacts.

`Create 20 MCQs from this document and put them in Excel` -> generate quiz -> export XLSX -> return artifact.

Limits are `AGENT_MAX_STEPS=10`, `AGENT_MAX_RETRIES=1`, and `AGENT_TIMEOUT_SECONDS=300`. Workflows run sequentially in this phase. The agent cannot execute shell commands, arbitrary code, or arbitrary filesystem operations.

## Phase 7: AI Runtime & Model Management

Apex Phase 7 establishes the **centralized AI Runtime** — the single intelligence layer that all application services use for LLM generation.

### Architecture

```
Application Layer (Chat, Agent, Intelligence, Code)
        ↓
    LLMService
        ↓
    AIRuntime
        ↓
    ModelManager
        ↓
  OllamaProvider
        ↓
   Qwen 2.5 3B
```

### Provider Abstraction

The runtime defines an `AIProvider` protocol that all concrete providers must implement:

| Method | Description |
|---|---|
| `health()` | Check if the provider is reachable |
| `list_models()` | Discover available models |
| `model_available(model)` | Check specific model availability |
| `generate(request, request_id)` | Chat completion |
| `generate_structured(request, request_id, schema)` | JSON-constrained generation |
| `stream(request, request_id)` | Streaming token generation |

Currently implemented: **OllamaProvider**. Cloud providers are architecturally supported but not yet implemented.

### Model Configuration

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `qwen2.5:3b` | Primary generation model |
| `OLLAMA_EMBED_MODEL` | *(empty)* | Embedding model (separate from generation) |
| `OLLAMA_FALLBACK_MODEL` | *(empty)* | Fallback model (disabled by default) |

**Important**: Generation and embedding models are configured separately. The runtime never uses the generation model for embeddings or vice versa.

### Generation Settings

All settings are CPU-friendly defaults for an 8 GB RAM machine.

| Variable | Default | Range | Description |
|---|---|---|---|
| `LLM_TEMPERATURE` | `0.2` | 0.0–2.0 | Sampling temperature |
| `LLM_TOP_P` | `0.9` | 0.0–1.0 | Nucleus sampling threshold |
| `LLM_TOP_K` | `40` | ≥ 1 | Top-k sampling |
| `LLM_NUM_CTX` | `4096` | 512–32768 | Context window size |
| `LLM_MAX_TOKENS` | `1024` | 1–4096 | Maximum generated tokens |
| `LLM_TIMEOUT_SECONDS` | `120` | 5–600 | Request timeout |
| `LLM_MAX_RETRIES` | `1` | 0–5 | Retry count for transient failures |

### Model Management

The `ModelManager` handles:
- Querying available Ollama models
- Verifying configured model availability
- Exposing model metadata (name, size, availability)
- Validating model selection
- Fallback model architecture (configurable, disabled by default)

### Structured Generation

The runtime supports Pydantic-schema-validated structured output:

1. Request is sent with `format='json'` and schema instruction
2. Model generates JSON
3. Response undergoes bounded JSON repair if needed (one attempt: trailing commas, JS comments)
4. Output is validated against the Pydantic schema
5. Invalid output produces a structured error — never silently accepted

### Streaming

Server-side streaming is supported through the provider's `stream()` method, which yields text chunks as a Python generator. WebSockets are not implemented yet.

### Retry & Timeout Policy

**Retries** (bounded by `LLM_MAX_RETRIES`):
- ✅ Retried: connection failure, temporary provider failure, timeout
- ❌ Not retried: invalid model, invalid request, schema validation errors, security errors

**Timeout**: Configurable via `LLM_TIMEOUT_SECONDS`. One model request cannot hang Apex indefinitely.

**Fallback**: If `OLLAMA_FALLBACK_MODEL` is set, the runtime attempts the fallback after primary failure. Never switches silently for structured operations. Always reports which model generated the response.

### Runtime Diagnostics

```powershell
# Health check
Invoke-RestMethod http://127.0.0.1:8000/api/runtime/health

# List available models
Invoke-RestMethod http://127.0.0.1:8000/api/runtime/models

# Diagnostic test
Invoke-RestMethod http://127.0.0.1:8000/api/runtime/test -Method Post -ContentType 'application/json' -Body '{"message":"Explain binary search in one sentence."}'
```

### In-Memory Metrics

The runtime tracks lightweight counters (no Prometheus, no persistence):
- Request count, success count, failure count
- Average latency, last request latency
- Model used

Metrics are exposed via `GET /api/runtime/health` under the `metrics` key.

### CPU Optimization Recommendations

- Context window: 4096 tokens (configurable, avoid >8192 on 8 GB RAM)
- Max generated tokens: 1024 (configurable)
- Single model loaded at a time
- No PyTorch, no Transformers, no GPU dependencies
- No unnecessary model duplication

### Security

The runtime does NOT:
- Execute generated code
- Access arbitrary filesystem paths
- Execute shell commands
- Allow user-controlled provider URLs
- Expose Ollama internals unnecessarily

### Current Configuration

```
OLLAMA_MODEL=qwen2.5:3b
```

The existing `/health` endpoint continues working unchanged. The chat API (`POST /api/chat`) now routes through the centralized runtime internally.
