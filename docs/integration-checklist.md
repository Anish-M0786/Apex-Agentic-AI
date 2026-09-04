# Apex Integration Checklist

> **Instructions**: Run each test manually against a live backend + frontend. Mark results with ✅ Pass, ❌ Fail, ⚠️ Partial, or ⏭️ Skipped (with reason).
>
> Backend: `http://127.0.0.1:8000`  
> Frontend: `http://localhost:3000`  
> Model: `qwen2.5:3b`

---

## 1. Startup

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 1.1 | Ollama running | `ollama list` shows `qwen2.5:3b` | ⬜ | |
| 1.2 | Backend starts | `uvicorn` starts without errors | ⬜ | |
| 1.3 | `/health` returns healthy | `{"status":"healthy","ollama":true,"model_available":true}` | ⬜ | |
| 1.4 | `/api/runtime/health` | `available: true`, `model_available: true` | ⬜ | |
| 1.5 | Frontend starts | `npm run dev` starts without errors | ⬜ | |
| 1.6 | Frontend loads | `http://localhost:3000` renders without console errors | ⬜ | |
| 1.7 | Header status | Shows `● Connected` when backend is up | ⬜ | |
| 1.8 | Sidebar model panel | Shows `Qwen 2.5 3B / Ollama / Connected` | ⬜ | |

---

## 2. Chat

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 2.1 | Plain chat: "What is binary search?" | Qwen response in chat | ⬜ | |
| 2.2 | Thinking state | `Thinking` indicator while request is in-flight | ⬜ | |
| 2.3 | Thinking → completed | Indicator disappears when response arrives | ⬜ | |
| 2.4 | Code response: "Write a Python binary search function" | Code block with syntax highlighting + copy button | ⬜ | |
| 2.5 | Multi-turn: follow-up question | Context within conversation visible in UI | ⬜ | |
| 2.6 | "What is the capital of France?" | Plain Qwen answer, no RAG triggered | ⬜ | |

---

## 3. PDF Creation (Agent Workflow)

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 3.1 | "Create a PDF explaining binary search" | Agent starts, SSE connects | ⬜ | |
| 3.2 | Activity panel appears | Shows `✦ Working…` with activity items | ⬜ | |
| 3.3 | Activity sequence | Thinking → Planning → Tool execution → Created PDF | ⬜ | |
| 3.4 | Artifact card | PDF card with filename, Open and Download buttons | ⬜ | |
| 3.5 | Download works | `/api/files/{filename}` serves the file | ⬜ | |
| 3.6 | Activity collapses | Panel collapses after completion (1s delay) | ⬜ | |
| 3.7 | Expandable | User can re-expand activity panel | ⬜ | |

---

## 4. Excel Creation (Agent Workflow)

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 4.1 | "Create an Excel spreadsheet with 10 binary search questions" | Agent workflow starts | ⬜ | |
| 4.2 | XLSX artifact card | Shows with Table2 icon | ⬜ | |
| 4.3 | Download `.xlsx` | File downloads and opens in Excel/LibreOffice | ⬜ | |

---

## 5. PPT Creation

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 5.1 | "Create a PowerPoint presentation on binary search" | PPTX artifact card | ⬜ | |
| 5.2 | Download `.pptx` | File downloads and opens | ⬜ | |

---

## 6. DOCX Creation

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 6.1 | "Create a Word document explaining recursion" | DOCX artifact card | ⬜ | |
| 6.2 | Download `.docx` | File downloads and opens | ⬜ | |

---

## 7. Multi-Step Workflow

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 7.1 | "Create a PDF and an Excel spreadsheet with 10 binary search interview questions" | Both artifacts produced | ⬜ | |
| 7.2 | Activity sequence | Planning → step 1 → step 2 → Completed | ⬜ | |
| 7.3 | Both artifact cards shown | PDF card + XLSX card | ⬜ | |

---

## 8. PDF Upload

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 8.1 | Upload PDF via UI | Upload button triggers `POST /api/documents/upload` | ⬜ | |
| 8.2 | Document ready indicator | `✓ 1 document ready` shown below chat | ⬜ | |
| 8.3 | `document_id` returned | Frontend stores ID, not path | ⬜ | |
| 8.4 | No path exposure | Response has `document_id` and `filename`, no filesystem path | ⬜ | |
| 8.5 | Re-upload same file | Frontend deduplicates by ID | ⬜ | |

---

## 9. PDF Chat (RAG)

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 9.1 | Upload PDF, then "Summarize this document" | RAG path triggered, Qwen answers from document | ⬜ | |
| 9.2 | "What are the important topics in Unit 2?" | RAG retrieval, relevant answer | ⬜ | |
| 9.3 | "What is deadlock?" (no doc signal) | Plain Qwen answer, NOT RAG | ⬜ | |
| 9.4 | Thinking indicator shown | Appears while RAG+Qwen runs | ⬜ | |
| 9.5 | No chunk IDs or paths in response | Response is clean prose | ⬜ | |

