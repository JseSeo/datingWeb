import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Profile from "./Profile";
import * as api from "../../lib/api";

const user = {
  id: 1, email: "a@b.com", name: "김미", university: "서울대학교",
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
});
