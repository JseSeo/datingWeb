import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ConsentModal } from "./ConsentModal";

describe("ConsentModal", () => {
  it("Esc 키로 닫힌다", () => {
    const onClose = vi.fn();
    render(<ConsentModal type="terms" onClose={onClose} />);

    fireEvent.keyDown(document, { key: "Escape" });

    expect(onClose).toHaveBeenCalled();
  });

  it("Esc 외의 키로는 닫히지 않는다", () => {
    const onClose = vi.fn();
    render(<ConsentModal type="terms" onClose={onClose} />);

    fireEvent.keyDown(document, { key: "Enter" });

    expect(onClose).not.toHaveBeenCalled();
  });

  it("배경을 누르면 닫힌다", () => {
    const onClose = vi.fn();
    render(<ConsentModal type="terms" onClose={onClose} />);

    fireEvent.click(screen.getByRole("dialog"));

    expect(onClose).toHaveBeenCalled();
  });

  it("내용 영역을 눌러도 닫히지 않는다", () => {
    const onClose = vi.fn();
    render(<ConsentModal type="terms" onClose={onClose} />);

    fireEvent.click(screen.getByRole("heading", { name: "이용약관" }));

    expect(onClose).not.toHaveBeenCalled();
  });

  it("닫기 버튼으로 닫힌다", () => {
    const onClose = vi.fn();
    render(<ConsentModal type="terms" onClose={onClose} />);

    fireEvent.click(screen.getByRole("button", { name: "닫기" }));

    expect(onClose).toHaveBeenCalled();
  });
});
