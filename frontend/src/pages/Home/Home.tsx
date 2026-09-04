import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { getNextRound, getSurvey, getMyMatch } from "../../lib/api";
import { formatKST, daysUntilKST } from "../../lib/datetime";
import type { MatchRoundOut, MatchResultOut } from "../../lib/types";
import styles from "./Home.module.css";

export default function Home() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [round, setRound] = useState<MatchRoundOut | null>(null);
  const [roundFailed, setRoundFailed] = useState(false);
  // null = 조회 실패. 실패했으면 설문 관련 안내를 아예 띄우지 않는다.
  const [surveyDone, setSurveyDone] = useState<boolean | null>(null);
  const [match, setMatch] = useState<MatchResultOut | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 셋은 서로 독립이다. 하나가 실패해도 나머지는 표시돼야 해서 allSettled를 쓴다.
    Promise.allSettled([getNextRound(), getSurvey(), getMyMatch()]).then(([r, s, m]) => {
      if (r.status === "fulfilled") setRound(r.value);
      else setRoundFailed(true);
      if (s.status === "fulfilled") setSurveyDone(s.value.updated_at !== null);
      if (m.status === "fulfilled") setMatch(m.value);
      setLoading(false);
    });
  }, []);

  const days = round ? daysUntilKST(round.scheduled_at) : null;

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>{!loading && match ? "이번 주 매칭 결과" : "다음 매칭"}</h1>

      {!loading && match ? (
        <section className={styles.card}>
          <p className={styles.partner}>{match.name}</p>
          <p className={styles.when}>{match.university}</p>
          <ul className={styles.contacts}>
            {match.instagram && <li>인스타그램 @{match.instagram.replace(/^@/, "")}</li>}
            {match.kakao_id && <li>카카오톡 {match.kakao_id}</li>}
            {match.phone && <li>전화번호 {match.phone}</li>}
          </ul>
          {!match.instagram && !match.kakao_id && !match.phone && (
            <p className={styles.muted}>상대가 등록한 연락처가 없어요</p>
          )}
          <p className={styles.muted}>{formatKST(match.executed_at)} 매칭</p>
        </section>
      ) : (
        <section className={styles.card}>
          {loading && <p className={styles.muted}>불러오는 중…</p>}
          {!loading && roundFailed && (
            <p className={styles.error}>일정을 불러오지 못했어요</p>
          )}
          {!loading && !roundFailed && !round && (
            <>
              <p className={styles.empty}>아직 예정된 매칭이 없어요</p>
              <p className={styles.muted}>일정이 정해지면 여기에 표시돼요</p>
            </>
          )}
          {!loading && round && (
            <>
              {days !== null && days >= 0 && (
                <p className={styles.dday}>{days === 0 ? "D-DAY" : `D-${days}`}</p>
              )}
              <p className={styles.when}>{formatKST(round.scheduled_at)}</p>
            </>
          )}
        </section>
      )}

      {!loading && (
        <section className={styles.status}>
          {surveyDone === false && (
            <div className={styles.notice}>
              <p className={styles.noticeText}>⚠ 설문을 아직 안 했어요</p>
              <button
                type="button"
                className={styles.cta}
                onClick={() => navigate("/survey")}
              >
                설문 하러가기
              </button>
            </div>
          )}
          {user?.matching_paused && (
            <div className={styles.notice}>
              <p className={styles.noticeText}>⏸ 매칭 일시정지 중</p>
              <button
                type="button"
                className={styles.cta}
                onClick={() => navigate("/mypage")}
              >
                마이페이지에서 해제
              </button>
            </div>
          )}
          {surveyDone === true && !user?.matching_paused && (
            <p className={styles.ok}>✓ 매칭 참여 중</p>
          )}
        </section>
      )}
    </div>
  );
}
