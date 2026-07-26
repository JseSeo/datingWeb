import { describe, it, expect } from "vitest";
import { QUESTIONS } from "./questions";

describe("questions catalog", () => {
  it("총 45문항", () => {
    expect(QUESTIONS.length).toBe(45);
  });
  it("id 중복 없음", () => {
    const ids = QUESTIONS.map((q) => q.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
  it("single/multi 문항은 choices 보유", () => {
    for (const q of QUESTIONS) {
      if (q.type === "single" || q.type === "multi") {
        expect(q.choices && q.choices.length > 0).toBe(true);
      }
    }
  });
  it("ranking 문항은 rankItems 보유", () => {
    for (const q of QUESTIONS.filter((q) => q.type === "ranking")) {
      expect(q.rankItems && q.rankItems.length > 0).toBe(true);
    }
  });
  it("noPrefId는 partner 문항에만 존재", () => {
    for (const q of QUESTIONS) {
      if (q.noPrefId) expect(q.section).toBe("partner");
    }
  });
  it("noPrefId가 있으면 해당 id가 choices에 존재(비-face)", () => {
    for (const q of QUESTIONS) {
      if (q.noPrefId && !q.face) {
        expect(q.choices?.some((c) => c.id === q.noPrefId)).toBe(true);
      }
    }
  });
  it("grooming_self만 maleOnly", () => {
    const maleOnly = QUESTIONS.filter((q) => q.maleOnly).map((q) => q.id);
    expect(maleOnly).toEqual(["grooming_self"]);
  });
});
