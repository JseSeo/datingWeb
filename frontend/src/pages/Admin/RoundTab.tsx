import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  ApiError,
  listMatchRounds,
  createMatchRound,
  updateMatchRound,
  deleteMatchRound,
  runMatchRound,
} from "../../lib/api";
import type { AdminMatchRoundOut, MatchingRunOut } from "../../lib/types";
import { formatKST, kstInputToUtcISO, utcISOToKstInput } from "../../lib/datetime";
import { Button } from "../../components/Button/Button";
import styles from "./Admin.module.css";

const INVALID_INPUT = "올바른 일시를 입력하세요.";
const GENERIC_ERROR = "요청에 실패했어요. 다시 시도해주세요.";

const STATUS_LABEL: Record<AdminMatchRoundOut["status"], string> = {
  pending: "예정",
  running: "실행중",
  done: "완료",
};

// 서버가 주는 값은 모두 같은 형식의 naive UTC 문자열이라 사전순 = 시간순이다.
function sortDesc(items: AdminMatchRoundOut[]): AdminMatchRoundOut[] {
  return [...items].sort((a, b) => b.scheduled_at.localeCompare(a.scheduled_at));
}

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : GENERIC_ERROR;
}

export default function RoundTab() {
  const [items, setItems] = useState<AdminMatchRoundOut[]>([]);
  const [form, setForm] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [running, setRunning] = useState<number | null>(null);
  const [summary, setSummary] = useState<(MatchingRunOut & { id: number }) | null>(null);

  useEffect(() => {
    let active = true;
    listMatchRounds()
      .then((data) => {
        if (active) setItems(sortDesc(data));
      })
      .catch(() => {
        if (active) setError("목록을 불러오지 못했어요.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError("");
    const iso = kstInputToUtcISO(form);
    if (iso === null) {
      setError(INVALID_INPUT);
      return;
    }
    try {
      // 낙관적 갱신을 하지 않는다 — 서버 응답을 받은 뒤에만 목록을 바꾼다
      const created = await createMatchRound(iso);
      setItems((prev) => sortDesc([...prev, created]));
      setForm("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  function startEdit(round: AdminMatchRoundOut) {
    setError("");
    setEditingId(round.id);
    setEditValue(utcISOToKstInput(round.scheduled_at));
  }

  async function handleSave(id: number) {
    setError("");
    const iso = kstInputToUtcISO(editValue);
    if (iso === null) {
      setError(INVALID_INPUT);
      return;
    }
    try {
      const updated = await updateMatchRound(id, iso);
      setItems((prev) => sortDesc(prev.map((r) => (r.id === id ? updated : r))));
      setEditingId(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("이 라운드를 삭제할까요?")) return;
    setError("");
    try {
      await deleteMatchRound(id);
      setItems((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleRun(id: number) {
    // 되돌릴 수 없는 작업이라 한 번 더 묻는다
    if (!window.confirm("이 라운드의 매칭을 실행할까요? 되돌릴 수 없어요.")) return;
    setError("");
    setRunning(id);
    try {
      const result = await runMatchRound(id);
      setSummary({ ...result, id });
      setItems((prev) =>
        prev.map((r) => (r.id === id ? { ...r, status: "done" } : r)),
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRunning(null);
    }
  }

  return (
    <div className={styles.wrap}>
      <form className={styles.formRow} onSubmit={handleCreate}>
        <label className={styles.formLabel} htmlFor="round-new">
          매칭 예정 일시
          <input
            id="round-new"
            type="datetime-local"
            value={form}
            onChange={(e) => setForm(e.target.value)}
          />
        </label>
        <Button type="submit">추가</Button>
      </form>

      {loading && <p>불러오는 중…</p>}
      {error && <p className={styles.error}>{error}</p>}
      {!loading && !error && items.length === 0 && <p>예정된 라운드 없음</p>}

      {items.map((round) => (
        <div key={round.id} className={styles.card}>
          <span className={styles.badge}>{STATUS_LABEL[round.status]}</span>
          {editingId === round.id ? (
            <>
              <label className={styles.formLabel} htmlFor={`round-edit-${round.id}`}>
                매칭 예정 일시 수정
                <input
                  id={`round-edit-${round.id}`}
                  type="datetime-local"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                />
              </label>
              <div className={styles.actions}>
                <Button onClick={() => handleSave(round.id)}>저장</Button>
                <Button onClick={() => setEditingId(null)}>취소</Button>
              </div>
            </>
          ) : (
            <>
              <div className={styles.name}>{formatKST(round.scheduled_at)}</div>
              {round.status === "pending" && (
                <div className={styles.actions}>
                  <Button onClick={() => handleRun(round.id)} disabled={running === round.id}>
                    {running === round.id ? "실행 중…" : "매칭 실행"}
                  </Button>
                  <Button onClick={() => startEdit(round)}>수정</Button>
                  <Button onClick={() => handleDelete(round.id)}>삭제</Button>
                </div>
              )}
              {summary?.id === round.id && (
                <p className={styles.summary}>
                  {summary.matched}쌍 매칭 (보장 {summary.guaranteed}쌍) · 미매칭 {summary.unmatched}명
                </p>
              )}
            </>
          )}
        </div>
      ))}
    </div>
  );
}
