import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QuestionField } from "./QuestionField";
import type { FaceChoice, Question } from "./types";

const FACE_TYPES: FaceChoice[] = [
  { id: "type_a", label: "강아지상", image: "/faces/placeholder-a.png" },
  { id: "type_b", label: "고양이상", image: "/faces/placeholder-b.png" },
  { id: "type_c", label: "곰상", image: "/faces/placeholder-c.png" },
  { id: "type_d", label: "여우상", image: "/faces/placeholder-d.png" },
];
const FACE_ANY_ID = "any";

const single: Question = {
  id: "q_single", section: "self", label: "단일", type: "single",
  choices: [{ id: "a", label: "A" }, { id: "b", label: "B" }],
};
const multi: Question = {
  id: "q_multi", section: "self", label: "복수", type: "multi",
  choices: [{ id: "a", label: "A" }, { id: "b", label: "B" }],
};
const number: Question = {
  id: "q_number", section: "self", label: "숫자", type: "number", unit: "cm",
  min: 120, max: 220,
};
const ranking: Question = {
  id: "q_ranking", section: "self", label: "순위", type: "ranking",
  rank_items: [{ id: "a", label: "A" }, { id: "b", label: "B" }, { id: "c", label: "C" }],
};
const imageSingle: Question = {
  id: "q_image_single", section: "self", label: "얼굴상", type: "image-single", face: true,
};
const imageMulti: Question = {
  id: "q_image_multi", section: "partner", label: "선호 얼굴상", type: "image-multi", face: true,
};

describe("QuestionField", () => {
  it("single: 선택 시 choiceId onChange", () => {
    const onChange = vi.fn();
    render(
      <QuestionField
        question={single}
        value={undefined}
        onChange={onChange}
        faceTypes={FACE_TYPES}
        faceAnyId={FACE_ANY_ID}
      />,
    );
    fireEvent.click(screen.getByLabelText("A"));
    expect(onChange).toHaveBeenCalledWith("a");
  });

  it("multi: 복수 선택 가능 안내문 표시 + 배열 갱신", () => {
    const onChange = vi.fn();
    render(
      <QuestionField
        question={multi}
        value={["a"]}
        onChange={onChange}
        faceTypes={FACE_TYPES}
        faceAnyId={FACE_ANY_ID}
      />,
    );
    expect(screen.getByText("복수 선택 가능")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("B"));
    expect(onChange).toHaveBeenCalledWith(["a", "b"]);
  });

  it("scale: 1~5 + 양끝 라벨", () => {
    const onChange = vi.fn();
    const scale: Question = {
      id: "q_scale", section: "self", label: "척도", type: "scale",
      scale_labels: ["낮음", "높음"],
    };
    render(
      <QuestionField
        question={scale}
        value={undefined}
        onChange={onChange}
        faceTypes={FACE_TYPES}
        faceAnyId={FACE_ANY_ID}
      />,
    );
    expect(screen.getByText("낮음")).toBeInTheDocument();
    expect(screen.getByText("높음")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "3" }));
    expect(onChange).toHaveBeenCalledWith(3);
  });

  it("number: 입력값 숫자로 onChange + 단위 표시", () => {
    const onChange = vi.fn();
    render(
      <QuestionField
        question={number}
        value={undefined}
        onChange={onChange}
        faceTypes={FACE_TYPES}
        faceAnyId={FACE_ANY_ID}
      />,
    );
    expect(screen.getByText("cm")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("spinbutton"), { target: { value: "172" } });
    expect(onChange).toHaveBeenCalledWith(172);
  });

  it("number: 빈 입력은 onChange 안 함", () => {
    const onChange = vi.fn();
    render(
      <QuestionField
        question={number}
        value={172}
        onChange={onChange}
        faceTypes={FACE_TYPES}
        faceAnyId={FACE_ANY_ID}
      />,
    );
    fireEvent.change(screen.getByRole("spinbutton"), { target: { value: "" } });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("ranking: 미응답 시 rankItems 순서로 표시 + ▼ 클릭 시 자리 교환", () => {
    const onChange = vi.fn();
    render(
      <QuestionField
        question={ranking}
        value={undefined}
        onChange={onChange}
        faceTypes={FACE_TYPES}
        faceAnyId={FACE_ANY_ID}
      />,
    );
    expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "A▲▼", "B▲▼", "C▲▼",
    ]);
    fireEvent.click(screen.getByRole("button", { name: "A 아래로" }));
    expect(onChange).toHaveBeenCalledWith(["b", "a", "c"]);
  });

  it("ranking: 첫 항목 ▲ / 끝 항목 ▼ 는 무시", () => {
    const onChange = vi.fn();
    render(
      <QuestionField
        question={ranking}
        value={["a", "b", "c"]}
        onChange={onChange}
        faceTypes={FACE_TYPES}
        faceAnyId={FACE_ANY_ID}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "A 위로" }));
    fireEvent.click(screen.getByRole("button", { name: "C 아래로" }));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("image-single: 얼굴상 목록만 표시 + 선택 시 faceId onChange", () => {
    const onChange = vi.fn();
    render(
      <QuestionField
        question={imageSingle}
        value={undefined}
        onChange={onChange}
        faceTypes={FACE_TYPES}
        faceAnyId={FACE_ANY_ID}
      />,
    );
    expect(screen.getAllByRole("radio")).toHaveLength(FACE_TYPES.length);
    expect(screen.queryByRole("radio", { name: "상관없음" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: FACE_TYPES[1].label }));
    expect(onChange).toHaveBeenCalledWith(FACE_TYPES[1].id);
  });

  it("image-multi: 상관없음 옵션 추가 + 복수 선택 안내문 + 배열 토글", () => {
    const onChange = vi.fn();
    render(
      <QuestionField
        question={imageMulti}
        value={[FACE_TYPES[0].id]}
        onChange={onChange}
        faceTypes={FACE_TYPES}
        faceAnyId={FACE_ANY_ID}
      />,
    );
    expect(screen.getByText("복수 선택 가능")).toBeInTheDocument();
    expect(screen.getAllByRole("checkbox")).toHaveLength(FACE_TYPES.length + 1);
    fireEvent.click(screen.getByRole("checkbox", { name: "상관없음" }));
    expect(onChange).toHaveBeenCalledWith([FACE_TYPES[0].id, FACE_ANY_ID]);
  });

  it("image-multi: 이미 선택된 항목 다시 클릭 시 해제", () => {
    const onChange = vi.fn();
    render(
      <QuestionField
        question={imageMulti}
        value={[FACE_TYPES[0].id]}
        onChange={onChange}
        faceTypes={FACE_TYPES}
        faceAnyId={FACE_ANY_ID}
      />,
    );
    fireEvent.click(screen.getByRole("checkbox", { name: FACE_TYPES[0].label }));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("number: 카탈로그의 min/max를 input에 그대로 건다", () => {
    // 서버가 범위 밖 값을 조용히 버리므로, 입력 단계에서 막아야 유저가
    // "저장했는데 값이 없다"를 겪지 않는다
    render(
      <QuestionField
        question={number}
        value={undefined}
        onChange={vi.fn()}
        faceTypes={FACE_TYPES}
        faceAnyId={FACE_ANY_ID}
      />,
    );
    const input = screen.getByRole("spinbutton");
    expect(input).toHaveAttribute("min", "120");
    expect(input).toHaveAttribute("max", "220");
  });
});
