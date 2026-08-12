import { describe, it, expect } from "vitest";
import { formatKST, daysUntilKST, kstInputToUtcISO, utcISOToKstInput } from "./datetime";

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

describe("daysUntilKST", () => {
  it("3일 뒤면 3", () => {
    expect(
      daysUntilKST("2026-08-14T12:00:00", new Date("2026-08-11T12:00:00Z")),
    ).toBe(3);
  });

  it("같은 KST 날짜면 0", () => {
    expect(
      daysUntilKST("2026-08-11T12:00:00", new Date("2026-08-11T00:00:00Z")),
    ).toBe(0);
  });

  it("UTC로는 같은 날이어도 KST로 날짜가 넘어가면 1", () => {
    // 대상: UTC 08-11 15:00 = KST 08-12 00:00
    // 기준: UTC 08-11 14:00 = KST 08-11 23:00
    expect(
      daysUntilKST("2026-08-11T15:00:00Z", new Date("2026-08-11T14:00:00Z")),
    ).toBe(1);
  });

  it("과거 시각이면 음수", () => {
    expect(
      daysUntilKST("2026-08-10T12:00:00", new Date("2026-08-11T12:00:00Z")),
    ).toBe(-1);
  });

  it("파싱 불가한 입력은 null", () => {
    expect(daysUntilKST("어제", new Date("2026-08-11T12:00:00Z"))).toBeNull();
  });
});

describe("kstInputToUtcISO", () => {
  it("KST 21:00 입력을 UTC 12:00으로 변환", () => {
    // 이 테스트는 TZ=UTC에서 돈다. 로컬 파싱 구현이면 21:00Z가 나와 실패한다
    expect(kstInputToUtcISO("2026-08-20T21:00")).toBe("2026-08-20T12:00:00.000Z");
  });

  it("초가 포함된 형식도 같은 결과", () => {
    expect(kstInputToUtcISO("2026-08-20T21:00:00")).toBe("2026-08-20T12:00:00.000Z");
  });

  it("KST 오전 8시는 전날 UTC 23시", () => {
    expect(kstInputToUtcISO("2026-08-20T08:00")).toBe("2026-08-19T23:00:00.000Z");
  });

  it("빈 문자열은 null", () => {
    expect(kstInputToUtcISO("")).toBeNull();
  });

  it("형식이 다른 입력은 null", () => {
    expect(kstInputToUtcISO("2026-08-20 21:00")).toBeNull();
  });

  it("형식은 맞지만 존재하지 않는 날짜는 null", () => {
    expect(kstInputToUtcISO("2026-13-45T21:00")).toBeNull();
  });
});

describe("utcISOToKstInput", () => {
  it("UTC ISO를 datetime-local 값으로", () => {
    expect(utcISOToKstInput("2026-08-20T12:00:00.000Z")).toBe("2026-08-20T21:00");
  });

  it("타임존 표시 없는 값도 UTC로 간주", () => {
    expect(utcISOToKstInput("2026-08-20T12:00:00")).toBe("2026-08-20T21:00");
  });

  it("분 단위 입력은 왕복해도 같다", () => {
    const input = "2026-08-20T21:00";
    expect(utcISOToKstInput(kstInputToUtcISO(input)!)).toBe(input);
  });
});
