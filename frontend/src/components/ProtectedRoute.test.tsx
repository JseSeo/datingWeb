import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "./ProtectedRoute";
import * as auth from "../lib/auth";

const baseUser = {
  id: 1, email: "a@b.com", name: "테스터", university: "서울대학교",
  status: "active" as const, profile_photo: null, bio: null,
  instagram: null, kakao_id: null, phone: null,
  matching_paused: false, is_admin: false, created_at: "2026-07-06",
};

function renderAt(user: typeof baseUser | null) {
  vi.spyOn(auth, "useAuth").mockReturnValue({
    user, loading: false,
    login: vi.fn(), logout: vi.fn(), refreshUser: vi.fn(),
  });
  return render(
    <MemoryRouter initialEntries={["/admin"]}>
      <Routes>
        <Route path="/home" element={<p>홈</p>} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute requireAdmin>
              <p>관리자 화면</p>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute requireAdmin", () => {
  it("admin이면 통과", () => {
    renderAt({ ...baseUser, is_admin: true });
    expect(screen.getByText("관리자 화면")).toBeInTheDocument();
  });

  it("비admin active는 /home으로 redirect", () => {
    renderAt({ ...baseUser, is_admin: false });
    expect(screen.getByText("홈")).toBeInTheDocument();
    expect(screen.queryByText("관리자 화면")).toBeNull();
  });
});
