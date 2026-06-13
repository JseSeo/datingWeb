import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { AuthProvider, useAuth } from "../src/lib/auth";
import * as api from "../src/lib/api";
import type { UserOut } from "../src/lib/types";

const fakeUser: UserOut = {
  id: 1, email: "a@b.com", name: "홍길동", university: "테스트대",
  status: "active", profile_photo: null, bio: null, instagram: null,
  kakao_id: null, phone: null, matching_paused: false, is_admin: false,
  created_at: "2026-06-13T00:00:00",
};

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe("useAuth", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("토큰 없으면 loading 끝나고 user null", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.user).toBeNull();
  });

  it("login 시 토큰 저장 + user 설정", async () => {
    vi.spyOn(api, "loginRequest").mockResolvedValue({ access_token: "tok", token_type: "bearer" });
    vi.spyOn(api, "fetchMe").mockResolvedValue(fakeUser);
    const setSpy = vi.spyOn(api, "setToken");

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    let returned: UserOut | undefined;
    await act(async () => {
      returned = await result.current.login("a@b.com", "password12");
    });

    expect(setSpy).toHaveBeenCalledWith("tok");
    expect(result.current.user).toEqual(fakeUser);
    expect(returned).toEqual(fakeUser);
  });

  it("logout 시 토큰삭제 + user null", async () => {
    vi.spyOn(api, "loginRequest").mockResolvedValue({ access_token: "tok", token_type: "bearer" });
    vi.spyOn(api, "fetchMe").mockResolvedValue(fakeUser);
    const clearSpy = vi.spyOn(api, "clearToken");

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => { await result.current.login("a@b.com", "password12"); });

    act(() => result.current.logout());
    expect(clearSpy).toHaveBeenCalled();
    expect(result.current.user).toBeNull();
  });
});