---

## 10. Document Intelligence

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 10.1 | "Create exam notes from this PDF" | Agent workflow, notes generated | ⬜ | |
| 10.2 | Activity events | Appropriate events shown (no internal details) | ⬜ | |
| 10.3 | "Generate 20 MCQs from this document and export to Excel" | Quiz + XLSX artifact | ⬜ | |
| 10.4 | XLSX artifact downloadable | Opens with questions in rows | ⬜ | |

---

## 11. Code Intelligence

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 11.1 | "Write a Python binary search function" | Code block rendered with syntax highlighting | ⬜ | |
| 11.2 | Copy button | Copies code to clipboard | ⬜ | |
| 11.3 | "Debug this Python code: `def add(a, b)\n    return a + b`" | Structured debug response | ⬜ | |
| 11.4 | Generated code NOT executed | Backend returns text only | ⬜ | |

---

## 12. SSE Activity Stream

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 12.1 | SSE connects on agent start | `GET /api/agent/events/{id}` opens | ⬜ | |
| 12.2 | Events arrive in order | Thinking → Planning → Tool → Completion | ⬜ | |
| 12.3 | `complete` event closes stream | SSE connection closes after completion | ⬜ | |
| 12.4 | No prompts exposed | Activity labels are user-friendly only | ⬜ | |
| 12.5 | No stack traces in events | Error events say "failed" not exception text | ⬜ | |

---

## 13. Artifact Downloads

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 13.1 | PDF download URL | `/api/files/{filename}` — no path traversal possible | ⬜ | |
| 13.2 | Open in browser | PDF opens in-browser | ⬜ | |
| 13.3 | Invalid filename | Returns 404, not 500 | ⬜ | |

---

## 14. Error Handling

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 14.1 | Stop backend, send chat | Shows "Something went wrong." in chat | ⬜ | |
| 14.2 | Header shows unavailable | `○ Backend unavailable` in header | ⬜ | |
| 14.3 | Stop Ollama, send chat | 503 → "Unable to reach… Ollama model." in UI | ⬜ | |
| 14.4 | Invalid document ID | 422 error shown as safe message | ⬜ | |
| 14.5 | React app doesn't crash | Error is isolated to message, UI continues | ⬜ | |
| 14.6 | No Python exceptions in UI | Never see tracebacks or raw exception text | ⬜ | |

---

## 15. SSE Disconnect / Reconnect

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 15.1 | Stop backend mid-stream | SSE error handler fires | ⬜ | |
| 15.2 | Reconnect attempts | Max 3 attempts with backoff (350ms, 700ms, 1400ms) | ⬜ | |
| 15.3 | After 3 failures | "Activity connection was interrupted." shown | ⬜ | |
| 15.4 | No infinite reconnect | SSE does not loop forever | ⬜ | |

---

## 16. Mobile / Responsive

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 16.1 | Desktop: sidebar visible | Sidebar always open, no overflow | ⬜ | |
| 16.2 | Mobile: sidebar hidden | Sidebar off-screen, menu button visible | ⬜ | |
| 16.3 | Mobile: sidebar opens | Drawer slides in on menu button | ⬜ | |
| 16.4 | Mobile: message compose | Textarea and send button usable | ⬜ | |
| 16.5 | Mobile: artifact cards | Cards wrap properly, download accessible | ⬜ | |
| 16.6 | No horizontal overflow | `max-width: 700px` media query prevents scroll | ⬜ | |

---

## 17. Automated Tests

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 17.1 | `python -m pytest -q` | ≥ 62 passed, ≤ 3 skipped, 0 errors | ⬜ | |
| 17.2 | `npm test` | 3 passed | ⬜ | |
| 17.3 | `npm run lint` | 0 errors | ⬜ | |
| 17.4 | `npm run build` | Build completes without errors | ⬜ | |

---

## 18. Production Build

| # | Test | Expected | Result | Notes |
|---|------|----------|--------|-------|
| 18.1 | `npm run build` | No TypeScript errors | ⬜ | |
| 18.2 | No hard-coded backend URLs | `grep -r "127.0.0.1" app components hooks lib` returns nothing | ⬜ | |
| 18.3 | No `olmo2.5` references | `findstr /r /s "olmo2.5" *` returns nothing in active code | ⬜ | |

---

## Summary

| Category | Pass | Fail | Partial | Skipped |
|----------|------|------|---------|---------|
| Startup | | | | |
| Chat | | | | |
| PDF creation | | | | |
| Excel/PPT/DOCX | | | | |
| Multi-step workflow | | | | |
| PDF upload | | | | |
| PDF chat (RAG) | | | | |
| Document intelligence | | | | |
| Code intelligence | | | | |
| SSE | | | | |
| Artifacts | | | | |
| Error handling | | | | |
| Mobile | | | | |
| Automated tests | | | | |
| **Total** | | | | |

---

_Last updated: 2026-08-14_
