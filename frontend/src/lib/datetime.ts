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

// KST는 서머타임이 없어 고정 +09:00이다.
const KST_OFFSET = "+09:00";
const MINUTE_FORM = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;
const SECOND_FORM = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/;

/**
 * datetime-local 값(KST로 해석)을 UTC ISO 문자열로. 잘못된 값이면 null.
 * 오프셋을 명시해 파싱한다 — 접미사 없이 파싱하면 브라우저 로컬 시각이 되어
 * KST가 아닌 환경에서 조용히 틀린다. 브라우저마다 초 유무가 달라 둘 다 받는다.
 */
export function kstInputToUtcISO(local: string): string | null {
  let value: string;
  if (MINUTE_FORM.test(local)) value = `${local}:00`;
  else if (SECOND_FORM.test(local)) value = local;
  else return null;

  const date = new Date(`${value}${KST_OFFSET}`);
  if (Number.isNaN(date.getTime())) return null;
  // 존재하지 않는 날짜(2/30, 4/31 등)는 형식은 맞아도 JS Date가 다음 달로
  // 조용히 넘겨버린다 — KST 기준으로 되돌려 입력 날짜와 다르면 거부한다.
  if (KST_DATE.format(date) !== local.slice(0, 10)) return null;
  return date.toISOString();
}

/** UTC ISO를 datetime-local 초기값("YYYY-MM-DDTHH:mm")으로. */
export function utcISOToKstInput(iso: string): string {
  return formatKST(iso).replace(" ", "T");
}
