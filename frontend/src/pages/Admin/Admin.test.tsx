import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Admin from "./Admin";
import * as api from "../../lib/api";

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(api, "listPendingVerifications").mockResolvedValue([]);
  vi.spyOn(api, "listReports").mockResolvedValue([]);
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

    fireEvent.click(report);
    await waitFor(() =>
      expect(report).toHaveAttribute("aria-selected", "true"),
    );
    expect(verification).toHaveAttribute("aria-selected", "false");
  });
});
