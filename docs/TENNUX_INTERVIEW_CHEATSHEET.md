# TennuX Interview Cheatsheet

## 30-second pitch

TennuX is a local-first AI productivity workspace using Next.js, FastAPI, Ollama, and Qwen 2.5 3B. FastAPI deterministically routes requests to simple chat, keyword-based PDF RAG, registered tools, or bounded agent workflows. Pydantic validates requests, tool arguments, plans, and structured model results. The system generates downloadable files and streams safe workflow milestones over SSE. It is a strong local engineering prototype, but it is not yet a production multi-user system: no auth, vector retrieval, distributed jobs, or measured AI-quality benchmarks are implemented.

## Two-minute architecture

The frontend uploads PDFs and sends chat or agent requests. `backend/api/chat.py` calls `backend/core/router.py`, which uses keyword signals. Simple chat calls `LLMService` and the shared `AIRuntime`. RAG extracts PDF text with pypdf, chunks it, ranks chunks with keyword overlap, and sends selected context to Ollama. A single tool goes through `ToolExecutor` and the central registry. A workflow goes through deterministic planning, plan validation, sequential execution, dependency/reference resolution, bounded retries, artifact collection, and safe activity events. The browser consumes activity events through `EventSource` and downloads files through `/api/files/{filename}`.

```text
Next.js -> FastAPI -> router -> chat / keyword RAG / tool / bounded agent
                                      |
                                      v
                         LLMService -> AIRuntime -> Ollama -> Qwen 2.5 3B
                                      |
                                      v
                         tools -> data/outputs -> safe download URL
                                      |
                                      v
                         ActivityStore -> SSE -> ActivityPanel
```

## Top 30 questions

1. **What is TennuX?** A local AI workspace combining chat, document study, code analysis, tools, artifacts, and bounded workflows.
2. **Why local-first?** Privacy and no cloud dependency, traded for local hardware and scaling limits.
3. **Why FastAPI?** Typed Pydantic APIs, easy composition, upload support, and streaming responses.
4. **Why Next.js?** React App Router, client hooks, and a production build path.
5. **Why Ollama?** A simple local model runtime with a Python client.
6. **Why Qwen 2.5 3B?** The configured small model suits CPU/local constraints; quality is not benchmarked here.
7. **How does routing work?** `backend/core/router.py` uses ordered keyword intent rules.
8. **Does an attached PDF always activate RAG?** No. IDs plus document-oriented language are required.
9. **How does RAG retrieve?** PDF text, 2,000-character chunks, 200 overlap, keyword-overlap scoring, top three or opening fallback.
10. **Does it use FAISS or embeddings?** No. Current RAG uses neither.
11. **What is a tool?** A name, description, Pydantic schema, callable, and enabled flag.
12. **Can the model execute arbitrary Python?** No. Only registered tools execute, and generated code is never run.
13. **What is the agent?** A bounded plan/validate/execute/recover orchestration layer.
14. **Is planning LLM-generated?** No. `backend/agent/planner.py` is deterministic keyword planning.
15. **How are plans validated?** Tool existence, schemas, duplicate IDs, dependencies, cycles, and max steps.
16. **How are dependencies handled?** Executor runs only steps whose dependencies completed.
17. **How are references handled?** `$step_id.result.field` is resolved from prior context at runtime.
18. **How are failures handled?** Eligible failures retry once by default; failed dependents are skipped.
19. **How are infinite loops prevented?** Finite plans, cycle detection, max steps, and retry limits.
20. **Why a central AI runtime?** One place for model availability, settings, retries, structured validation, metrics, and provider abstraction.
21. **What if Ollama is down?** Health degrades and generation APIs return safe 503 errors.
22. **What if JSON is malformed?** One bounded repair attempt, then Pydantic validation or failure.
23. **What is SSE used for?** One-way workflow progress and completion events.
24. **Does SSE expose chain-of-thought?** No. It exposes safe labels only.
25. **How does frontend reconnect?** Up to three EventSource retries with increasing delays; no replay cursor.
26. **How are files secured?** Basename/sanitization, fixed output directory, resolved-parent checks, and download checks.
27. **How is caching implemented?** SQLite JSON cache with SHA-256-derived deterministic keys.
28. **What has been tested?** Backend 62 pass/3 skip; frontend lint/build pass; 2/3 frontend tests pass.
29. **What is not tested?** Real-model quality, end-to-end RAG quality, performance, auth, scaling, and production security.
30. **What would you improve?** Auth/isolation, durable jobs/events, hybrid retrieval with citations, observability, and benchmarked model quality.

## Important file paths

