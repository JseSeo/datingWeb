import { describe, it, expect } from "vitest";
import { FACE_TYPES, FACE_ANY_ID } from "./faceTypes";

describe("faceTypes placeholder", () => {
  it("최소 2개 이상 얼굴상 + 각 항목 id/label/image 보유", () => {
    expect(FACE_TYPES.length).toBeGreaterThanOrEqual(2);
    for (const f of FACE_TYPES) {
      expect(f.id).toBeTruthy();
      expect(f.label).toBeTruthy();
      expect(f.image).toBeTruthy();
    }
  });
  it("상관없음 id가 얼굴상 목록과 겹치지 않는다", () => {
    expect(FACE_TYPES.some((f) => f.id === FACE_ANY_ID)).toBe(false);
  });
});
