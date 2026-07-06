import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Game from "./Game";
import * as api from "../../lib/api";

beforeEach(() => {
  vi.clearAllMocks();
  // 붉은실 탭 마운트 시 호출되는 로드 API stub
  vi.spyOn(api, "getRedThread").mockResolvedValue({ targets: [] });
  vi.spyOn(api, "getRedThreadReceived").mockResolvedValue({ count: 0 });
});

describe("Game", () => {
  it("기본은 오작교 탭 노출", () => {
    render(<Game />);
    expect(screen.getByRole("button", { name: "중매하기" })).toBeInTheDocument();
  });

  it("붉은실 탭 클릭 시 붉은실 화면으로 전환", async () => {
    render(<Game />);
    fireEvent.click(screen.getByRole("button", { name: "붉은실" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "저장" })).toBeInTheDocument(),
    );
  });
});