| Topic | Path |
|---|---|
| App composition | `backend/main.py` |
| Settings | `backend/config.py`, `.env.example` |
| Chat routing/API | `backend/core/router.py`, `backend/api/chat.py` |
| Runtime | `backend/core/llm.py`, `backend/runtime/generation.py`, `backend/runtime/ollama_provider.py` |
| Tools | `backend/core/tools.py`, `backend/core/executor.py` |
| Agent | `backend/agent/planner.py`, `validator.py`, `executor.py`, `recovery.py` |
| RAG | `backend/core/rag.py` |
| Intelligence | `backend/intelligence/base.py`, `models.py`, `backend/api/intelligence.py` |
| Code | `backend/code/base.py`, `tools.py`, `models.py` |
| Artifacts | `backend/generators/*`, `backend/api/files.py` |
| SSE | `backend/agent/activity.py`, `backend/api/agent.py`, `frontend/lib/sse.ts` |
| UI state | `frontend/hooks/useChat.ts`, `useAgent.ts`, `useActivityStream.ts` |
| Tests | `tests/*.py`, `frontend/components/activity/ThinkingIndicator.test.tsx` |

## Key numbers and test status

- Agent request message limit: 12,000 characters.
- Agent document IDs: maximum 10.
- Default agent max steps: 10.
- Default agent retries: 1.
- Default agent timeout setting: 300 seconds; current executor does not independently enforce a wall-clock timeout.
- PDF upload limit: 25 MB.
- RAG: 2,000-character chunks, 200-character overlap, maximum 3 retrieved chunks, context capped at 7,000 characters.
- Intelligence: default 5,000-character chunks, maximum 40 chunks.
- Code input default: 30,000 characters.
- Backend: 62 passed, 3 skipped.
- Frontend: 2 passed, 1 failed; lint passed; build passed.
- Real Qwen integration tests: skipped because Ollama/model was unavailable in the verification environment.

## Security points

The registry allowlists tools; Pydantic validates inputs; plans have max steps and cycle checks; retries are bounded; output filenames are sanitized and confined to `data/outputs`; document IDs are constrained; generated code is never executed; structured output is size-limited and schema-validated; CORS is configured to a frontend origin. Missing controls are authentication, authorization, tenant isolation, rate limiting, durable audit logs, and a true sandbox for any future execution features.

## Limitations

RAG is lexical rather than semantic and has no citations. Routing is heuristic. The 3B local model may be limited, but no quality number is claimed. Storage and activity are local/process-bound. Workflows are sequential. There is no distributed worker or production observability layer. Real model workflows and performance have not been benchmarked. The current frontend activity panel has a failing collapse test.

## “Why did you choose this?” answers

- **FastAPI:** typed APIs, straightforward routing, uploads, and `StreamingResponse`; trade-off is still needing production deployment controls.
- **Next.js:** React App Router and integrated build; trade-off is more frontend machinery than a small SPA.
- **Ollama:** local model serving with a simple client; trade-off is hardware/process dependency.
- **Qwen 2.5 3B:** small configured local model; trade-off is a lower reasoning ceiling than larger models.
- **SQLite:** zero-setup local cache; trade-off is poor distributed/multi-user scaling.
- **Pydantic:** one validation language for APIs, tools, plans, and model JSON; trade-off is strict schema failures.
- **SSE:** simple one-way activity stream; trade-off is no bidirectional protocol or durable replay.
- **Tool registry:** explicit allowlist and shared executor; trade-off is manual registration and process-local state.
- **Agent planner:** deterministic and bounded; trade-off is less flexible than an LLM planner.
- **CPU inference:** works without GPU; trade-off is expected slower throughput, not measured here.

## Scaling answer

“The current design is a local single-user prototype. To scale it, I would move document/artifact bytes to object storage, metadata and cache to PostgreSQL, events and transient state to Redis or a durable event store, and workflow execution to a queue-backed worker pool. I would add authentication, authorization, per-user namespaces, rate limits, tracing, metrics, and idempotency. Model serving would be separated from the API and benchmarked on GPU or a dedicated inference service. I would only claim a concurrency target after measuring P50/P95 latency, memory, tokens/sec, queue time, and failure recovery.”

## What would you improve?

“First, close the production safety boundary: authentication, authorization, tenant isolation, durable storage, and rate limits. Second, evaluate and improve RAG with page-aware hybrid retrieval, embeddings/reranking, citations, and no-answer behavior. Third, make workflows durable and observable. Fourth, build a real evaluation suite for chat, RAG, intelligence, code, and agent completion. Finally, fix the frontend activity collapse mismatch and reconcile the document storage paths/configuration.”

## Disclosure statement

“I used AI-assisted development to accelerate implementation, then reviewed and integrated the code, ran the available tests, investigated failures, and understand the actual request and execution flow. I describe unmeasured model behavior as unverified rather than claiming accuracy or performance.”

## Study priorities

1. **Critical:** FastAPI/Pydantic, async and SSE, Ollama/runtime behavior, RAG limitations, prompt injection, auth/filesystem security, and mock versus real-model testing.
2. **High:** DAG execution, retries/idempotency, caching, Next.js client state, observability, model serving, and benchmark design.
3. **Medium:** Hybrid/vector retrieval, Redis/job queues, PostgreSQL, cloud deployment, and code sandboxing.
