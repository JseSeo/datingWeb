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

  it("신고 · 건의 탭 클릭 시 해당 탭 렌더", async () => {
    render(<Admin />);
    fireEvent.click(screen.getByRole("button", { name: "신고 · 건의" }));
    await waitFor(() => expect(api.listReports).toHaveBeenCalled());
    expect(screen.queryByText("심사 대기 없음")).toBeNull();
  });
});
