import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import Survey from "./Survey";
import { getSurvey, saveSurvey } from "../../lib/api";

// 성별에 따라 useAuth 반환값을 테스트별로 바꾸기 위한 mutable 상태.
// (vi.resetModules + 동적 import 대신 이 프로젝트의 기존 관례(Profile.test.tsx: 고정 vi.mock)를
// 따르되, 성별만 테스트 간 전환 가능하도록 mutable 변수로 감싼다.)
const authState: { gender: "male" | "female" } = { gender: "male" };

vi.mock("../../lib/api", () => ({
  getSurvey: vi.fn().mockResolvedValue({ answers: {}, updated_at: null }),
  saveSurvey: vi.fn().mockResolvedValue({ answers: { responses: {}, absolute: [] }, updated_at: "x" }),
}));
vi.mock("../../lib/auth", () => ({
  useAuth: () => ({ user: { gender: authState.gender }, loading: false }),
}));

describe("Survey page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authState.gender = "male";
  });

  it("마운트 시 기존 설문 로드", async () => {
    render(<Survey />);
    await waitFor(() => expect(getSurvey).toHaveBeenCalled());
  });

  it("남성이면 grooming_self(외모관리 습관) 노출", async () => {
    render(<Survey />);
    await waitFor(() =>
      expect(screen.getByText("외모관리 습관")).toBeInTheDocument());
  });

  it("저장 버튼 클릭 시 saveSurvey 호출", async () => {
    render(<Survey />);
    await waitFor(() => screen.getByText("외모관리 습관"));
    fireEvent.click(screen.getByRole("button", { name: /저장/ }));
    await waitFor(() => expect(saveSurvey).toHaveBeenCalled());
  });

  it("여성이면 grooming_self 미노출", async () => {
    authState.gender = "female";
    render(<Survey />);
    await waitFor(() => screen.getByText("내 키"));
    expect(screen.queryByText("외모관리 습관")).not.toBeInTheDocument();
  });
});
