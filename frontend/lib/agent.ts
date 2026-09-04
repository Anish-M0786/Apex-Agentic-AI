import { apiFetch, apiUrl } from './api';
import type { AgentResult, AgentStart } from '@/types/agent';

/** Start a streaming agent workflow. */
export const startAgent = (message: string, document_ids: string[] = []) =>
  apiFetch<AgentStart>('/api/agent/run?stream=true', {
    method: 'POST',
    body: JSON.stringify({ message, document_ids }),
  });

/**
 * Send a plain chat message. If document_ids are provided the backend will
 * decide whether to activate RAG based on the message intent.
 */
export const runChat = (
  message: string,
  document_ids: string[] = [],
  history: { role: 'user' | 'assistant'; content: string }[] = [],
) =>
  apiFetch<{ response: string; model: string; success: boolean }>('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message, document_ids, history }),
  });

/** Build an absolute download URL for an artifact filename. */
export const artifactUrl = (filename: string) =>
  apiUrl('/api/files/' + encodeURIComponent(filename));

/**
 * Resolve an artifact URL to an absolute URL pointing at the FastAPI backend.
 *
 * The backend emits relative paths like `/api/files/agent-result.pdf`.
 * If used as-is they resolve to localhost:3000 (Next.js) — a 404.
 * This function always produces an absolute http://127.0.0.1:8000/... URL.
 */
function resolveArtifactUrl(downloadUrl: string | undefined, filename: string): string {
  if (!downloadUrl) return artifactUrl(filename);
  // Already absolute (http:// or https://)
  if (/^https?:\/\//i.test(downloadUrl)) return downloadUrl;
  // Relative path — prepend the configured backend base URL
  return apiUrl(downloadUrl.startsWith('/') ? downloadUrl : '/' + downloadUrl);
}

/** Map raw AgentResult artifacts to the UI Artifact shape. */
export const asArtifacts = (result: AgentResult) =>
  (result.artifacts || []).map(a => ({
    filename: a.filename,
    type: a.type,
    url: resolveArtifactUrl(a.download_url, a.filename),
  }));