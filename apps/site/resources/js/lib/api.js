// Client for this application's public API (/api/v1). The browser never calls the AI service.

const VISITOR_KEY = 'daleel:visitor';

/** Anonymous, per-browser id so answers can be rated and the admin area can group questions. */
export function visitorId() {
    try {
        let id = localStorage.getItem(VISITOR_KEY);
        if (!id) {
            id = crypto.randomUUID();
            localStorage.setItem(VISITOR_KEY, id);
        }
        return id;
    } catch {
        return null;
    }
}

function headers() {
    const id = visitorId();
    return { 'Content-Type': 'application/json', Accept: 'application/json', ...(id ? { 'X-Visitor-Id': id } : {}) };
}

export class ApiError extends Error {
    constructor(status, body) {
        super(body?.message || `HTTP ${status}`);
        this.status = status;
        this.body = body;
    }
}

/**
 * Ask a question. Resolves with the stored answer, or rejects with ApiError
 * (502/503 when the AI service failed, 422 for invalid input, 429 when rate limited).
 */
export async function ask({ query, channel = 'text', parentId = null, signal }) {
    const response = await fetch('/api/v1/ask', {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ query, channel, answer_mode: 'text', ...(parentId ? { parent_id: parentId } : {}) }),
        signal,
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) throw new ApiError(response.status, body);
    return body;
}

export async function sendFeedback(questionId, value, reason = null) {
    const response = await fetch(`/api/v1/questions/${questionId}/feedback`, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({ value, reason }),
    });
    if (!response.ok) throw new ApiError(response.status, null);
}

/** true when the AI service is reachable, false otherwise. */
export async function aiOnline() {
    try {
        const response = await fetch('/api/v1/status', { headers: { Accept: 'application/json' } });
        if (!response.ok) return false;
        return (await response.json()).ai === true;
    } catch {
        return false;
    }
}
