import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import UniversityWeightTab from "./UniversityWeightTab";
import * as api from "../../lib/api";

const SINGLE = {
  id: 1, university_a: "서울대학교", university_b: "",
  bonus: 30, active: true, note: "가을 이벤트",
};
const PAIR = {
  id: 2, university_a: "고려대학교", university_b: "연세대학교",
  bonus: -10, active: false, note: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  vi.spyOn(api, "listUniversities").mockResolvedValue([
    { id: 1, name: "서울대학교", active: true },
    { id: 2, name: "고려대학교", active: true },
  ]);
});

describe("UniversityWeightTab", () => {
  it("단일 규칙과 쌍 규칙을 구분해 보여준다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([SINGLE, PAIR]);
    render(<UniversityWeightTab />);
    expect(await screen.findByText("서울대학교", { selector: "div" })).toBeInTheDocument();
    expect(screen.getByText("고려대학교 × 연세대학교")).toBeInTheDocument();
    expect(screen.getByText("+30점")).toBeInTheDocument();
    expect(screen.getByText("-10점")).toBeInTheDocument();
  });

  it("끈 규칙은 중지로 표시된다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([PAIR]);
    render(<UniversityWeightTab />);
    expect(await screen.findByText("중지")).toBeInTheDocument();
  });

  it("규칙이 없으면 빈 상태 문구", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([]);
    render(<UniversityWeightTab />);
    expect(await screen.findByText("등록된 규칙 없음")).toBeInTheDocument();
  });

  it("추가하면 목록에 붙는다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([]);
    const create = vi.spyOn(api, "createUniversityWeight").mockResolvedValue(SINGLE);
    render(<UniversityWeightTab />);
    await screen.findByText("등록된 규칙 없음");

    fireEvent.change(await screen.findByRole("combobox", { name: "대학 A" }), { target: { value: "서울대학교" } });
    fireEvent.change(screen.getByLabelText(/보너스/), { target: { value: "30" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() => expect(create).toHaveBeenCalledWith({
      university_a: "서울대학교", university_b: "", bonus: 30,
      active: true, note: null,
    }));
    expect(await screen.findByText("서울대학교", { selector: "div" })).toBeInTheDocument();
  });

  it("대학명이 비면 요청하지 않고 에러를 띄운다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([]);
    const create = vi.spyOn(api, "createUniversityWeight");
    render(<UniversityWeightTab />);
    await screen.findByText("등록된 규칙 없음");

    fireEvent.change(screen.getByLabelText(/보너스/), { target: { value: "30" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    expect(await screen.findByText("대학명과 보너스를 확인하세요.")).toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });

  it("보너스가 비면 0으로 보내지 않고 에러를 띄운다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([]);
    const create = vi.spyOn(api, "createUniversityWeight");
    render(<UniversityWeightTab />);
    await screen.findByText("등록된 규칙 없음");

    fireEvent.change(await screen.findByRole("combobox", { name: "대학 A" }), { target: { value: "서울대학교" } });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    expect(await screen.findByText("대학명과 보너스를 확인하세요.")).toBeInTheDocument();
    expect(create).not.toHaveBeenCalled();
  });

  it("중지를 누르면 active를 반전해 저장한다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([SINGLE]);
    const update = vi.spyOn(api, "updateUniversityWeight")
      .mockResolvedValue({ ...SINGLE, active: false });
    render(<UniversityWeightTab />);
    fireEvent.click(await screen.findByRole("button", { name: "중지" }));

    await waitFor(() => expect(update).toHaveBeenCalledWith(1, {
      university_a: "서울대학교", university_b: "", bonus: 30,
      active: false, note: "가을 이벤트",
    }));
    expect(await screen.findByText("중지")).toBeInTheDocument();
  });

  it("삭제하면 목록에서 사라진다", async () => {
    vi.spyOn(api, "listUniversityWeights").mockResolvedValue([SINGLE]);
    const remove = vi.spyOn(api, "deleteUniversityWeight").mockResolvedValue(undefined);
    render(<UniversityWeightTab />);
    fireEvent.click(await screen.findByRole("button", { name: "삭제" }));

    await waitFor(() => expect(remove).toHaveBeenCalledWith(1));
    expect(await screen.findByText("등록된 규칙 없음")).toBeInTheDocument();
  });

  it("목록 조회가 실패하면 에러 문구", async () => {
    vi.spyOn(api, "listUniversityWeights").mockRejectedValue(new Error("boom"));
    render(<UniversityWeightTab />);
    expect(await screen.findByText("목록을 불러오지 못했어요.")).toBeInTheDocument();
  });
});
