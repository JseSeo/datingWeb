import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Pending from "./Pending";
import * as api from "../../lib/api";

const navigate = vi.fn();
vi.mock("react-router-dom", async (orig) => ({
  ...(await orig<typeof import("react-router-dom")>()),
  useNavigate: () => navigate,
}));
vi.mock("../../lib/auth", () => ({ useAuth: () => ({ logout: vi.fn() }) }));

beforeEach(() => {
  vi.clearAllMocks();
  URL.createObjectURL = vi.fn(() => "blob:mock");
});

const baseUser = {
  id: 1, email: "a@b.com", name: "테스터", university: "서울대학교",
  status: "pending" as const, profile_photo: null, bio: null,
  instagram: null, kakao_id: null, phone: null,
  matching_paused: false, is_admin: false, created_at: "2026-07-06",
};
const verifBase = {
  id: 1, user_id: 1, image_url: "x",
  reviewed_at: null, created_at: "2026-07-06",
};

function mock(userStatus: "pending" | "active", verif: unknown) {
  vi.spyOn(api, "fetchMe").mockResolvedValue({ ...baseUser, status: userStatus });
  vi.spyOn(api, "getMyVerification").mockResolvedValue(verif as never);
}

describe("Pending", () => {
  it("verification 없으면 업로드 안내 + 폼", async () => {
    mock("pending", null);
    render(<Pending />);
    await waitFor(() => expect(screen.getByText(/학생증을 올려/)).toBeInTheDocument());
    expect(screen.getByLabelText("학생증 파일")).toBeInTheDocument();
  });

  it("pending이면 검토 중 표시", async () => {
    mock("pending", { ...verifBase, status: "pending" });
    render(<Pending />);
    await waitFor(() => expect(screen.getByText(/검토 중/)).toBeInTheDocument());
  });

  it("rejected면 반려 안내", async () => {
    mock("pending", { ...verifBase, status: "rejected" });
    render(<Pending />);
    await waitFor(() => expect(screen.getByText(/반려/)).toBeInTheDocument());
  });

  it("active면 홈으로 이동", async () => {
    mock("active", null);
    render(<Pending />);
    await waitFor(() => expect(navigate).toHaveBeenCalledWith("/home"));
  });
});
