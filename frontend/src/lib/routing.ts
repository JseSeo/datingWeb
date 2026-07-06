import type { UserStatus } from "./types";

// suspended는 호출측에서 별도 차단 처리 (이동 경로 없음)
export function destinationFor(status: UserStatus): string {
  return status === "active" ? "/home" : "/pending";
}
