import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiFetch, ApiError, getToken, setToken, clearToken } from "../src/lib/api";

describe("token storage", () => {
  beforeEach(() => localStorage.clear());

  it("set/get/clear 토큰", () => {
    expect(getToken()).toBeNull();
    setToken("abc");
    expect(getToken()).toBe("abc");
    clearToken();
    expect(getToken()).toBeNull();
  });
});

describe("apiFetch", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  function mockFetch(status: number, body: unknown) {
    return vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
    );
  }

  it("토큰 있으면 Authorization 헤더 첨부", async () => {
    setToken("tok123");
    const spy = mockFetch(200, { ok: true });
    await apiFetch("/me");
    const init = spy.mock.calls[0][1] as RequestInit;
    const headers = init.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer tok123");
  });

  it("성공 시 JSON 반환", async () => {
    mockFetch(200, { id: 1 });
    const data = await apiFetch<{ id: number }>("/me");
    expect(data.id).toBe(1);
  });

  it("non-2xx 시 detail 문자열로 ApiError throw", async () => {
    mockFetch(409, { detail: "이미 사용 중인 이메일입니다" });
    await expect(apiFetch("/auth/register", { method: "POST" })).rejects.toMatchObject({
      status: 409,
      message: "이미 사용 중인 이메일입니다",
    });
  });

  it("422 detail 배열이면 첫 msg 추출", async () => {
    mockFetch(422, { detail: [{ msg: "비밀번호는 8자 이상이어야 합니다", loc: ["body", "password"] }] });
    await expect(apiFetch("/auth/register", { method: "POST" })).rejects.toMatchObject({
      message: "비밀번호는 8자 이상이어야 합니다",
    });
  });

  it("401 시 토큰 삭제", async () => {
    setToken("tok");
    mockFetch(401, { detail: "unauthorized" });
    await expect(apiFetch("/me")).rejects.toBeInstanceOf(ApiError);
    expect(getToken()).toBeNull();
  });

  it("네트워크 실패 시 status 0 ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network down"));
    await expect(apiFetch("/me")).rejects.toMatchObject({ status: 0 });
  });

  it("204 응답 시 undefined 반환", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
    const result = await apiFetch("/me");
    expect(result).toBeUndefined();
  });
});
