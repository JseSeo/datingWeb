import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Register from "./Register";
import * as api from "../../lib/api";

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => navigate };
});

beforeEach(() => vi.clearAllMocks());

function renderRegister() {
  render(<MemoryRouter><Register /></MemoryRouter>);
}

function fillFields() {
  fireEvent.change(screen.getByLabelText("이메일"), { target: { value: "a@b.com" } });
  fireEvent.change(screen.getByLabelText("비밀번호 (8자 이상)"), { target: { value: "password123" } });
  fireEvent.change(screen.getByLabelText("이름"), { target: { value: "김테스트" } });
  fireEvent.change(screen.getByLabelText("학교"), { target: { value: "서울대학교" } });
}

describe("Register 동의 게이트", () => {
  it("동의 전에는 가입 버튼 disabled", () => {
    renderRegister();
    expect(screen.getByRole("button", { name: "가입하기" })).toBeDisabled();
  });

  it("필수 3개 체크하면 버튼 활성", () => {
    renderRegister();
    fireEvent.click(screen.getByLabelText(/이용약관/));
    fireEvent.click(screen.getByLabelText(/개인정보처리방침/));
    fireEvent.click(screen.getByLabelText(/만 14세 이상/));
    expect(screen.getByRole("button", { name: "가입하기" })).toBeEnabled();
  });

  it("전체 동의 클릭하면 3개 일괄 체크", () => {
    renderRegister();
    fireEvent.click(screen.getByLabelText("전체 동의"));
    expect(screen.getByLabelText(/이용약관/)).toBeChecked();
    expect(screen.getByLabelText(/개인정보처리방침/)).toBeChecked();
    expect(screen.getByLabelText(/만 14세 이상/)).toBeChecked();
  });

  it("개별 하나 해제하면 전체 동의도 해제", () => {
    renderRegister();
    fireEvent.click(screen.getByLabelText("전체 동의"));
    fireEvent.click(screen.getByLabelText(/이용약관/));
    expect(screen.getByLabelText("전체 동의")).not.toBeChecked();
  });

  it("제출 시 동의 필드 포함해 registerUser 호출", async () => {
    const spy = vi.spyOn(api, "registerUser").mockResolvedValue({} as never);
    renderRegister();
    fillFields();
    fireEvent.click(screen.getByLabelText("전체 동의"));
    fireEvent.click(screen.getByRole("button", { name: "가입하기" }));
    await waitFor(() => expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        agreed_terms: true, agreed_privacy: true, agreed_age_14: true,
      }),
    ));
  });
});
