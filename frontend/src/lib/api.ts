import type { TokenResponse, UserOut, RegisterPayload } from "./types";

const BASE = import.meta.env.VITE_API_URL;
const TOKEN_KEY = "datedrop_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function parseDetail(body: unknown): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length && typeof (detail[0] as { msg?: unknown })?.msg === "string") {
    return (detail[0] as { msg: string }).msg;
  }
  return "요청 처리 중 오류가 발생했습니다";
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, "서버 연결에 실패했습니다");
  }

  if (res.status === 401) clearToken();

  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      /* 본문 없음 */
    }
    throw new ApiError(res.status, parseDetail(body));
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function registerUser(payload: RegisterPayload): Promise<UserOut> {
  return apiFetch<UserOut>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loginRequest(email: string, password: string): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function fetchMe(): Promise<UserOut> {
  return apiFetch<UserOut>("/me", { method: "GET" });
}
