import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import TopNav from "./TopNav";

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <TopNav />
    </MemoryRouter>,
  );
}

describe("TopNav", () => {
  it("3개 링크 렌더", () => {
    renderAt("/home");
    expect(screen.getByRole("link", { name: "홈" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "게임" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "마이페이지" })).toBeInTheDocument();
  });

  it("현재 경로 링크에 active 표시 (aria-current)", () => {
    renderAt("/game");
    expect(screen.getByRole("link", { name: "게임" })).toHaveAttribute("aria-current", "page");
  });
});
