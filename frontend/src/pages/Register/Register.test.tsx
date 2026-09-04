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

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(api, "listUniversities").mockResolvedValue([
    { id: 1, name: "서울대학교", active: true },
  ]);
});

function renderRegister() {
  render(<MemoryRouter><Register /></MemoryRouter>);
}

async function fillFields() {
  fireEvent.change(screen.getByLabelText("이메일"), { target: { value: "a@b.com" } });
  fireEvent.change(screen.getByLabelText("비밀번호 (8자 이상)"), { target: { value: "password123" } });
  fireEvent.change(screen.getByLabelText("이름"), { target: { value: "김테스트" } });
  const select = await screen.findByLabelText("학교");
  fireEvent.change(select, { target: { value: "서울대학교" } });
  fireEvent.click(screen.getByLabelText("남"));
}

describe("Register 동의 게이트", () => {
  it("동의 전에는 가입 버튼 disabled", async () => {
    renderRegister();
    await screen.findByRole("combobox", { name: "학교" });
    expect(screen.getByRole("button", { name: "가입하기" })).toBeDisabled();
  });

  it("필수 3개 체크하면 버튼 활성", async () => {
    renderRegister();
    await screen.findByRole("combobox", { name: "학교" });
    fireEvent.click(screen.getByLabelText(/이용약관/));
    fireEvent.click(screen.getByLabelText(/개인정보처리방침/));
    fireEvent.click(screen.getByLabelText(/만 14세 이상/));
    fireEvent.click(screen.getByLabelText("남"));
    expect(screen.getByRole("button", { name: "가입하기" })).toBeEnabled();
  });

  it("전체 동의 클릭하면 3개 일괄 체크", async () => {
    renderRegister();
    await screen.findByRole("combobox", { name: "학교" });
    fireEvent.click(screen.getByLabelText("전체 동의"));
    expect(screen.getByLabelText(/이용약관/)).toBeChecked();
    expect(screen.getByLabelText(/개인정보처리방침/)).toBeChecked();
    expect(screen.getByLabelText(/만 14세 이상/)).toBeChecked();
  });

  it("개별 하나 해제하면 전체 동의도 해제", async () => {
    renderRegister();
    await screen.findByRole("combobox", { name: "학교" });
    fireEvent.click(screen.getByLabelText("전체 동의"));
    fireEvent.click(screen.getByLabelText(/이용약관/));
    expect(screen.getByLabelText("전체 동의")).not.toBeChecked();
  });

  it("제출 시 동의 필드 포함해 registerUser 호출", async () => {
    const spy = vi.spyOn(api, "registerUser").mockResolvedValue({} as never);
    renderRegister();
    await fillFields();
    fireEvent.click(screen.getByLabelText("전체 동의"));
    fireEvent.click(screen.getByRole("button", { name: "가입하기" }));
    await waitFor(() => expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        agreed_terms: true, agreed_privacy: true, agreed_age_14: true, gender: "male",
      }),
    ));
  });

  it("이메일이 비면 제출을 막고 커스텀 에러를 보여준다 (noValidate 경로 검증)", async () => {
    const spy = vi.spyOn(api, "registerUser").mockResolvedValue({} as never);
    renderRegister();
    await screen.findByRole("combobox", { name: "학교" });
    fireEvent.click(screen.getByLabelText("전체 동의"));
    fireEvent.click(screen.getByLabelText("남"));
    fireEvent.click(screen.getByRole("button", { name: "가입하기" }));
    expect(await screen.findByText("올바른 이메일을 입력하세요")).toBeInTheDocument();
    expect(spy).not.toHaveBeenCalled();
  });
});

describe("Register 학교", () => {
  it("목록에서 학교를 고른다", async () => {
    renderRegister();
    const select = await screen.findByRole("combobox", { name: "학교" });
    fireEvent.change(select, { target: { value: "서울대학교" } });
    expect((select as HTMLSelectElement).value).toBe("서울대학교");
  });
});

describe("Register 성별", () => {
  it("성별 라디오가 렌더된다", async () => {
    renderRegister();
    await screen.findByRole("combobox", { name: "학교" });
    expect(screen.getByLabelText("남")).toBeInTheDocument();
    expect(screen.getByLabelText("여")).toBeInTheDocument();
  });

  it("성별 미선택이면 제출 불가", async () => {
    renderRegister();
    fireEvent.change(screen.getByLabelText("이메일"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("비밀번호 (8자 이상)"), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText("이름"), { target: { value: "홍길동" } });
    const select = await screen.findByRole("combobox", { name: "학교" });
    fireEvent.change(select, { target: { value: "서울대학교" } });
    fireEvent.click(screen.getByLabelText("전체 동의"));
    expect(screen.getByRole("button", { name: "가입하기" })).toBeDisabled();
  });
});
