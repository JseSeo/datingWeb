import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Profile from "./Profile";
import * as api from "../../lib/api";

const user = {
  id: 1, email: "a@b.com", name: "김미", university: "서울대학교",
  gender: "female" as const,
  status: "active" as const, profile_photo: null, bio: null,
  instagram: null, kakao_id: null, phone: null,
  matching_paused: false, is_admin: false, created_at: "2026-01-01",
};

vi.mock("../../lib/auth", () => ({
  useAuth: () => ({ user, refreshUser: vi.fn().mockResolvedValue(undefined) }),
}));

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => navigate };
});

beforeEach(() => vi.clearAllMocks());

function renderProfile() {
  render(<MemoryRouter><Profile /></MemoryRouter>);
}

describe("Profile", () => {
  it("연락처 3개 모두 비면 저장 막고 에러 표시", async () => {
    const spy = vi.spyOn(api, "updateProfile");
    renderProfile();
    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    await waitFor(() =>
      expect(screen.getByText("연락처를 1개 이상 입력하세요")).toBeInTheDocument(),
    );
    expect(spy).not.toHaveBeenCalled();
  });

  it("연락처 1개 있으면 저장 호출", async () => {
    const spy = vi.spyOn(api, "updateProfile").mockResolvedValue(user);
    renderProfile();
    fireEvent.change(screen.getByLabelText("인스타그램"), {
      target: { value: "myig" },
    });
    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    await waitFor(() => expect(spy).toHaveBeenCalled());
  });

  it("마지막 연락처 삭제 시도가 서버에서 거부되면 서버 메시지를 그대로 보여준다", async () => {
    vi.spyOn(api, "updateProfile").mockRejectedValue(
      new api.ApiError(422, "연락처는 최소 1개를 남겨야 합니다"),
    );
    renderProfile();
    // 클라이언트 사전 체크를 통과시키기 위해 1개는 채우되, 서버가 병합 결과로 거부하는 상황을 가정한다
    fireEvent.change(screen.getByLabelText("인스타그램"), {
      target: { value: "myig" },
    });
    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    expect(
      await screen.findByText("연락처는 최소 1개를 남겨야 합니다"),
    ).toBeInTheDocument();
  });
});
