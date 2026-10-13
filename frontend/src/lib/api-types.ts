// Types and helpers shared by server code and the browser. No server-only values here.

export type HealthResponse = {
  status: "ok";
  service: string;
  version: string;
  environment: string;
};

export type Role = "system" | "user" | "assistant";

export type ChatMessage = {
  role: Role;
  content: string;
};

export type ChatCompletionRequest = {
  model: string;
  messages: ChatMessage[];
  max_tokens?: number;
  temperature?: number;
};

export type Usage = {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
};

export type ChatCompletionResponse = {
  id: string;
  object: "chat.completion";
  created: number;
  model: string;
  provider: string;
  choices: { index: number; message: ChatMessage; finish_reason: string }[];
  usage: Usage;
  latency_ms: number;
};

export type ModelInfo = {
  id: string;
  object: "model";
  owned_by: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly type?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Read a JSON body, throwing `ApiError` with the gateway's normalized error message on failure. */
export async function readJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed with HTTP ${res.status}.`;
    let type: string | undefined;
    try {
      const body = (await res.json()) as { error?: { message?: string; type?: string } };
      message = body.error?.message ?? message;
      type = body.error?.type;
    } catch {
      // Non-JSON error body; keep the generic message.
    }
    throw new ApiError(message, res.status, type);
  }
  return (await res.json()) as T;
}
