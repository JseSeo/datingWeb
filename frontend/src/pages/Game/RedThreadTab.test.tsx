import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import RedThreadTab from "./RedThreadTab";
import * as api from "../../lib/api";

beforeEach(() => vi.clearAllMocks());

function mockLoad(targets: { target_name: string; target_university: string }[], count: number) {
  vi.spyOn(api, "getRedThread").mockResolvedValue({ targets });
  vi.spyOn(api, "getRedThreadReceived").mockResolvedValue({ count });
}

describe("RedThreadTab", () => {
  it("마운트 시 기존 지목 prefill + 받은 인원수 표시", async () => {
    mockLoad([{ target_name: "이영희", target_university: "연세대학교" }], 3);
    render(<RedThreadTab />);
    await waitFor(() =>
      expect((screen.getByLabelText("상대1 이름") as HTMLInputElement).value).toBe("이영희"),
    );
    expect(screen.getByText("나를 3명이 지목했어요")).toBeInTheDocument();
  });

  it("받은 인원 0명이면 안내 문구", async () => {
    mockLoad([], 0);
    render(<RedThreadTab />);
    await waitFor(() =>
      expect(screen.getByText("아직 나를 지목한 사람이 없어요")).toBeInTheDocument(),
    );
  });

  it("두 슬롯이 같으면 제출 막고 에러", async () => {
    mockLoad([], 0);
    const spy = vi.spyOn(api, "postRedThread");
    render(<RedThreadTab />);
    await waitFor(() => screen.getByLabelText("상대1 이름"));
    fireEvent.change(screen.getByLabelText("상대1 이름"), { target: { value: "이영희" } });
    fireEvent.change(screen.getByLabelText("상대1 학교"), { target: { value: "연세대학교" } });
    fireEvent.change(screen.getByLabelText("상대2 이름"), { target: { value: "이영희" } });
    fireEvent.change(screen.getByLabelText("상대2 학교"), { target: { value: "연세대학교" } });
    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    await waitFor(() =>
      expect(screen.getByText("같은 사람을 두 번 넣을 수 없어요")).toBeInTheDocument(),
    );
    expect(spy).not.toHaveBeenCalled();
  });

  it("저장 성공 시 메시지 표시", async () => {
    mockLoad([], 0);
    vi.spyOn(api, "postRedThread").mockResolvedValue({
      targets: [{ target_name: "이영희", target_university: "연세대학교" }],
    });
    render(<RedThreadTab />);
    await waitFor(() => screen.getByLabelText("상대1 이름"));
    fireEvent.change(screen.getByLabelText("상대1 이름"), { target: { value: "이영희" } });
    fireEvent.change(screen.getByLabelText("상대1 학교"), { target: { value: "연세대학교" } });
    fireEvent.click(screen.getByRole("button", { name: "저장" }));
    await waitFor(() =>
      expect(screen.getByText("저장됐어요")).toBeInTheDocument(),
    );
  });
});
