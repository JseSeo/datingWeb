import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import RoundTab from "./RoundTab";
import * as api from "../../lib/api";
import { ApiError } from "../../lib/api";
import type { AdminMatchRoundOut } from "../../lib/types";

const pending: AdminMatchRoundOut = {
  id: 1,
  scheduled_at: "2026-08-20T12:00:00",  // KST 21:00
  status: "pending",
};

const done: AdminMatchRoundOut = {
  id: 2,
  scheduled_at: "2026-08-06T12:00:00",
  status: "done",
};

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.restoreAllMocks());

describe("RoundTab", () => {
  it("목록을 KST로 표시하고 상태 배지를 붙인다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending, done]);
    render(<RoundTab />);
    await waitFor(() =>
      expect(screen.getByText("2026-08-20 21:00")).toBeInTheDocument(),
    );
    expect(screen.getByText("2026-08-06 21:00")).toBeInTheDocument();
    expect(screen.getByText("예정")).toBeInTheDocument();
    expect(screen.getByText("완료")).toBeInTheDocument();
  });

  it("done 라운드에는 수정·삭제 버튼이 없다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending, done]);
    render(<RoundTab />);
    await waitFor(() => screen.getByText("2026-08-06 21:00"));
    // pending 한 건에 대해서만 버튼이 있다
    expect(screen.getAllByRole("button", { name: "수정" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "삭제" })).toHaveLength(1);
  });

  it("생성 — KST 입력을 UTC ISO로 바꿔 보내고 목록에 반영", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([]);
    const created: AdminMatchRoundOut = {
      id: 3,
      scheduled_at: "2026-09-01T12:00:00",
      status: "pending",
    };
    const spy = vi.spyOn(api, "createMatchRound").mockResolvedValue(created);
    render(<RoundTab />);
    await waitFor(() => screen.getByText("예정된 라운드 없음"));

    fireEvent.change(screen.getByLabelText("매칭 예정 일시"), {
      target: { value: "2026-09-01T21:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() =>
      expect(screen.getByText("2026-09-01 21:00")).toBeInTheDocument(),
    );
    expect(spy).toHaveBeenCalledWith("2026-09-01T12:00:00.000Z");
  });

  it("생성 실패 시 서버 문구를 그대로 표시하고 목록은 그대로", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending]);
    vi.spyOn(api, "createMatchRound").mockRejectedValue(
      new ApiError(409, "같은 시각의 라운드가 이미 있습니다"),
    );
    render(<RoundTab />);
    await waitFor(() => screen.getByText("2026-08-20 21:00"));

    fireEvent.change(screen.getByLabelText("매칭 예정 일시"), {
      target: { value: "2026-09-01T21:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() =>
      expect(
        screen.getByText("같은 시각의 라운드가 이미 있습니다"),
      ).toBeInTheDocument(),
    );
    // 기존 라운드는 그대로 남아있고 (낙관적 갱신 없음), 실패한 생성 요청이
    // 목록에 유령 카드를 추가하지 않았다 — 개수로 못을 박는다.
    expect(screen.getByText("2026-08-20 21:00")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "수정" })).toHaveLength(1);
  });

  it("빈 입력으로 추가하면 요청을 보내지 않는다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([]);
    const spy = vi.spyOn(api, "createMatchRound");
    render(<RoundTab />);
    await waitFor(() => screen.getByText("예정된 라운드 없음"));

    fireEvent.click(screen.getByRole("button", { name: "추가" }));

    await waitFor(() =>
      expect(screen.getByText("올바른 일시를 입력하세요.")).toBeInTheDocument(),
    );
    expect(spy).not.toHaveBeenCalled();
  });

  it("수정 — 기존 값이 입력칸에 채워지고 저장하면 목록이 갱신된다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending]);
    const spy = vi.spyOn(api, "updateMatchRound").mockResolvedValue({
      ...pending,
      scheduled_at: "2026-08-13T12:00:00",
    });
    render(<RoundTab />);
    await waitFor(() => screen.getByText("2026-08-20 21:00"));

    fireEvent.click(screen.getByRole("button", { name: "수정" }));
    const input = screen.getByLabelText("매칭 예정 일시 수정");
    expect(input).toHaveValue("2026-08-20T21:00");

    fireEvent.change(input, { target: { value: "2026-08-13T21:00" } });
    fireEvent.click(screen.getByRole("button", { name: "저장" }));

    await waitFor(() =>
      expect(screen.getByText("2026-08-13 21:00")).toBeInTheDocument(),
    );
    expect(spy).toHaveBeenCalledWith(1, "2026-08-13T12:00:00.000Z");
  });

  it("수정 취소 — 값이 원래대로 남고 요청도 없다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending]);
    const spy = vi.spyOn(api, "updateMatchRound");
    render(<RoundTab />);
    await waitFor(() => screen.getByText("2026-08-20 21:00"));

    fireEvent.click(screen.getByRole("button", { name: "수정" }));
    fireEvent.change(screen.getByLabelText("매칭 예정 일시 수정"), {
      target: { value: "2026-08-13T21:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "취소" }));

    await waitFor(() =>
      expect(screen.getByText("2026-08-20 21:00")).toBeInTheDocument(),
    );
    expect(spy).not.toHaveBeenCalled();
  });

  it("삭제 — confirm 승인 시 목록에서 제거", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending]);
    const spy = vi.spyOn(api, "deleteMatchRound").mockResolvedValue(undefined);
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<RoundTab />);
    await waitFor(() => screen.getByText("2026-08-20 21:00"));

    fireEvent.click(screen.getByRole("button", { name: "삭제" }));

    await waitFor(() =>
      expect(screen.queryByText("2026-08-20 21:00")).toBeNull(),
    );
    expect(spy).toHaveBeenCalledWith(1);
  });

  it("삭제 — confirm 취소 시 아무 일도 없다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([pending]);
    const spy = vi.spyOn(api, "deleteMatchRound");
    vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<RoundTab />);
    await waitFor(() => screen.getByText("2026-08-20 21:00"));

    fireEvent.click(screen.getByRole("button", { name: "삭제" }));

    expect(spy).not.toHaveBeenCalled();
    expect(screen.getByText("2026-08-20 21:00")).toBeInTheDocument();
  });

  it("로드 실패 시 에러 문구", async () => {
    vi.spyOn(api, "listMatchRounds").mockRejectedValue(new Error("fail"));
    render(<RoundTab />);
    await waitFor(() =>
      expect(screen.getByText("목록을 불러오지 못했어요.")).toBeInTheDocument(),
    );
  });

  it("로드 실패 시 목록이 비어있다는 문구는 뜨지 않는다", async () => {
    vi.spyOn(api, "listMatchRounds").mockRejectedValue(new Error("fail"));
    render(<RoundTab />);
    await waitFor(() =>
      expect(screen.getByText("목록을 불러오지 못했어요.")).toBeInTheDocument(),
    );
    expect(screen.queryByText("예정된 라운드 없음")).toBeNull();
  });
});

