/** Shared API error + client types for the EvalForge Control Plane. */

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    retryable: boolean;
    details?: Record<string, unknown>;
  };
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;
  readonly details: Record<string, unknown> | undefined;

  constructor(
    message: string,
    options: {
      status: number;
      code: string;
      retryable?: boolean;
      details?: Record<string, unknown>;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code;
    this.retryable = options.retryable ?? false;
    this.details = options.details;
  }
}

export function getApiBaseUrl(): string {
  const configured = process.env["NEXT_PUBLIC_API_URL"]?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "http://localhost:8000";
}

export interface ApiRequestOptions {
  method?: string;
  body?: unknown;
  token?: string | null;
  signal?: AbortSignal;
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (options.token) {
    headers["Authorization"] = `Bearer ${options.token}`;
  }

  const init: RequestInit = {
    method: options.method ?? (options.body !== undefined ? "POST" : "GET"),
    headers,
    cache: "no-store",
  };
  if (options.body !== undefined) {
    init.body = JSON.stringify(options.body);
  }
  if (options.signal) {
    init.signal = options.signal;
  }

  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, init);
  } catch (cause) {
    throw new ApiError("Unable to reach the EvalForge API", {
      status: 0,
      code: "NETWORK_ERROR",
      retryable: true,
      details: { cause: cause instanceof Error ? cause.message : String(cause) },
    });
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? ((await response.json()) as unknown) : null;

  if (!response.ok) {
    const errorPayload =
      payload !== null && typeof payload === "object" && "error" in payload
        ? (payload as ApiErrorBody)
        : null;
    const statusLabel = String(response.status);
    const errorOptions: {
      status: number;
      code: string;
      retryable: boolean;
      details?: Record<string, unknown>;
    } = {
      status: response.status,
      code: errorPayload?.error.code ?? "HTTP_ERROR",
      retryable: errorPayload?.error.retryable ?? false,
    };
    if (errorPayload?.error.details) {
      errorOptions.details = errorPayload.error.details;
    }
    throw new ApiError(
      errorPayload?.error.message ?? `Request failed (${statusLabel})`,
      errorOptions,
    );
  }

  return payload as T;
}
