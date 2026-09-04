import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import UniversityTab from "./UniversityTab";
import * as api from "../../lib/api";

describe("UniversityTab", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "listAllUniversities").mockResolvedValue([
      { id: 1, name: "서울대학교", active: true },
      { id: 2, name: "꺼진대학교", active: false },
    ]);
  });

  it("비활성 대학도 목록에 보인다", async () => {
    render(<UniversityTab />);
    expect(await screen.findByText("꺼진대학교")).toBeInTheDocument();
  });

  it("대학을 추가한다", async () => {
    const create = vi.spyOn(api, "createUniversity").mockResolvedValue({
      id: 3, name: "한양대학교", active: true,
    });
    render(<UniversityTab />);
    fireEvent.change(await screen.findByLabelText("대학명"), {
      target: { value: "한양대학교" },
    });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith("한양대학교"));
  });

  it("사용 중인 대학 삭제는 안내를 띄운다", async () => {
    vi.spyOn(api, "deleteUniversity").mockRejectedValue(
      new api.ApiError(409, "이미 사용 중인 대학입니다. 삭제 대신 비활성으로 끄세요")
    );
    render(<UniversityTab />);
    const rows = await screen.findAllByRole("button", { name: "삭제" });
    fireEvent.click(rows[0]);
    expect(await screen.findByText(/삭제 대신 비활성/)).toBeInTheDocument();
  });
});
