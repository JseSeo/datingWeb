import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Admin from "./Admin";
import * as api from "../../lib/api";

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(api, "listPendingVerifications").mockResolvedValue([]);
  vi.spyOn(api, "listReports").mockResolvedValue([]);
  vi.spyOn(api, "listMatchRounds").mockResolvedValue([]);
  vi.spyOn(api, "listUniversityWeights").mockResolvedValue([]);
  // 대학 가중치 탭의 학교 셀렉트가 마운트 시 호출하는 목록 API stub
  vi.spyOn(api, "listUniversities").mockResolvedValue([
    { id: 1, name: "서울대학교", active: true },
  ]);
  // 대학 목록 탭이 마운트 시 호출하는 전체 목록 API stub
  vi.spyOn(api, "listAllUniversities").mockResolvedValue([
    { id: 1, name: "서울대학교", active: true },
  ]);
});

describe("Admin", () => {
  it("기본 탭은 학생증 심사", async () => {
    render(<Admin />);
    await waitFor(() =>
      expect(screen.getByText("심사 대기 없음")).toBeInTheDocument(),
    );
    expect(api.listPendingVerifications).toHaveBeenCalled();
  });

  it("페이지 h1은 탭과 무관하게 '관리자' 하나", async () => {
    render(<Admin />);
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("관리자");
    fireEvent.click(screen.getByRole("tab", { name: "신고 · 건의" }));
    await waitFor(() => expect(api.listReports).toHaveBeenCalled());
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("관리자");
  });

  it("신고 · 건의 탭 클릭 시 해당 탭 렌더", async () => {
    render(<Admin />);
    fireEvent.click(screen.getByRole("tab", { name: "신고 · 건의" }));
    await waitFor(() => expect(api.listReports).toHaveBeenCalled());
    expect(screen.queryByText("심사 대기 없음")).toBeNull();
  });

  it("선택된 탭만 aria-selected=true", async () => {
    render(<Admin />);
    const verification = screen.getByRole("tab", { name: "학생증 심사" });
    const report = screen.getByRole("tab", { name: "신고 · 건의" });

    expect(verification).toHaveAttribute("aria-selected", "true");
    expect(report).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("tabpanel")).toHaveAttribute(
      "aria-labelledby",
      "tab-verification",
    );

    fireEvent.click(report);
    await waitFor(() =>
      expect(report).toHaveAttribute("aria-selected", "true"),
    );
    expect(verification).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("tabpanel")).toHaveAttribute(
      "aria-labelledby",
      "tab-report",
    );
  });

  it("라운드 탭 클릭 시 해당 탭 렌더", async () => {
    render(<Admin />);
    fireEvent.click(screen.getByRole("tab", { name: "라운드" }));
    await waitFor(() => expect(api.listMatchRounds).toHaveBeenCalled());
    expect(screen.queryByText("심사 대기 없음")).toBeNull();
    expect(screen.getByText("예정된 라운드 없음")).toBeInTheDocument();
  });

  it("대학 가중치 탭 클릭 시 해당 탭 렌더", async () => {
    render(<Admin />);
    fireEvent.click(screen.getByRole("tab", { name: "대학 가중치" }));
    await waitFor(() => expect(api.listUniversityWeights).toHaveBeenCalled());
    expect(screen.queryByText("심사 대기 없음")).toBeNull();
    expect(screen.getByText("등록된 규칙 없음")).toBeInTheDocument();
  });

  it("탭 5개 중 선택된 하나만 aria-selected=true", async () => {
    render(<Admin />);
    const round = screen.getByRole("tab", { name: "라운드" });
    expect(screen.getAllByRole("tab")).toHaveLength(5);
    expect(round).toHaveAttribute("aria-selected", "false");

    fireEvent.click(round);
    await waitFor(() => expect(round).toHaveAttribute("aria-selected", "true"));
    expect(screen.getByRole("tab", { name: "학생증 심사" })).toHaveAttribute(
      "aria-selected",
      "false",
    );
    expect(screen.getByRole("tabpanel")).toHaveAttribute(
      "aria-labelledby",
      "tab-round",
    );
  });
});
