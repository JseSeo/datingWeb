import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import MyPage from "./MyPage";
import * as api from "../../lib/api";

const user = {
  id: 1, email: "a@b.com", name: "김미", university: "서울대학교",
  status: "active" as const, profile_photo: null, bio: null,
  instagram: null, kakao_id: null, phone: null,
  matching_paused: false, is_admin: false, created_at: "2026-01-01",
};

const logout = vi.fn();
const refreshUser = vi.fn();
vi.mock("../../lib/auth", () => ({
  useAuth: () => ({ user, logout, refreshUser }),
}));

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => navigate };
});

beforeEach(() => vi.clearAllMocks());

function renderMyPage() {
  render(<MemoryRouter><MyPage /></MemoryRouter>);
}

describe("MyPage", () => {
  it("탈퇴 confirm 후 withdraw 호출 + logout + 랜딩 이동", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const spy = vi.spyOn(api, "withdraw").mockResolvedValue(undefined);
    renderMyPage();
    fireEvent.click(screen.getByRole("button", { name: /회원 탈퇴/ }));
    await waitFor(() => expect(spy).toHaveBeenCalled());
    expect(logout).toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith("/");
  });

  it("탈퇴 실패 시 에러 표시 + 리다이렉트 안 함", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(api, "withdraw").mockRejectedValue(
      new api.ApiError(500, "서버 오류"),
    );
    renderMyPage();
    fireEvent.click(screen.getByRole("button", { name: /회원 탈퇴/ }));
    await waitFor(() => expect(screen.getByText("서버 오류")).toBeInTheDocument());
    expect(logout).not.toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("가치관 설문 클릭 시 /survey 이동", () => {
    renderMyPage();
    fireEvent.click(screen.getByRole("button", { name: /가치관 설문/ }));
    expect(navigate).toHaveBeenCalledWith("/survey");
  });

  it("탈퇴 confirm 취소 시 withdraw 호출 안 함", () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const spy = vi.spyOn(api, "withdraw");
    renderMyPage();
    fireEvent.click(screen.getByRole("button", { name: /회원 탈퇴/ }));
    expect(spy).not.toHaveBeenCalled();
  });

  it("신고 & 건의 클릭 시 /report 이동", () => {
    renderMyPage();
    fireEvent.click(screen.getByRole("button", { name: /신고 & 건의/ }));
    expect(navigate).toHaveBeenCalledWith("/report");
  });

  it("매칭 일시중지 토글 성공 시 refreshUser 호출", async () => {
    const spy = vi
      .spyOn(api, "toggleMatchingPause")
      .mockResolvedValue({ ...user, gender: "female" });
    renderMyPage();
    fireEvent.click(screen.getByRole("button", { name: /매칭 일시중지/ }));
    await waitFor(() => expect(spy).toHaveBeenCalledWith(true));
    expect(refreshUser).toHaveBeenCalled();
  });

  it("매칭 일시중지 토글 실패 시 refreshUser 호출 안 함", async () => {
    vi.spyOn(api, "toggleMatchingPause").mockRejectedValue(
      new api.ApiError(500, "서버 오류"),
    );
    renderMyPage();
    fireEvent.click(screen.getByRole("button", { name: /매칭 일시중지/ }));
    // 롤백으로 OFF가 다시 뜨면 catch 블록이 끝났다는 뜻 — 그 시점에 확정 검증
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /매칭 일시중지/ })).toHaveTextContent("OFF"),
    );
    expect(refreshUser).not.toHaveBeenCalled();
  });

  it("저장 성공 후 refreshUser가 실패해도 롤백하지 않음", async () => {
    vi.spyOn(api, "toggleMatchingPause").mockResolvedValue({
      ...user,
      gender: "female",
    });
    refreshUser.mockRejectedValueOnce(new api.ApiError(500, "서버 오류"));
    renderMyPage();
    fireEvent.click(screen.getByRole("button", { name: /매칭 일시중지/ }));
    await waitFor(() => expect(refreshUser).toHaveBeenCalled());
    // 서버엔 이미 저장됐다. 갱신 실패로 UI가 되돌아가면 서버와 어긋난다
    expect(
      screen.getByRole("button", { name: /매칭 일시중지/ }),
    ).toHaveTextContent("ON");
  });
});
