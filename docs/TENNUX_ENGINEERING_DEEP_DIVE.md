# TennuX Engineering Deep Dive

> Repository reverse-engineering record. This document describes the code that exists in this repository as inspected on 2026-08-15. The implementation and README use the product name **Apex** in several places; the requested documentation name is **TennuX**. No application behavior was changed to produce this document.

## 1. Executive summary

TennuX is a local-first AI productivity workspace built around a FastAPI backend, a Next.js App Router frontend, and a local Ollama model configured as `qwen2.5:3b`. A deterministic router separates ordinary chat, document-grounded chat, single registered-tool requests, and bounded multi-step workflows. The backend centralizes model access in an AI runtime, validates structured results with Pydantic, extracts and retrieves PDF text, generates study/code outputs, produces PDF/XLSX/PPTX/DOCX artifacts, and streams safe workflow milestones to the frontend with Server-Sent Events. It is a working local application, not a production multi-user platform: authentication, persistent distributed execution, vector retrieval, and measured AI-quality evaluation are not implemented.

### 30-second explanation

“TennuX is a local AI workspace. A Next.js UI sends requests to FastAPI, which deterministically routes them to chat, keyword-based PDF RAG, a registered tool, or a bounded agent workflow. All model calls go through one runtime backed by Ollama and Qwen 2.5 3B. The system validates tool inputs and model JSON with Pydantic, creates downloadable files, and exposes safe progress events over SSE. It is intentionally local and CPU-friendly, but it is not yet production-ready or multi-user.”

### 2-minute explanation

The frontend uploads PDFs, keeps document IDs, sends chat requests, or starts `/api/agent/run?stream=true` for creation workflows. FastAPI validates request bodies. `backend/core/router.py` uses keyword signals and priority rules. Simple chat calls `LLMService`; RAG reads uploaded PDFs, chunks them, ranks chunks using token overlap, and places the selected excerpts in a prompt; single-tool requests go through `ToolExecutor`; workflows use a deterministic planner, validator, sequential executor, and recovery policy. The central `AIRuntime` talks to the local Ollama provider, checks model availability, applies generation settings, records in-memory metrics, supports bounded retries, and validates structured outputs. Generators write only under `data/outputs`; artifacts are represented as safe filenames and `/api/files/...` URLs. Agent progress is stored in an in-memory `ActivityStore`, emitted as safe labels such as “Creating PDF”, and read by a browser `EventSource`.

### 5-minute explanation

The architecture has three important boundaries. First, the application boundary: APIs do not create ad hoc Ollama clients; chat, intelligence, code, and agent operations use the `LLMService`/`AIRuntime` facade. Second, the execution boundary: tools are registered with a name, description, Pydantic schema, callable, and enabled flag. Agents can only invoke names in that registry; they do not execute arbitrary Python, shell commands, subprocesses, or generated code. Third, the artifact/activity boundary: generated files are sanitized into a fixed output directory and returned through a filename-checked download route, while the activity stream exposes only user-facing milestones, never prompts, arguments, model reasoning, or filesystem paths.

The agent is bounded rather than open-ended. `create_plan()` builds a deterministic plan from request keywords. `validate_plan()` checks step count, IDs, tool existence, dependencies, schemas, and cycles. `execute_plan()` runs ready steps sequentially, resolves `$step.result...` references, collects artifacts, retries eligible failures within a configured limit, and skips dependent steps after failure. This is an orchestration engine with agent-like planning, not a free-form autonomous loop. The principal limitations are CPU inference cost, a small model, keyword routing, simple keyword RAG, local/in-memory persistence, no auth, and the lack of objective model-quality benchmarks.

## 2. Repository inventory

| Area | Important paths | Actual responsibility |
|---|---|---|
| Backend entrypoint | `backend/main.py` | Creates FastAPI app, CORS, routers, request logging, root and health endpoints |
| Configuration | `backend/config.py`, `.env.example` | Environment settings and LLM parameter validation |
| Runtime | `backend/runtime/*.py`, `backend/core/llm.py` | Provider abstraction, Ollama, model manager, generation, JSON validation, metrics, streaming |
| APIs | `backend/api/*.py` | Chat, agent, files, documents, intelligence, code, runtime endpoints |
| Router/RAG | `backend/core/router.py`, `backend/core/rag.py` | Intent selection and PDF retrieval-augmented chat |
| Tools | `backend/core/tools.py`, `backend/core/executor.py` | Registry, schema validation, callable invocation |
| Agent | `backend/agent/*.py` | Plan construction, validation, sequential execution, recovery, state, activity |
| Document intelligence | `backend/intelligence/*.py` | Structured summaries, topics, notes, guides, flashcards, quizzes, questions |
| Code intelligence | `backend/code/*.py` | Static AI-assisted code generation and analysis |
| Generators | `backend/generators/*.py`, `backend/exporters/study_export.py` | PDF, Excel, PowerPoint, Word, study-result exports |
| Frontend | `frontend/app`, `frontend/components`, `frontend/hooks`, `frontend/lib` | Next.js UI, chat state, agent state, SSE, artifacts |
| Tests | `tests/*.py`, `frontend/components/activity/ThinkingIndicator.test.tsx` | Backend unit/API tests and three frontend activity tests |
| Storage | `data/uploads`, `data/outputs`, `data/intelligence_cache.sqlite`, `data/apex_memory.json` | Local documents, artifacts, cache, single-user memory |

## 3. Component inventory

