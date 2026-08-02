import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Report from "./Report";
import * as api from "../../lib/api";

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => navigate };
});

beforeEach(() => vi.clearAllMocks());

const HINT = /대상을 특정할 수 있는 정보/;

describe("Report", () => {
  it("초기 상태: 유형 미선택이면 제출 버튼 비활성", () => {
    render(<Report />);
    expect(screen.getByRole("button", { name: "제출" })).toBeDisabled();
  });

  it("뒤로 버튼 클릭 시 /mypage 이동", () => {
    render(<Report />);
    fireEvent.click(screen.getByRole("button", { name: "마이페이지로 돌아가기" }));
    expect(navigate).toHaveBeenCalledWith("/mypage");
  });

  it("신고 선택 시 대상 입력칸 + 안내문 노출", () => {
    render(<Report />);
    fireEvent.click(screen.getByLabelText("신고"));
    expect(screen.getByLabelText("신고 대상 이름")).toBeInTheDocument();
    expect(screen.getByLabelText("신고 대상 학교")).toBeInTheDocument();
    expect(screen.getByText(HINT)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "제출" })).toBeEnabled();
  });

  it("건의 선택 시 대상 입력칸 사라짐", () => {
    render(<Report />);
    fireEvent.click(screen.getByLabelText("신고"));
    fireEvent.click(screen.getByLabelText("건의"));
    expect(screen.queryByLabelText("신고 대상 이름")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("신고 대상 학교")).not.toBeInTheDocument();
    expect(screen.queryByText(HINT)).not.toBeInTheDocument();
  });

  it("신고 제출 성공: strip된 값 전송 + 완료 문구 + 폼 초기화", async () => {
    const spy = vi.spyOn(api, "submitReport").mockResolvedValue({
      id: 1, type: "report", target_name: "대상자",
      target_university: "연세대학교", reason: "사유",
      created_at: "2026-08-02T00:00:00",
    });
    render(<Report />);
    fireEvent.click(screen.getByLabelText("신고"));
    fireEvent.change(screen.getByLabelText("신고 대상 이름"), {
      target: { value: "  대상자  " },
    });
    fireEvent.change(screen.getByLabelText("신고 대상 학교"), {
      target: { value: "  연세대학교  " },
    });
    fireEvent.change(screen.getByLabelText("내용"), { target: { value: "사유" } });
    fireEvent.click(screen.getByRole("button", { name: "제출" }));

    await waitFor(() =>
      expect(screen.getByText("접수되었습니다")).toBeInTheDocument(),
    );
    expect(spy).toHaveBeenCalledWith({
      type: "report",
      target_name: "대상자",
      target_university: "연세대학교",
      reason: "사유",
    });
    expect(screen.getByLabelText("내용")).toHaveValue("");
    expect(screen.getByRole("button", { name: "제출" })).toBeDisabled();
  });

  it("건의 제출: 대상 필드는 null로 전송", async () => {
    const spy = vi.spyOn(api, "submitReport").mockResolvedValue({
      id: 2, type: "suggestion", target_name: null,
      target_university: null, reason: "건의합니다",
      created_at: "2026-08-02T00:00:00",
    });
    render(<Report />);
    fireEvent.click(screen.getByLabelText("건의"));
    fireEvent.change(screen.getByLabelText("내용"), {
      target: { value: "건의합니다" },
    });
    fireEvent.click(screen.getByRole("button", { name: "제출" }));

    await waitFor(() => expect(spy).toHaveBeenCalledWith({
      type: "suggestion",
      target_name: null,
      target_university: null,
      reason: "건의합니다",
    }));
  });

  it("서버 400이면 백엔드 문구를 그대로 표시", async () => {
    vi.spyOn(api, "submitReport").mockRejectedValue(
      new api.ApiError(400, "신고 대상의 이름과 학교를 입력하세요"),
    );
    render(<Report />);
    fireEvent.click(screen.getByLabelText("신고"));
    fireEvent.change(screen.getByLabelText("내용"), { target: { value: "사유" } });
    fireEvent.click(screen.getByRole("button", { name: "제출" }));

    await waitFor(() =>
      expect(
        screen.getByText("신고 대상의 이름과 학교를 입력하세요"),
      ).toBeInTheDocument(),
    );
  });
});
