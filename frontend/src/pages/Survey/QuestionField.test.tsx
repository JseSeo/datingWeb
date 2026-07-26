import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QuestionField } from "./QuestionField";
import type { Question } from "./types";

const single: Question = {
  id: "q_single", section: "self", label: "단일", type: "single",
  choices: [{ id: "a", label: "A" }, { id: "b", label: "B" }],
};
const multi: Question = {
  id: "q_multi", section: "self", label: "복수", type: "multi",
  choices: [{ id: "a", label: "A" }, { id: "b", label: "B" }],
};

describe("QuestionField", () => {
  it("single: 선택 시 choiceId onChange", () => {
    const onChange = vi.fn();
    render(<QuestionField question={single} value={undefined} onChange={onChange} />);
    fireEvent.click(screen.getByLabelText("A"));
    expect(onChange).toHaveBeenCalledWith("a");
  });

  it("multi: 복수 선택 가능 안내문 표시 + 배열 갱신", () => {
    const onChange = vi.fn();
    render(<QuestionField question={multi} value={["a"]} onChange={onChange} />);
    expect(screen.getByText("복수 선택 가능")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("B"));
    expect(onChange).toHaveBeenCalledWith(["a", "b"]);
  });

  it("scale: 1~5 + 양끝 라벨", () => {
    const onChange = vi.fn();
    const scale: Question = {
      id: "q_scale", section: "self", label: "척도", type: "scale",
      scaleLabels: ["낮음", "높음"],
    };
    render(<QuestionField question={scale} value={undefined} onChange={onChange} />);
    expect(screen.getByText("낮음")).toBeInTheDocument();
    expect(screen.getByText("높음")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "3" }));
    expect(onChange).toHaveBeenCalledWith(3);
  });
});
