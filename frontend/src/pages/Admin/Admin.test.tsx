import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Admin from "./Admin";
import * as api from "../../lib/api";

beforeEach(() => {
  vi.clearAllMocks();
});

const entry = {
  id: 5, user_id: 2, status: "pending" as const,
  reviewed_at: null, created_at: "2026-07-06",
  name: "김학생", university: "연세대학교",
};

describe("Admin", () => {
  it("목록 로드 후 이름·대학 표시", async () => {
    vi.spyOn(api, "listPendingVerifications").mockResolvedValue([entry]);
    render(<Admin />);
    await waitFor(() => expect(screen.getByText("김학생")).toBeInTheDocument());
    expect(screen.getByText(/연세대학교/)).toBeInTheDocument();
  });

  it("빈 목록이면 안내 문구", async () => {
    vi.spyOn(api, "listPendingVerifications").mockResolvedValue([]);
    render(<Admin />);
    await waitFor(() => expect(screen.getByText("심사 대기 없음")).toBeInTheDocument());
  });

  it("로드 실패면 에러 표시", async () => {
    vi.spyOn(api, "listPendingVerifications").mockRejectedValue(new Error("fail"));
    render(<Admin />);
    await waitFor(() =>
      expect(screen.getByText("목록을 불러오지 못했어요.")).toBeInTheDocument(),
    );
  });

  it("학생증 보기 클릭 → 이미지 로드", async () => {
    vi.spyOn(api, "listPendingVerifications").mockResolvedValue([entry]);
    vi.spyOn(api, "fetchVerificationImage").mockResolvedValue("blob:mock-url");
    render(<Admin />);
    await waitFor(() => screen.getByText("김학생"));
    fireEvent.click(screen.getByRole("button", { name: "학생증 보기" }));
    await waitFor(() =>
      expect(screen.getByAltText("김학생 학생증")).toHaveAttribute("src", "blob:mock-url"),
    );
    expect(api.fetchVerificationImage).toHaveBeenCalledWith(5);
  });

  it("승인 클릭 → reviewVerification 호출 후 카드 제거", async () => {
    vi.spyOn(api, "listPendingVerifications").mockResolvedValue([entry]);
    vi.spyOn(api, "reviewVerification").mockResolvedValue({ ...entry, status: "approved" });
    render(<Admin />);
    await waitFor(() => screen.getByText("김학생"));
    fireEvent.click(screen.getByRole("button", { name: "승인" }));
    await waitFor(() => expect(screen.queryByText("김학생")).toBeNull());
    expect(api.reviewVerification).toHaveBeenCalledWith(5, "approve");
  });

  it("반려 클릭 → reject 액션", async () => {
    vi.spyOn(api, "listPendingVerifications").mockResolvedValue([entry]);
    vi.spyOn(api, "reviewVerification").mockResolvedValue({ ...entry, status: "rejected" });
    render(<Admin />);
    await waitFor(() => screen.getByText("김학생"));
    fireEvent.click(screen.getByRole("button", { name: "반려" }));
    await waitFor(() => expect(api.reviewVerification).toHaveBeenCalledWith(5, "reject"));
  });
});
