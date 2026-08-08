import { describe, it, expect } from "vitest";
import { formatKST } from "./datetime";

describe("formatKST", () => {
  it("타임존 표시 없는 UTC 문자열을 KST로 변환 (날짜 넘어감)", () => {
    expect(formatKST("2026-08-03T17:01:59.776396")).toBe("2026-08-04 02:01");
  });

  it("이미 Z가 붙은 입력도 같은 결과 (Z 중복 안 붙음)", () => {
    expect(formatKST("2026-08-03T17:01:59Z")).toBe("2026-08-04 02:01");
  });

  it("offset이 붙은 입력은 그 offset을 존중 (이중 변환 안 함)", () => {
    expect(formatKST("2026-08-03T17:01:59+09:00")).toBe("2026-08-03 17:01");
  });

  it("자정 경계에서 24시가 아니라 00시로 출력", () => {
    expect(formatKST("2026-08-03T15:00:00")).toBe("2026-08-04 00:00");
  });

  it("파싱 불가한 입력은 원문 그대로 반환", () => {
    expect(formatKST("어제")).toBe("어제");
  });
});
