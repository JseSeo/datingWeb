import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { UniversitySelect } from "./UniversitySelect";
import * as api from "../../lib/api";

describe("UniversitySelect", () => {
  beforeEach(() => {
    vi.spyOn(api, "listUniversities").mockResolvedValue([
      { id: 1, name: "서울대학교", active: true },
      { id: 2, name: "연세대학교", active: true },
    ]);
  });

  it("목록을 받아 옵션으로 그린다", async () => {
    render(<UniversitySelect id="u" label="학교" value="" onChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByRole("option", { name: "서울대학교" })).toBeInTheDocument();
    });
  });

  it("목록이 비면 안내를 띄운다", async () => {
    vi.spyOn(api, "listUniversities").mockResolvedValue([]);
    render(<UniversitySelect id="u" label="학교" value="" onChange={() => {}} />);
    await waitFor(() => {
      expect(screen.getByText(/등록된 대학이 없습니다/)).toBeInTheDocument();
    });
  });

  it("allowEmpty면 '없음' 옵션이 있다", async () => {
    render(
      <UniversitySelect id="u" label="학교" value="" onChange={() => {}} allowEmpty emptyLabel="없음" />
    );
    await waitFor(() => {
      const option = screen.getByRole("option", { name: "없음" }) as HTMLOptionElement;
      expect(option).toBeInTheDocument();
      expect(option.value).toBe("");
    });
  });
});
