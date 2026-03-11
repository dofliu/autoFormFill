/** Request body sent to POST /api/v1/email/draft. */
export interface EmailDraftRequest {
  recipient_name: string;
  recipient_email: string;
  subject_hint?: string;
  purpose: string;
  tone?: "professional" | "friendly" | "formal";
  collections?: string[];
  n_results?: number;
  user_id?: number;
}

// SSE events reuse the same types as chat (SSEEvent from types/chat.ts)