describe("매칭 실행", () => {
  it("pending 라운드에 실행 버튼이 있고, 누르면 결과 요약이 보인다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([
      { id: 1, scheduled_at: "2026-09-01T10:00:00", status: "pending" },
    ]);
    vi.spyOn(api, "runMatchRound").mockResolvedValue({
      matched: 12, unmatched: 3, guaranteed: 2,
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<RoundTab />);
    const button = await screen.findByRole("button", { name: "매칭 실행" });
    fireEvent.click(button);

    expect(await screen.findByText(/12쌍/)).toBeInTheDocument();
    expect(screen.getByText(/미매칭 3명/)).toBeInTheDocument();
    expect(api.runMatchRound).toHaveBeenCalledWith(1);
  });

  it("확인 창에서 취소하면 실행하지 않는다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([
      { id: 1, scheduled_at: "2026-09-01T10:00:00", status: "pending" },
    ]);
    const spy = vi.spyOn(api, "runMatchRound");
    vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<RoundTab />);
    fireEvent.click(await screen.findByRole("button", { name: "매칭 실행" }));

    expect(spy).not.toHaveBeenCalled();
  });

  it("done 라운드에는 실행 버튼이 없다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([
      { id: 1, scheduled_at: "2026-09-01T10:00:00", status: "done" },
    ]);

    render(<RoundTab />);
    expect(await screen.findByText("완료")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "매칭 실행" })).toBeNull();
  });

  it("실행 요청이 도는 동안 수정·삭제 버튼이 잠긴다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([
      { id: 1, scheduled_at: "2026-09-01T10:00:00", status: "pending" },
    ]);
    // 요청이 끝나지 않은 상태를 만든다 — 그동안 로컬 status는 아직 "pending"이다
    vi.spyOn(api, "runMatchRound").mockReturnValue(new Promise(() => {}));
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<RoundTab />);
    fireEvent.click(await screen.findByRole("button", { name: "매칭 실행" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "실행 중…" })).toBeDisabled(),
    );
    expect(screen.getByRole("button", { name: "수정" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "삭제" })).toBeDisabled();
  });

  it("실행 실패 메시지를 보여준다", async () => {
    vi.spyOn(api, "listMatchRounds").mockResolvedValue([
      { id: 1, scheduled_at: "2026-09-01T10:00:00", status: "pending" },
    ]);
    vi.spyOn(api, "runMatchRound").mockRejectedValue(
      new ApiError(409, "이미 실행 중이거나 완료된 라운드입니다"),
    );
    vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<RoundTab />);
    fireEvent.click(await screen.findByRole("button", { name: "매칭 실행" }));

    expect(
      await screen.findByText("이미 실행 중이거나 완료된 라운드입니다"),
    ).toBeInTheDocument();
  });
});
