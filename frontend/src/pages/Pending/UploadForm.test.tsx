import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import UploadForm from "./UploadForm";
import * as api from "../../lib/api";

beforeEach(() => {
  vi.clearAllMocks();
  URL.createObjectURL = vi.fn(() => "blob:mock");
});

function makeFile(type: string, size = 100): File {
  const file = new File(["x"], "id", { type });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

function selectFile(file: File) {
  fireEvent.change(screen.getByLabelText("학생증 파일"), { target: { files: [file] } });
}

const okVerif = {
  id: 1, user_id: 1, status: "pending" as const,
  reviewed_at: null, created_at: "2026-07-06",
};

describe("UploadForm", () => {
  it("잘못된 타입은 에러 + 제출 안 감", () => {
    const spy = vi.spyOn(api, "uploadVerification");
    render(<UploadForm onUploaded={() => {}} />);
    selectFile(makeFile("application/pdf"));
    expect(screen.getByText("JPG, PNG, WEBP 파일만 올릴 수 있어요")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "제출" }));
    expect(spy).not.toHaveBeenCalled();
  });

  it("10MB 초과 거부", () => {
    render(<UploadForm onUploaded={() => {}} />);
    selectFile(makeFile("image/jpeg", 11 * 1024 * 1024));
    expect(screen.getByText("파일 크기는 10MB 이하여야 해요")).toBeInTheDocument();
  });

  it("유효 파일 제출 → onUploaded 호출", async () => {
    const onUploaded = vi.fn();
    vi.spyOn(api, "uploadVerification").mockResolvedValue(okVerif);
    render(<UploadForm onUploaded={onUploaded} />);
    selectFile(makeFile("image/jpeg"));
    fireEvent.click(screen.getByRole("button", { name: "제출" }));
    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith(okVerif));
  });

  it("백엔드 에러 메시지 표시", async () => {
    vi.spyOn(api, "uploadVerification").mockRejectedValue(
      new api.ApiError(400, "파일 크기는 10MB 이하여야 합니다"),
    );
    render(<UploadForm onUploaded={() => {}} />);
    selectFile(makeFile("image/jpeg"));
    fireEvent.click(screen.getByRole("button", { name: "제출" }));
    await waitFor(() =>
      expect(screen.getByText("파일 크기는 10MB 이하여야 합니다")).toBeInTheDocument(),
    );
  });
});