| Component | Location | Responsibility | Depends on | Used by | Tested? |
|---|---|---|---|---|---|
| FastAPI application | `backend/main.py` | App composition, CORS, logging, health | APIs, settings, LLM service | Uvicorn/tests | Yes, API smoke tests |
| Configuration | `backend/config.py` | Environment loading and bounds | `python-dotenv` | All backend layers | Yes indirectly |
| Logging | `backend/utils/logger.py`, `backend/main.py` | Basic configured/request logging | Python logging | App/runtime/agent | Not directly |
| Ollama provider | `backend/runtime/ollama_provider.py` | Health, model list, chat, JSON, token streaming | `ollama` | `AIRuntime` | Mocked; real tests skipped if unavailable |
| AI runtime | `backend/runtime/generation.py` | Central generation, retry, fallback, metrics | Model manager, validation | Chat/intelligence/code | Yes |
| Model manager | `backend/runtime/manager.py` | Model discovery/availability/selection | Ollama provider | Runtime APIs | Yes through runtime tests |
| Tool registry | `backend/core/tools.py` | Allowlisted tool metadata and dispatch | Pydantic, generators | Executor/planner | Yes |
| Tool executor | `backend/core/executor.py` | Thin registry execution facade | Tool registry | Chat/agent | Yes via agent/tool tests |
| Agent planner | `backend/agent/planner.py` | Deterministic bounded plan creation | Registry, agent models | Agent service | Yes |
| Plan validator | `backend/agent/validator.py` | Tool/schema/dependency/cycle/limit checks | Registry, Pydantic | Agent service/executor | Yes |
| Agent executor | `backend/agent/executor.py` | Sequential dependency-aware execution | Tool executor, context/state | Agent service | Yes |
| Agent recovery | `backend/agent/recovery.py` | One bounded retry policy | Settings | Agent executor | Yes indirectly |
| Agent state/context | `backend/agent/state.py`, `context.py` | Results, artifacts, errors, current step | Pydantic | Executor | Partially tested |
| Activity broker | `backend/agent/activity.py` | In-memory ordered per-request events | Locks/conditions | Agent API/SSE | Yes |
| SSE endpoint | `backend/api/agent.py` | `activity` and `complete` events | Activity store | Frontend SSE client | Yes |
| Router | `backend/core/router.py` | Keyword intent classification | Pydantic | Chat API | Yes |
| Chat API | `backend/api/chat.py` | Routes chat/RAG/tools/workflows | Router, runtime, RAG, agent | Frontend | Yes |
| RAG | `backend/core/rag.py` | PDF extraction, chunking, overlap retrieval | pypdf, runtime | Chat API | Not directly covered by a focused test |
| Document ingestion | `backend/api/documents.py` | PDF upload, UUID filename, 25 MB limit | FastAPI upload | Frontend/RAG | Not directly tested |
| Document intelligence | `backend/intelligence/*.py` | Structured study outputs | Runtime, SQLite cache | API/agent | Models/cache/export tested; real model generation not verified |
| Code intelligence | `backend/code/*.py` | Static code generation/analysis | Runtime/cache/Pydantic | API/registry | Input/models/registration/API mocked |
| PDF generator | `backend/generators/pdf.py` | ReportLab PDF | `reportlab` | Tools/exporter | Yes via export |
| Excel generator | `backend/generators/excel.py` | openpyxl workbook | `openpyxl` | Tools/exporter | Yes via export |
| PowerPoint generator | `backend/generators/ppt.py` | python-pptx deck | `python-pptx` | Tools/exporter | Registry/API path indirectly |
| DOCX generator | `backend/generators/document.py` | python-docx document | `python-docx` | Tools/exporter | Yes via export |
| Artifact API | `backend/api/files.py`, `backend/utils/agent_utils.py` | Safe file URL and download | Local output directory | Frontend | Agent URL tested |
| Cache | `backend/intelligence/base.py` | SQLite deterministic result cache | SQLite, JSON | Intelligence/code | Yes |
| Frontend API client | `frontend/lib/api.ts`, `frontend/lib/agent.ts` | HTTP, upload, artifact URL mapping | `fetch` | Hooks/components | Not unit tested directly |
| Frontend agent hook | `frontend/hooks/useAgent.ts` | Request/activity/result state | Agent API/SSE hook | Chat window | Not directly |
| SSE hook/client | `frontend/hooks/useActivityStream.ts`, `frontend/lib/sse.ts` | EventSource subscription and retry | Browser EventSource | Chat window | Partially, backend SSE tested |
| Activity panel | `frontend/components/activity/ActivityPanel.tsx` | Accessible workflow timeline | Activity item/icon | Message list | 2 pass, 1 currently fails |
| Artifact cards | `frontend/components/artifacts/ArtifactCard.tsx` | Download links | Artifact type | Chat UI | Download rendering tested |
| Chat UI | `frontend/components/chat/*`, `ChatWindow.tsx` | Upload, route choice, messages | Hooks/components | App pages | Build verified, not end-to-end tested |

## 4. Architecture

```text
User
  |
  v
Next.js App Router frontend
  |  fetch /api/chat, /api/documents/upload, /api/agent/run
  v
FastAPI (backend/main.py)
  |
  v
Chat router (backend/core/router.py)
  |---- simple_chat ----> LLMService -> AIRuntime -> ModelManager -> Ollama -> Qwen 2.5 3B
  |---- rag_chat --------> PDF extraction -> chunks -> keyword overlap -> LLMService
  |---- single_tool ----> ToolExecutor -> ToolRegistry -> generator/code tool
  `---- workflow --------> Planner -> Validator -> AgentExecutor
                                      |        |
                                      |        `-> ToolRegistry -> ToolExecutor -> Tools
                                      `-> ActivityStore -> SSE -> EventSource -> ActivityPanel

Tools / intelligence / code
  |
  v
PDF, XLSX, PPTX, DOCX artifacts under data/outputs
  |
  v
/api/files/{filename} -> frontend artifact download
```

RAG is separate from agent execution:

```text
PDF upload -> UUID document_id -> data/uploads/{id}.pdf
                                  |
Chat with document_ids + document language
                                  v
                          backend/core/rag.py
                                  |
          pypdf text -> 2,000-char chunks / 200-char overlap
                                  |
       vague query: first 3 chunks; specific query: overlap score
                                  v
                 compact context (max 7,000 chars) -> Qwen
