import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ReportTab from "./ReportTab";
import * as api from "../../lib/api";
import type { AdminReportOut } from "../../lib/types";

beforeEach(() => vi.clearAllMocks());

const report: AdminReportOut = {
  id: 1, type: "report",
  target_name: "홍길동", target_university: "연세대학교",
  reason: "부적절한 사진", created_at: "2026-08-03T14:30:00",
  handled: false,
  reporter_name: "김철수", reporter_university: "서울대학교",
};

const suggestion: AdminReportOut = {
  id: 2, type: "suggestion",
  target_name: null, target_university: null,
  reason: "알림 끄는 기능 주세요", created_at: "2026-08-03T15:00:00",
  handled: false,
  reporter_name: "이영희", reporter_university: "고려대학교",
};

describe("ReportTab", () => {
  it("신고는 대상 줄 표시, 건의는 미표시 + 유형 배지", async () => {
    vi.spyOn(api, "listReports").mockResolvedValue([report, suggestion]);
    render(<ReportTab />);
    await waitFor(() => expect(screen.getByText(/홍길동/)).toBeInTheDocument());
    expect(screen.getByText("신고")).toBeInTheDocument();
    expect(screen.getByText("건의")).toBeInTheDocument();
    expect(screen.getByText(/알림 끄는 기능/)).toBeInTheDocument();
    // 카드 2장 중 대상 줄은 신고 쪽 하나뿐이어야 한다
    expect(screen.getAllByText(/^대상:/)).toHaveLength(1);
  });

  it("신고자 이름·학교 표시", async () => {
    vi.spyOn(api, "listReports").mockResolvedValue([report]);
    render(<ReportTab />);
    await waitFor(() => expect(screen.getByText(/김철수/)).toBeInTheDocument());
    expect(screen.getByText(/서울대학교/)).toBeInTheDocument();
  });

  it("처리 완료 클릭 → API 호출 후 목록에서 제거", async () => {
    vi.spyOn(api, "listReports").mockResolvedValue([report]);
    const spy = vi.spyOn(api, "markReportHandled")
      .mockResolvedValue({ ...report, handled: true });
    render(<ReportTab />);
    await waitFor(() => screen.getByText(/홍길동/));
    fireEvent.click(screen.getByRole("button", { name: "처리 완료" }));
    await waitFor(() => expect(screen.queryByText(/홍길동/)).toBeNull());
    expect(spy).toHaveBeenCalledWith(1);
  });

  it("처리된 항목도 보기 체크 → include_handled=true 로 재조회", async () => {
    const spy = vi.spyOn(api, "listReports").mockResolvedValue([]);
    render(<ReportTab />);
    await waitFor(() => expect(spy).toHaveBeenCalledWith(false));
    fireEvent.click(screen.getByLabelText("처리된 항목도 보기"));
    await waitFor(() => expect(spy).toHaveBeenCalledWith(true));
  });

  it("로드 실패 시 에러 문구", async () => {
    vi.spyOn(api, "listReports").mockRejectedValue(new Error("fail"));
    render(<ReportTab />);
    await waitFor(() =>
      expect(screen.getByText("목록을 불러오지 못했어요.")).toBeInTheDocument(),
    );
  });
});
