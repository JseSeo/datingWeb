// 서버는 naive UTC(타임존 표시 없음)로 내려준다. 표시가 없으면 UTC로 간주한다.
// 날짜 부분의 "-"(2026-08-03)를 offset으로 오인하지 않도록 끝 위치에 고정한다.
const TZ_SUFFIX = /(Z|[+-]\d{2}:\d{2})$/;

const KST_FORMAT = new Intl.DateTimeFormat("en-US", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

/** UTC ISO 문자열을 "YYYY-MM-DD HH:mm" 형태의 KST로 변환. 실패하면 원문 반환. */
export function formatKST(iso: string): string {
  const date = new Date(TZ_SUFFIX.test(iso) ? iso : `${iso}Z`);
  if (Number.isNaN(date.getTime())) return iso;

  const parts = KST_FORMAT.formatToParts(date);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")} ${get("hour")}:${get("minute")}`;
}

// en-CA 로케일은 YYYY-MM-DD 형태를 준다 — 날짜만 비교하기 위해 사용.
const KST_DATE = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** KST 자정 기준 UTC 밀리초. 날짜만 비교하려고 시각을 버린다. */
function kstDayStart(date: Date): number {
  const [year, month, day] = KST_DATE.format(date).split("-").map(Number);
  return Date.UTC(year, month - 1, day);
}

/**
 * KST 달력 기준 남은 "날짜" 수. 시각 차이가 아니라 날짜 차이다.
 * 과거면 음수. 파싱 실패하면 null.
 */
export function daysUntilKST(iso: string, now: Date = new Date()): number | null {
  const target = new Date(TZ_SUFFIX.test(iso) ? iso : `${iso}Z`);
  if (Number.isNaN(target.getTime())) return null;
  const MS_PER_DAY = 86_400_000;
  return Math.round((kstDayStart(target) - kstDayStart(now)) / MS_PER_DAY);
}
