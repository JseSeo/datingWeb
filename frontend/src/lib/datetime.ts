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
