import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Home from "./Home";
import * as api from "../../lib/api";

const user = {
  id: 1, email: "a@b.com", name: "김홈", university: "서울대학교",
  gender: "male" as const, status: "active" as const, profile_photo: null,
  bio: null, instagram: null, kakao_id: null, phone: null,
  matching_paused: false, is_admin: false, created_at: "2026-01-01",
};

let currentUser = { ...user };
vi.mock("../../lib/auth", () => ({
  useAuth: () => ({ user: currentUser, logout: vi.fn(), refreshUser: vi.fn() }),
}));

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => navigate };
});

const SURVEY_DONE = { answers: { responses: {}, absolute: [] }, updated_at: "2026-08-01T00:00:00" };
const SURVEY_EMPTY = { answers: {}, updated_at: null };

beforeEach(() => {
  vi.clearAllMocks();
  currentUser = { ...user };
  // Home은 daysUntilKST를 now 없이 호출하므로 시계를 고정해야 D-3이 확정된다.
  // shouldAdvanceTime이 없으면 findBy*의 대기 타이머가 멈춰 타임아웃 난다.
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date("2026-08-11T12:00:00Z"));
});

afterEach(() => vi.useRealTimers());

function renderHome() {
  render(<MemoryRouter><Home /></MemoryRouter>);
}

describe("Home", () => {
  it("라운드가 있으면 D-day와 예정 일시 표시", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue({
      id: 1, scheduled_at: "2026-08-14T12:00:00",
    });
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    renderHome();
    expect(await screen.findByText("D-3")).toBeInTheDocument();
    expect(screen.getByText("2026-08-14 21:00")).toBeInTheDocument();
  });

  it("라운드가 없으면 빈 상태 문구", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue(null);
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    renderHome();
    expect(await screen.findByText("아직 예정된 매칭이 없어요")).toBeInTheDocument();
  });

  it("설문 미완이면 경고와 설문 이동 버튼", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue(null);
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_EMPTY);
    renderHome();
    const button = await screen.findByRole("button", { name: /설문 하러가기/ });
    fireEvent.click(button);
    expect(navigate).toHaveBeenCalledWith("/survey");
  });

  it("일시정지면 경고와 마이페이지 이동 버튼", async () => {
    currentUser = { ...user, matching_paused: true };
    vi.spyOn(api, "getNextRound").mockResolvedValue(null);
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    renderHome();
    const button = await screen.findByRole("button", { name: /해제/ });
    fireEvent.click(button);
    expect(navigate).toHaveBeenCalledWith("/mypage");
  });

  it("설문 완료 + 일시정지 아님이면 참여 중 표시", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue(null);
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_DONE);
    renderHome();
    expect(await screen.findByText(/매칭 참여 중/)).toBeInTheDocument();
  });

  it("일시정지 + 설문 미완이면 두 안내가 함께 뜨고 참여 중은 안 뜸", async () => {
    currentUser = { ...user, matching_paused: true };
    vi.spyOn(api, "getNextRound").mockResolvedValue(null);
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_EMPTY);
    renderHome();
    expect(await screen.findByText("⚠ 설문을 아직 안 했어요")).toBeInTheDocument();
    expect(screen.getByText("⏸ 매칭 일시정지 중")).toBeInTheDocument();
    expect(screen.queryByText(/매칭 참여 중/)).toBeNull();
  });

  it("라운드 조회만 실패해도 설문 안내는 표시", async () => {
    vi.spyOn(api, "getNextRound").mockRejectedValue(new api.ApiError(500, "서버 오류"));
    vi.spyOn(api, "getSurvey").mockResolvedValue(SURVEY_EMPTY);
    renderHome();
    expect(await screen.findByText("일정을 불러오지 못했어요")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /설문 하러가기/ })).toBeInTheDocument();
  });

  it("설문 조회만 실패하면 설문 경고를 띄우지 않음", async () => {
    vi.spyOn(api, "getNextRound").mockResolvedValue(null);
    vi.spyOn(api, "getSurvey").mockRejectedValue(new api.ApiError(500, "서버 오류"));
    renderHome();
    await waitFor(() =>
      expect(screen.getByText("아직 예정된 매칭이 없어요")).toBeInTheDocument(),
    );
    expect(screen.queryByRole("button", { name: /설문 하러가기/ })).toBeNull();
    expect(screen.queryByText(/매칭 참여 중/)).toBeNull();
  });
});