```

## 5. Request lifecycles

### A. Simple chat

For “Explain binary search.”:

1. `frontend/components/chat/ChatWindow.tsx` chooses ordinary chat because the message is not a creation workflow.
2. `frontend/hooks/useChat.ts` calls `runChat()` in `frontend/lib/agent.ts`.
3. `POST /api/chat` is validated by `ChatRequest` in `backend/api/chat.py`.
4. `decide()` in `backend/core/router.py` returns `simple_chat` because no workflow/tool/code signal wins.
5. `chat()` builds a system prompt, appends up to eight history messages, and calls `LLMService.chat()` in `backend/core/llm.py`.
6. `LLMService` delegates to the shared `AIRuntime`; `OllamaProvider.generate()` calls the configured Ollama model.
7. The response is returned as `{response, model, success}` and rendered as Markdown by the frontend.

If Ollama/model generation fails, the API returns HTTP 503 with a safe message. Exact model output is not guaranteed or evaluated by the repository.

### B. PDF chat

For “Summarize this document.”:

1. `uploadPdf()` posts a multipart PDF to `/api/documents/upload`. Only `application/pdf`, a `.pdf` filename, and 25 MB or less are accepted. The server creates a random 32-character hex ID and writes `data/uploads/{id}.pdf`.
2. The frontend keeps the ID, not the original path, and sends it in `ChatRequest.document_ids`.
3. `decide()` returns `rag_chat` only when document IDs exist and document-oriented language is present. An attached document alone does not force RAG.
4. `rag_chat()` validates every ID against 32 alphanumeric characters, resolves the PDF under `data/uploads`, and extracts text with `pypdf.PdfReader`.
5. Text is split into 2,000-character chunks with a 200-character overlap. At most three chunks are retrieved.
6. Vague/overview questions use the first three chunks. Specific questions remove generic overview words, score each chunk as the fraction of query tokens occurring in the chunk, and select the top three. If the best score is below `0.05`, it falls back to the first chunks.
7. Selected context is joined with separators and truncated to 7,000 characters. It is placed in an explicit prompt instructing the model not to invent unsupported information.
8. `LLMService.chat()` sends the prompt through the central runtime and the answer returns through `/api/chat`.

This is keyword retrieval. **FAISS is not used. Embeddings are not used. A vector database is not used.** The configured `OLLAMA_EMBED_MODEL` exists as configuration plumbing, but `backend/core/rag.py` never calls an embedding model.

### C. Single tool

For “Create a PDF about binary search.”:

1. The frontend sends `/api/chat`.
2. The router detects a creation verb and `pdf`, returning `single_tool` with `create_pdf` and deterministic arguments.
3. `backend/api/chat.py` calls `ToolExecutor().execute()`.
4. `backend/core/tools.py` looks up the registered `Tool`, rejects a missing/disabled tool, validates arguments with its Pydantic input model, then invokes `backend/generators/pdf.py:create_pdf()`.
5. `output_path()` strips directory components, replaces unsafe characters, enforces the `.pdf` suffix, resolves the path, and requires the parent to equal `data/outputs`.
6. The API returns “Completed create_pdf”; a generated artifact can be downloaded through `/api/files/{filename}`.

The direct single-tool PDF path does not ask Qwen to write the content. The planner has a small deterministic starter-content helper for some topics. The generated file itself is tested as an artifact, not for semantic quality.

### D. Agent workflow

For “Read this PDF, create notes, generate MCQs and export them to Excel.”:

1. The UI treats creation requests as agent candidates using `CREATION_VERBS` and `CREATION_TARGETS` in `ChatWindow.tsx`.
2. It starts `POST /api/agent/run?stream=true`, gets a UUID request ID, then subscribes to `/api/agent/events/{request_id}`.
3. A daemon thread runs `run_with_activity()`.
4. `create_plan()` recognizes notes plus quiz and creates `generate_notes` followed by dependent `generate_quiz`; an export keyword creates `export_study_result` depending on the suitable generated result.
5. `validate_plan()` checks the plan and its tool arguments. References are replaced with schema-shaped sample values during validation; actual values are resolved during execution.
6. `execute_plan()` picks a pending step whose dependencies are completed, resolves `$step_id.result.field`, calls `ToolExecutor`, records results, and captures file artifacts.
7. Each step emits safe events. No prompt, argument payload, model thought, or server path is emitted.
8. Completion stores the result. The SSE route emits `event: complete`, and `useAgent`/`useActivityStream` update chat, activity, and artifact state.

## 6. Routing

`backend/core/router.py:decide()` lowercases the message and follows this effective order:

1. Document-grounded RAG if `document_ids` are present and `_has_document_intent()` sees strong signals such as “this PDF”, “according to”, “summarize”, “chapter”, or “page”. Weak words such as “explain” require a document anchor.
2. Workflow if multiple creation/document signals match, or `_is_workflow()` sees connectors such as `and`/`export` with output formats or study operations.
3. The code dispatch checks language words plus `debug`, `refactor`, `review`, `explain`, `complexity`, `test`, or `documentation`; generation verbs map to `generate_code`.
4. Single file creation maps `pdf`, `excel`, `ppt`, or document phrases to registered generators.
5. Otherwise the intent is `simple_chat`.

The source contains a duplicated RAG check after workflow logic; the first RAG check normally handles the case. Because RAG is checked first, a message with document IDs and strong document language can win over a workflow-looking message. The frontend has its own coarse creation check, so frontend/backend classification can differ; the backend remains authoritative.

## 7. AI runtime and model integration

`backend/runtime/provider.py` defines the `AIProvider` protocol: health, model listing, availability, normal generation, structured generation, and streaming. The only concrete provider is `OllamaProvider` in `backend/runtime/ollama_provider.py`, using `ollama.Client(host=..., timeout=...)`.

`ModelManager` discovers models, checks the configured model, reports optional size metadata, and validates explicit selection. `AIRuntime` is the single generation boundary used by `LLMService`, intelligence, code, and runtime diagnostics. This prevents each feature from creating different clients, defaults, retry behavior, or validation rules.

Configured values come from `backend/config.py`. Important actual defaults in code are `qwen2.5:3b`, temperature `0.2`, top-p `0.9`, top-k `40`, context `3072`, max output `768`, timeout `120` seconds, and zero runtime retries. `.env.example` documents different values for context, max tokens, and retries (`4096`, `1024`, `1`); environment values win. This discrepancy is a configuration/documentation gap, not a measured behavior difference.

Normal generation checks availability, applies defaults, retries non-`ValueError` failures up to `LLM_MAX_RETRIES`, validates non-empty response and a 200,000-character maximum, records in-memory metrics, and can try a configured fallback model. Structured generation does not silently switch models: Ollama is asked for JSON, the response is extracted, one bounded repair removes trailing commas/comments, and Pydantic validation must succeed. Invalid structured output raises an error. `OllamaProvider.stream()` yields text chunks, and `AIRuntime.stream()` exposes them, but application chat does not currently use token streaming; the separate workflow SSE streams activity/result events.

Metrics are process-local counters: request count, successes, failures, average latency, last latency, and last model. They are not persisted, Prometheus metrics, or a benchmark. Usage fields are copied from Ollama when available; the code does not fabricate token counts.

## 8. Tool registry and executor

A tool is a `Tool(name, description, schema, execute, enabled)` in `backend/core/tools.py`. Registration inserts it into the module-level `_TOOLS` map. `get_tool()` and `list_tools()` provide discovery. `execute_tool()` performs lookup, enabled check, `schema.model_validate(arguments)`, callable invocation, and normalized success/error output.

### Registered tools

| Tool | Purpose | Inputs | Output | Called by |
|---|---|---|---|---|
| `create_pdf` | Create PDF | `filename`, `title`, `content` | `{success,file,type}` | Chat, agent |
| `create_excel` | Create workbook | `filename`, `sheet_name`, `columns`, `rows` | file result | Chat, agent |
| `create_ppt` | Create presentation | `filename`, `presentation_title`, `slides` | file result | Chat, agent |
| `create_document` | Create DOCX | `filename`, `title`, `paragraphs` | file result | Chat, agent |
| `summarize_document` | Structured document summary | `document_id` | `Summary` dict | Agent |
| `generate_notes` | Structured notes | `document_id`, `style` | `Notes` dict | Agent |
| `generate_quiz` | MCQs | `document_id`, `count`, `difficulty` | `Quiz` dict | Agent |
| `generate_flashcards` | Flashcards | `document_id`, `count` | `Flashcards` dict | Agent |
| `export_study_result` | Convert study result to file | `result`, `format`, `filename` | file result | Agent |
| `generate_code` | Static code generation | language/task/constraints/existing code | `CodeGeneration` dict | Chat, code API |
| `explain_code` | Static explanation | code/language | `ExplainCode` dict | Chat, code API |
| `debug_code` | Static debugging | code/language/error/expected behavior | `DebugResult` dict | Chat, code API |
| `refactor_code` | Static refactoring | code/language/goal | `RefactorResult` dict | Chat, code API |
| `review_code` | Static review | code/language | `ReviewResult` dict | Chat, code API |
| `generate_tests` | Generate unexecuted tests | code/language/framework | `TestGeneration` dict | Chat, code API |
| `generate_documentation` | Generate docs | code/language/style | `Documentation` dict | Chat, code API |
| `analyze_complexity` | Static complexity analysis | code/language | `ComplexityAnalysis` dict | Chat, code API |

Import side effects in `backend/agent/__init__.py` and `backend/code/__init__.py` register agent and code tools. There is no arbitrary function lookup from user text, shell executor, `eval`, `exec`, subprocess runner, or generated-code runner. Registry allowlisting is a meaningful control, but there is no authentication or per-user authorization around it.

`ToolExecutor` is intentionally separate from the agent: direct chat and other services can invoke the same validation/dispatch path, while the agent owns planning, dependencies, references, retries, and state.

## 9. Agent orchestration

`AgentRequest` limits messages to 12,000 characters and document IDs to 10. `AgentStep` contains an ID, tool, arguments, dependencies, and one of `pending`, `running`, `completed`, `failed`, or `skipped`. `AgentPlan` contains the goal and steps. `AgentResult` contains success, request ID, status, steps, artifacts, and errors.

The planner is deterministic keyword planning, not an LLM planner. It selects document tools for notes/quizzes/flashcards, creates export steps, or builds bounded direct artifact plans. It uses only currently registered tool names. The validator enforces `AGENT_MAX_STEPS` (default 10), non-empty plans, unique IDs, registered tools, known dependencies, Pydantic-valid arguments after reference placeholders, and acyclic dependencies.

The executor repeatedly selects the first runnable step whose dependencies are completed. It resolves references of the form `$step_id.result.field` or `$step_id.artifact...`; unsupported references fail the step. It calls `ToolExecutor`, stores result payloads in `AgentContext` and `WorkflowState`, captures files through `artifact_from_output()`, and emits activity milestones. Execution is sequential in this implementation, even where the dependency graph could allow parallelism.

Recovery is bounded by `AGENT_MAX_RETRIES` (default 1). Errors containing “invalid tool input”, “not found”, “unsupported”, or “dangerous” are not retried. Other failures may retry until the limit. Failed steps cause directly dependent pending steps to become skipped; the final status is `completed`, `partial_failure`, or `failed`. There is no open-ended loop because plans are finite and validated before execution.

### Example plan

For “Read my Compiler Design PDF, create exam notes, generate 20 MCQs, export the MCQs to Excel and create a PowerPoint”, assuming the document ID is supplied, the actual planner can produce approximately:

```text
step_1  generate_notes(document_id, style=exam)
step_2  generate_quiz(document_id, count=20, difficulty=mixed) depends_on step_1
step_3  export_study_result($step_2.result, xlsx, agent-study-result.xlsx) depends_on step_2
step_4  export_study_result($step_1.result, pptx, agent-study-result.pptx) depends_on step_1
```

The exact plan depends on keywords and the planner’s export-source selection. If step 3 fails, its status is `failed` and only its dependents are skipped; the notes and PPT may still complete. The overall result is `partial_failure`. If the Excel generator fails after notes and quiz succeed, the Excel artifact is absent and the workflow reports an error rather than pretending it exists.

## 10. RAG and document intelligence

### RAG

RAG reads only UUID-named uploaded PDFs from `data/uploads`. It extracts page text with `pypdf`, chunks with fixed character windows, and uses keyword overlap. It does not persist an index, calculate embeddings, use FAISS, cite page numbers, or expose retrieval scores. If no meaningful overlap is found, it uses the first three chunks, which is a graceful overview fallback but can be irrelevant for specific questions. Invalid IDs, missing documents, unreadable PDFs, and empty extracted text become safe API errors.

### Document intelligence

Available API operations in `backend/api/intelligence.py` are summarize, topics, notes, semester-notes, study-guide, flashcards, quiz, and questions. Each operation reads a document through `backend/intelligence/base.py`, hashes its source text, operation, request, and count, then checks SQLite cache. Long documents are split into up to 40 chunks of the configured `INTELLIGENCE_CHUNK_CHARS` (default 5,000); each chunk first goes through structured fact extraction, then the combined facts are sent to the operation-specific Pydantic schema. The runtime prompts the model for JSON, parses it, and Pydantic validates it.

Models enforce useful invariants: quiz answers must be among four options; quiz questions and flashcard questions must be unique case-insensitively; fields and counts have API bounds. Cache storage is `data/intelligence_cache.sqlite`; it is deterministic for identical source/configuration inputs. It is local, single-process friendly, not distributed, not encrypted, and not a performance benchmark.

## 11. Code intelligence

Code endpoints are generate, explain, debug, refactor, review, tests, document, and complexity. Supported languages are Python, C, C++, Java, JavaScript, TypeScript, SQL, HTML, CSS, and Bash. `validate_code()` enforces non-empty input and `CODE_MAX_INPUT_CHARS` (default 30,000); language detection is heuristic. Outputs are structured Pydantic models and can be cached under a code-specific hash when `CODE_CACHE_ENABLED` is true.

The crucial safety fact is that generated code is not compiled, run, tested, evaluated, or otherwise executed by this service. Generated tests are explicitly marked unexecuted. This protects the local process from generated code, but it also means correctness claims are not execution-verified.

## 12. File generation and artifacts

| Format | Library | Flow | Download |
|---|---|---|---|
| PDF | ReportLab | Wrap text, headings, pages, save under output directory | `/api/files/name.pdf` |
| XLSX | openpyxl | Create workbook, header, rows, save | `/api/files/name.xlsx` |
| PPTX | python-pptx | Title slide plus bullet slides, save | `/api/files/name.pptx` |
| DOCX | python-docx | Heading plus paragraphs, save | `/api/files/name.docx` |

`output_path()` uses `Path(filename).name`, replaces characters outside a conservative allowlist, strips unsafe trailing characters, enforces a suffix, resolves the result, and verifies the parent directory. `backend/api/files.py` repeats basename/parent/existence checks before `FileResponse`. Agent artifact metadata includes only the basename, relative project path, type, and `/api/files/...` URL. The frontend turns relative URLs into backend-absolute URLs because the Next.js origin differs.

## 13. Caching, memory, and persistence

Intelligence cache keys include operation/request/count and SHA-256 of source text. Code cache keys include operation/language/code/request/error and a namespace. Values are JSON payloads validated back into their Pydantic model on cache hit. Cache behavior is deterministic for equal inputs but no expiry, size policy, invalidation UI, encryption, or distributed backend exists.

`backend/core/memory.py` is a small local JSON store, not an agent memory system. It stores recent themes, a detected “my name is” fact, and up to 200 feedback records in `data/apex_memory.json`. Simple chat includes this context. There is no user identity, tenant isolation, durable database abstraction, or privacy control in the code.

## 14. SSE activity and thinking UI

`POST /api/agent/run?stream=true` creates a request ID, creates an `ActivityStore` record, starts a daemon thread, and immediately returns `{request_id,status:started}`. The worker emits safe `ActivityEvent` objects, finishes with the serialized result, and the GET endpoint streams:

```text
event: activity   data: {safe event JSON}
event: activity   data: {safe event JSON}
event: complete   data: {agent result JSON}
```

Event types are `thinking`, `planning`, `tool_selection`, `tool_execution`, `retrieval`, `generation`, `artifact`, `completion`, and `error`; statuses are pending/running/completed/failed. In practice agent service/executor emits thinking, planning, tool selection/execution, artifact, completion/error. Events preserve append order per request. `ActivityStore` holds at most 200 request records and waits up to 15 seconds between checks. There is no persistent event log. Once evicted or unknown, a request returns 404. Reconnection is implemented in `frontend/lib/sse.ts`: close on error, retry up to three times with exponential-ish delays (350 ms, 700 ms, 1,400 ms), then show an error. The client does not send a last-event ID or replay cursor, so missed events during reconnect are not guaranteed to be recovered.

SSE is a reasonable design rationale for one-way server-to-browser progress while the POST starts work; the code does not document a formal WebSocket comparison. WebSockets are not used for this activity path. Runtime token streaming exists separately but is not wired into `/api/chat`.

“Thinking” in the UI means safe workflow status, not private chain-of-thought. TennuX displays “Understanding request”, “Planning task”, “Creating PDF”, “Generating study notes”, and completion/error milestones. It never sends hidden prompts, raw model reasoning, tool arguments, or internal analysis to the client.

## 15. Frontend architecture

The frontend is Next.js 15/React 19 with App Router pages at `/`, `/chat`, and `/workspace`. `ChatWindow` owns the high-level choice between agent creation and ordinary chat. `useChat` maintains ordinary messages and uses synthetic document activity steps while the request runs. `useAgent` stores request ID, up to 30 activity items, result, error, and mapped artifacts. `useActivityStream` connects that state to `EventSource`. `MessageList`, `AssistantMessage`, `ActivityPanel`, `ActivityItem`, and `ArtifactCard` render the result. `useBackendStatus` polls `/api/runtime/health` for backend/provider status.

This state split means a document question through `/api/chat` uses simulated frontend activity labels, while an agent workflow uses actual backend SSE events. The UI’s completed activity collapse behavior is currently inconsistent with its test: `ActivityPanel` initializes `open` to `true` and does not use its `completed` prop to initialize closed state.

## 16. Security posture

| Threat | Current protection | Status/gap |
|---|---|---|
| Output path traversal | Basename stripping, sanitization, resolved-parent check | Implemented for generator and download paths |
| Uploaded filename traversal | Server stores random UUID basename; returns `Path(filename).name` | Implemented |
| Invalid document IDs | Regex and fixed directory checks | Implemented; PDF upload has no content inspection beyond MIME/name/size |
| Malicious tool name | Registry lookup and enabled flag | Implemented allowlist; no auth boundary |
| Invalid tool arguments | Pydantic schema validation | Implemented |
| Infinite workflow loop | Finite plan plus max steps | Implemented for current planner/executor |
| Endless retry | Runtime and agent retry limits | Implemented |
| Generated code execution | No compiler/interpreter/subprocess/eval/exec path | Implemented non-execution property |
| Structured-output abuse | Size limit, JSON parsing/repair, Pydantic validation | Implemented; prompt injection is not fully solved |
| Prompt injection in source documents | Intelligence system prompt labels source as untrusted and says not to follow instructions | Mitigation only; no formal isolation guarantee |
| Secrets | Environment configuration; no secrets committed in `.env.example` | Basic; no secret manager |
| CORS | Configured frontend origin, GET/POST only, no wildcard | Implemented; `FRONTEND_ORIGIN` is environment-controlled |
| Authentication/authorization | None | Not implemented |
| Rate limiting | None | Not implemented |
| Multi-user isolation | None; shared local files/cache/memory | Not implemented |
| Safe Markdown | React Markdown/GFM rendering | Rendering exists; no dedicated sanitization/security test was found |
| SSE access control | Request IDs only | Not authenticated; anyone with an ID could request the stream |

The project has useful local safety controls, but it must not be described as production-secure.

## 17. Testing and current verification

### Latest commands run

| Area | Command | Result |
|---|---|---|
| Backend | `python -m pytest -q` | **62 passed, 3 skipped**, one Starlette/httpx deprecation warning |
| Frontend tests | `npm test -- --run` | **2 passed, 1 failed** out of 3; completed activity expected `aria-expanded=false`, received `true` |
| Frontend lint | `npm run lint` | Passed |
| Frontend build | `npm run build` | Passed; Next build emitted repeated optional SWC native-module warnings but compiled, type-checked, and generated pages |

### Test inventory

| Test area | What is verified | Automated? | Current result |
|---|---|---|---|
| `tests/test_tools.py` | Tool schemas, missing/disabled/invalid tool behavior, file outputs | Yes | Included in 62 pass |
| `tests/test_runtime.py` | Runtime models, provider mocks, retry limits, metrics, API diagnostics, structured parsing | Yes | Included in 62 pass |
| `tests/test_intelligence.py` | Pydantic invariants, invalid document ID, SQLite cache, PDF/DOCX/XLSX export | Yes | Included in 62 pass |
| `tests/test_health.py` | Root, health without Ollama, empty chat rejection | Yes | Included in 62 pass |
| `tests/test_code.py` | Models, severity, input/language helpers, registration, mocked API generation | Yes | Included in 62 pass |
| `tests/test_agent.py` | Plan validation, references, artifacts, failures/skips, APIs, routing | Yes | Included in 62 pass |
| `tests/test_activity.py` | In-memory order/safe serialization, missing SSE request, streamed completion | Yes | Included in 62 pass |
| Frontend activity tests | Thinking label, artifact link, completed collapse | Yes | 2 pass, 1 fail |
| Real Qwen tests | Runtime and chat against actual Ollama/Qwen | Conditional integration | 2 skipped because model/provider unavailable in this environment |

Unit/API tests use mocks and `TestClient` heavily. The repository does not prove full real-model quality, full upload-to-RAG-to-answer behavior, multi-user behavior, performance, or deployment behavior. No static security audit or benchmark run was found. “Code exists” is not the same as “AI behavior verified.”

## 18. Failure modes

| Trigger | Detection | Handling | User-visible result |
|---|---|---|---|
| Ollama down | Provider health/generation exception | Health returns degraded; generation returns 503; bounded retry may occur | Backend unavailable/model error |
| Model missing | `model_available()` false | Raise configuration/model unavailable | 422/503 depending endpoint |
| Invalid PDF | Upload MIME/name/size or pypdf extraction failure | Reject upload or return safe RAG error | 415/413/422/503 |
| Invalid document ID | Regex/fixed path checks | ValueError/FileNotFoundError | 422 or 404 |
| Unknown tool | Registry lookup | Return failure / reject plan | 400 or 422 |
| Invalid tool args | Pydantic validation | No execution; normalized error | 400/422 |
| Cyclic plan | Validator topological readiness check | Reject before execution | 422 |
| Tool failure | Executor result `success=false` or exception normalization | Retry if eligible; mark failed; skip dependents | Partial failure/error artifact list |
| Malformed model JSON | Parse/extract/one repair/schema validation | Raise; structured result not accepted | Generation endpoint failure |
| SSE connection failure | Browser `EventSource.onerror` | Close and retry up to three times | “Activity connection was interrupted.” |
| Missing artifact | Download path/existence check | 404 | File not found |
| Backend unavailable | Fetch failure in frontend | Hook catches and displays error | Unable to complete request/status unavailable |
| Frontend cannot connect to SSE | EventSource error | Retry then error | Workflow activity may be incomplete, but worker may continue |

## 19. Limitations and production evolution

Current limitations supported by the code are CPU-only local inference assumptions, small-model reasoning limits, keyword retrieval instead of semantic retrieval, possible hallucinations, heuristic routing, local SQLite/JSON/in-memory storage, no authentication or tenant isolation, no distributed worker execution, no durable activity events, no rate limits, no production observability, and no execution-based code verification. The repository has `data/documents` support in intelligence code but the public upload route writes `data/uploads`; this is an operational inconsistency worth fixing before presenting a unified ingestion design.

### Future architecture, explicitly not implemented

| Stage | Likely evolution |
|---|---|
| Local development | Keep Ollama, local files, SQLite, single FastAPI/Next process |
| Single cloud instance | Managed PostgreSQL for metadata/cache, object storage for PDFs/artifacts, model server with GPU or hosted inference, reverse proxy, auth |
| Multi-user production | PostgreSQL, object storage, Redis/event bus, durable job queue, worker pool, persistent event log, per-user authorization, rate limits, audit logs, metrics/traces, vector index/embedding service, isolated model execution |

Horizontal scaling requires removing process-local singletons (`ActivityStore`, metrics, caches), making artifacts/object metadata durable, and ensuring a request is routed to a worker that can recover after restart. Supporting 1,000 concurrent users would require measured capacity work; the current local Ollama and in-memory thread model does not establish that capacity.

### Deployment view

Next.js can be hosted on a Node-capable or managed Next platform. FastAPI can run behind a reverse proxy on a container/VM. Ollama needs a host with sufficient CPU/RAM or GPU; a basic web server is not automatically a suitable inference host. Uploaded documents and generated files should move to object storage, metadata/cache to PostgreSQL/Redis, and long workflows to a queue. Authentication, authorization, TLS, rate limiting, and secret management must be added.

## 20. Design decisions

| Choice | Reason grounded in code/design | Trade-off | Alternative |
|---|---|---|---|
| FastAPI | Typed request models, simple API composition, async upload, `TestClient`, streaming response | Python service still needs deployment/runtime hardening | Flask, Django, another ASGI framework |
| Next.js | React App Router UI and production build tooling | More frontend complexity than a plain SPA | Vite React, server-rendered alternatives |
| Ollama | Local model endpoint and simple Python client | Requires local model process and hardware | Hosted API, vLLM, llama.cpp service |
| Qwen 2.5 3B | Configured CPU-friendly local model | Smaller reasoning/context quality ceiling | Larger local or hosted model |
| SQLite | Zero-setup local deterministic cache | No distributed concurrency/tenant model | PostgreSQL, Redis |
| Pydantic | Request, tool, structured model and agent validation | Schema failures can expose strictness to callers | JSON Schema libraries, dataclasses plus validators |
| SSE | One-way progress events from worker to browser | No bidirectional channel or replay durability | WebSocket, polling, durable event stream |
| Tool registry | Central allowlist and shared schemas | Registry is process-local and extensibility is manual | Plugin system, external tool service |
| Agent planner | Deterministic, bounded, interviewable workflows | Limited language flexibility; not a general planner | LLM planner, LangGraph, workflow engine |
| Local-first | Privacy, no cloud dependency, affordable development | Hardware, availability, scaling, update burden | Cloud-first model APIs |
| CPU inference | Makes the project usable without GPU | Higher latency/lower throughput is expected, but not measured | GPU serving |
| Keyword RAG | Simple, dependency-light, CPU-friendly | Lower semantic recall and no citations | Embeddings plus vector/hybrid retrieval |

## 21. Model evaluation and benchmark plan

### Currently implemented evaluation

The repository has schema/unit/API tests and conditional real-Ollama smoke tests. It has **no measured accuracy, factuality, retrieval precision/recall, grounded-answer rate, summary score, code execution score, plan-selection accuracy, workflow success benchmark, latency percentile, tokens/second, or memory benchmark**.

### Recommended evaluation

Create fixed, versioned datasets with expected answers or rubrics:

| Capability | Metrics |
|---|---|
| Chat | Factuality, relevance, refusal appropriateness, hallucination rate |
| RAG | Recall@k, precision@k, grounded-answer rate, citation/page accuracy, no-answer correctness |
| Intelligence | Summary coverage, factual consistency, duplicate rate, schema validity, human usefulness |
| Code | Static rubric plus compile/run/test pass rate in an isolated sandbox; current product intentionally does not execute code |
| Agent | Plan validity, tool-selection accuracy, completion rate, partial-failure correctness, retry/recovery rate |

Practical first benchmark: 100 general chat questions, 50 document questions over annotated PDFs, 50 generation/export tasks, 50 code tasks, and 25 agent workflows. Store prompts, model/config version, expected evidence, output, and scorer decisions. Use deterministic automated checks where possible and blinded human review for quality. These are proposed test sizes, not completed results.

### Future performance table

| Metric | Current measurement | Recommended benchmark |
|---|---|---|
| Chat latency | Not measured | P50/P95 end-to-end and model time |
| RAG latency | Not measured | P50/P95 by document size and query type |
| Agent workflow time | Not measured | P50/P95 per step and complete workflow |
| Memory usage | Not measured | Peak RSS with model loaded and during exports |
| Tokens/sec | Not measured | CPU tokens/sec by prompt/output size |
| SSE delivery | Not measured | Event delay, disconnect/recovery rate |

## 22. Interview preparation

### Hard questions with honest answers

- **Why is this an agent and not just an LLM wrapper?** Short: It creates and executes bounded multi-step plans with dependencies, state, retries, and artifacts. Deep: The current planner is deterministic rather than LLM-generated, but `AgentPlan`, validator, executor, references, recovery, and activity create an orchestration layer beyond one completion. Interviewer tests whether I distinguish orchestration from branding.
- **Why not LangChain or LangGraph?** Short: The repository needed a small explicit registry and bounded executor. Deep: A custom implementation makes the actual safety and dependency rules visible and keeps dependencies small; the trade-off is less ecosystem support and more code to maintain. This is a design choice, not proof that frameworks are inferior.
- **How do you prevent arbitrary tool execution?** Short: Only registered tool names are accepted and arguments are validated by each tool schema. Deep: `get_tool()` resolves a name from `_TOOLS`; there is no user-controlled import, shell, subprocess, eval, or exec path. Authentication and authorization are still absent.
- **How do you prevent infinite loops?** Short: Plans are finite and capped by `AGENT_MAX_STEPS`. Deep: The planner returns a finite list, validator rejects cycles, executor only runs pending steps, and retries are capped by `AGENT_MAX_RETRIES`.
- **How do you handle partial failure?** Short: A failed step is recorded, retryable errors may retry, and dependents are skipped. Deep: Independent steps can still finish; `AgentResult.status` becomes `partial_failure` when some work completed but failures/skips remain.
- **Why keyword RAG?** Short: It is a lightweight CPU-friendly baseline. Deep: Chunks are ranked by fraction of query tokens occurring in each chunk, with an opening-chunk fallback. It is not semantic retrieval and should be replaced or supplemented with embeddings after evaluation.
- **How do you handle prompt injection?** Short: Intelligence prompts label source as untrusted and instruct the model not to follow source instructions. Deep: This is a prompt-level mitigation, not a hard security boundary; stronger isolation, content filtering, retrieval controls, and output evaluation are future work.
- **What happens if Ollama is unavailable?** Short: Health becomes degraded and generation APIs return safe 503 errors. Deep: Provider calls are bounded by timeout/retry settings; model availability is checked before generation.
- **What happens if JSON is malformed?** Short: The runtime extracts JSON, makes one bounded repair attempt, then validates with Pydantic. Deep: Invalid JSON/schema never becomes a silently accepted result.
- **Why SSE instead of WebSockets?** Short: The workflow needs one-way server-to-browser milestones. Deep: POST starts the job, GET streams events; the browser reconnects up to three times. There is no bidirectional requirement in the implemented activity path.
- **What is the biggest bottleneck?** Short: Local model inference is the likely bottleneck, but no latency benchmark exists. Deep: CPU model generation, document extraction, and sequential workflows are candidates; claims require measurement.
- **Can the system support 1,000 users?** Short: Not in its current form. Deep: In-memory activity, local files, SQLite cache, process-local metrics, thread workers, and one Ollama instance require replacement with durable/distributed components.
- **How is generated code made safe?** Short: It is never executed. Deep: The service only asks the model for structured source text and analysis; no compiler, interpreter, subprocess, or sandbox runner exists.
- **How would you make RAG more accurate?** Short: Evaluate retrieval first, then add semantic/hybrid retrieval and citations. Deep: Preserve page/chunk metadata, use embeddings/vector or BM25 hybrid search, rerank, add no-answer thresholds, and measure recall/grounding.
- **What would you improve in three months?** Short: Authentication/isolation, durable jobs/events, evaluated hybrid RAG, observability, and production deployment. Deep: I would prioritize controls that change the system’s operational risk before adding more model features.

## 23. Code walkthrough order

1. `README.md` — “This gives the phase history and the local run contract, but I will verify claims against code.”
2. `backend/main.py` — “This composes the FastAPI app, CORS, routers, logging, and health.”
3. `backend/config.py` and `.env.example` — “These define runtime knobs and also show where defaults/documentation differ.”
4. `backend/api/chat.py` — “This is the top-level request fan-out.”
5. `backend/core/router.py` — “Routing is deterministic keyword classification with RAG priority.”
6. `backend/core/llm.py` and `backend/runtime/generation.py` — “Every model call crosses this central boundary.”
7. `backend/runtime/ollama_provider.py` — “This is the concrete local provider.”
8. `backend/core/tools.py` and `backend/core/executor.py` — “This is the allowlisted execution boundary.”
9. `backend/agent/models.py`, `planner.py`, `validator.py`, `executor.py` — “These show the bounded workflow state machine.”
10. `backend/agent/recovery.py` and `activity.py` — “These show failure policy and safe progress events.”
11. `backend/core/rag.py` — “This is keyword-overlap PDF retrieval, not vector RAG.”
12. `backend/intelligence/base.py` and `models.py` — “This shows extraction, cache, structured generation, and invariants.”
13. `backend/code/base.py` and `backend/code/tools.py` — “Code is static and never executed.”
14. `backend/generators/*` and `backend/api/files.py` — “Artifacts are sanitized and downloaded through a checked path.”
15. `backend/api/agent.py` — “This connects background workflow execution to SSE.”
16. `frontend/lib/sse.ts`, `frontend/hooks/useAgent.ts`, `frontend/components/activity/ActivityPanel.tsx` — “The frontend receives safe milestones and renders them as a timeline.”
17. `tests/*.py` and frontend test — “These separate mock/unit/API coverage from skipped real-model tests and the current UI failure.”

## 24. Five-minute demo script

| Time | Demo | Truthful framing |
|---|---|---|
| 00:00 | Introduce TennuX | Local FastAPI/Next/Ollama workspace |
| 00:30 | Ask a simple question | Direct runtime path; output quality is model-dependent |
| 01:00 | Upload a PDF | UUID document ID, 25 MB PDF limit |
| 01:30 | Ask “summarize this PDF” | Keyword-overlap retrieval, not embeddings |
| 02:10 | Start a notes/quiz/export request | Deterministic bounded agent plan |
| 03:00 | Show activity panel | Safe events, not chain-of-thought |
| 03:40 | Download PDF/XLSX/PPTX/DOCX artifact | Fixed output directory and safe URL |
| 04:20 | Open runtime/health | Provider/model status and in-memory metrics |
| 04:40 | Explain tests/security | 62 backend pass, 3 skipped; frontend lint/build pass, 1 UI test failure |
| 05:00 | State limitations | No auth, vector RAG, distributed jobs, or measured model benchmarks |

## 25. Honest disclosure

An interview-safe statement is: “I used AI-assisted development to accelerate implementation. I still integrated the components, reviewed the repository behavior, ran and interpreted the tests, debugged failures, and can explain the request flow, validation, execution boundaries, and limitations. I do not claim that every line was manually authored or that unmeasured model quality is proven.” This is a professional description of the development process without inventing personal contributions.

## 26. Gaps to study

**CRITICAL:** FastAPI request/response validation and dependency patterns; Pydantic v2; async/threading and SSE; local model inference and Ollama; RAG retrieval quality; prompt injection; authentication/authorization; filesystem/object-storage security; testing mock versus real-model behavior.

**HIGH:** DAG/dependency execution; retries and idempotency; SQLite concurrency; caching keys/invalidation; Next.js client state; EventSource reconnect semantics; observability; CPU/GPU model serving; benchmark design.

**MEDIUM:** LangChain/LangGraph trade-offs; vector databases and hybrid search; Redis/job queues; PostgreSQL schema design; cloud deployment; sandboxing generated code; frontend accessibility testing.

## 27. Glossary

| Term | Meaning here |
|---|---|
| LLM | The language model served by Ollama |
| RAG | Retrieval-augmented generation using selected document text in the prompt |
| Embedding | Numeric semantic representation; not implemented in current RAG |
| Chunking | Splitting document text into bounded pieces |
| Retrieval | Selecting chunks for a query |
| Tool | Registered callable plus description and Pydantic schema |
| Agent | Bounded planner/executor workflow layer |
| Planner | Deterministic function that builds `AgentPlan` |
| Executor | Runs validated steps and resolves dependencies/references |
| Orchestration | Coordinating multiple steps, tools, state, and recovery |
| Structured output | Model JSON parsed and validated against a schema |
| Pydantic | Python validation/model library used throughout the backend |
| SSE | One-way HTTP event stream from server to browser |
| Artifact | Generated file plus safe metadata/download URL |
| Cache | SQLite JSON result store keyed by deterministic hashes |
| Inference | Model execution to produce an output |
| Model routing | Current keyword route selection; not model selection by task |
| Prompt injection | Instructions hidden in user/source content attempting to change model behavior |
| Hallucination | Unsupported or fabricated model output |

## 28. Final architecture summary: how TennuX works in one picture

```text
Frontend (Next.js)
      |
      v
FastAPI APIs
      |
      v
Deterministic router
      |
      +--> Simple chat ------+
      +--> RAG --------------+--> LLMService --> AIRuntime --> Ollama --> Qwen 2.5 3B
      +--> Single tool ------+
      `--> Agent planner -> validator -> sequential executor -> registry/tools
                                                        |
                                                        v
                                                  Artifacts / files
                                                        |
                                                        v
                                         SSE activity -> frontend timeline
```

## 29. Final status table

| Capability | Implemented | Automated test | Manual verification | Production ready? |
|---|---|---|---|---|
| FastAPI app/health | YES | YES | Local test client | NO |
| Simple chat | YES | API path; real model skipped | Not verified with live model here | NO |
| PDF upload | YES | PARTIAL | Not recorded here | NO |
| PDF RAG | YES, keyword-based | NOT VERIFIED end-to-end | Not recorded here | NO |
| Document intelligence | YES | Models/cache/export only | Real generation not verified | NO |
| Code intelligence | YES, static | Mocked/API validation | Not verified with live model | NO |
| PDF/XLSX/PPTX/DOCX generation | YES | PARTIAL by format | Sample outputs exist in data | NO |
| Tool registry/executor | YES | YES | Not separately audited | NO |
| Agent planning/validation | YES, bounded/deterministic | YES | Non-LLM workflow tested | NO |
| Agent recovery/partial failure | YES | YES, limited cases | Not production-tested | NO |
| SSE activity | YES | YES backend | Frontend reconnect not end-to-end tested | NO |
| Frontend chat/artifacts | YES | PARTIAL | Build only | NO |
| Frontend activity collapse | PARTIALLY IMPLEMENTED | 1 failing test | Failure reproduced | NO |
| Authentication/authorization | NO | NO | NO | NO |
| Embedding/vector RAG | NO | NO | NO | NO |
| Code execution sandbox | NO | NO | NO | NO |
| Distributed jobs/events | NO | NO | NO | NO |
| AI quality evaluation | NO | NO | NO | NO |
