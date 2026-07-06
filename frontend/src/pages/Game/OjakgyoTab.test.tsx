import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import OjakgyoTab from "./OjakgyoTab";
import * as api from "../../lib/api";
import { ApiError } from "../../lib/api";

beforeEach(() => vi.clearAllMocks());

function fill(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

describe("OjakgyoTab", () => {
  it("두 사람이 같으면 제출 막고 에러 표시", async () => {
    const spy = vi.spyOn(api, "postOjakgyo");
    render(<OjakgyoTab />);
    fill("사람1 이름", "김철수");
    fill("사람1 학교", "서울대학교");
    fill("사람2 이름", "김철수");
    fill("사람2 학교", "서울대학교");
    fireEvent.click(screen.getByRole("button", { name: "중매하기" }));
    await waitFor(() =>
      expect(screen.getByText("두 사람이 같아요")).toBeInTheDocument(),
    );
    expect(spy).not.toHaveBeenCalled();
  });

  it("성공 시 완료 메시지 표시 + 폼 리셋", async () => {
    vi.spyOn(api, "postOjakgyo").mockResolvedValue({
      id: 1, recommender_id: 1,
      person_a_name: "김철수", person_a_university: "서울대학교",
      person_b_name: "이영희", person_b_university: "연세대학교",
      created_at: "2026-01-01",
    });
    render(<OjakgyoTab />);
    fill("사람1 이름", "김철수");
    fill("사람1 학교", "서울대학교");
    fill("사람2 이름", "이영희");
    fill("사람2 학교", "연세대학교");
    fireEvent.click(screen.getByRole("button", { name: "중매하기" }));
    await waitFor(() =>
      expect(screen.getByText("중매 완료!")).toBeInTheDocument(),
    );
    expect((screen.getByLabelText("사람1 이름") as HTMLInputElement).value).toBe("");
  });

  it("백엔드 에러 detail 표시", async () => {
    vi.spyOn(api, "postOjakgyo").mockRejectedValue(
      new ApiError(409, "이미 지목한 쌍입니다"),
    );
    render(<OjakgyoTab />);
    fill("사람1 이름", "김철수");
    fill("사람1 학교", "서울대학교");
    fill("사람2 이름", "이영희");
    fill("사람2 학교", "연세대학교");
    fireEvent.click(screen.getByRole("button", { name: "중매하기" }));
    await waitFor(() =>
      expect(screen.getByText("이미 지목한 쌍입니다")).toBeInTheDocument(),
    );
  });
});
