import { useEffect, useState } from "react";
import { listReports, markReportHandled } from "../../lib/api";
import type { AdminReportOut } from "../../lib/types";
import { formatKST } from "../../lib/datetime";
import { Button } from "../../components/Button/Button";
import styles from "./Admin.module.css";

export default function ReportTab() {
  const [items, setItems] = useState<AdminReportOut[]>([]);
  const [includeHandled, setIncludeHandled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    listReports(includeHandled)
      .then((data) => {
        if (active) setItems(data);
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
  }, [includeHandled]);

  async function handle(id: number) {
    try {
      const updated = await markReportHandled(id);
      setItems((prev) =>
        includeHandled
          ? prev.map((r) => (r.id === updated.id ? updated : r))
          : prev.filter((r) => r.id !== id),
      );
    } catch {
      setError("처리에 실패했어요. 다시 시도해주세요.");
    }
  }

  return (
    <div className={styles.wrap}>
      <label className={styles.filter}>
        <input
          type="checkbox"
          checked={includeHandled}
          onChange={(e) => setIncludeHandled(e.target.checked)}
        />
        처리된 항목도 보기
      </label>
      {loading && <p>불러오는 중…</p>}
      {error && <p className={styles.error}>{error}</p>}
      {!loading && !error && items.length === 0 && <p>신고 · 건의 없음</p>}
      {items.map((r) => (
        <div key={r.id} className={styles.card} data-handled={r.handled}>
          <span className={styles.badge}>
            {r.type === "report" ? "신고" : "건의"}
          </span>
          {r.type === "report" && (
            <div className={styles.name}>
              대상: {r.target_name} · {r.target_university}
            </div>
          )}
          <div className={styles.university}>
            {r.type === "report" ? "신고자" : "작성자"}: {r.reporter_name} ·{" "}
            {r.reporter_university}
          </div>
          <div className={styles.when}>{formatKST(r.created_at)}</div>
          <p className={styles.reason}>{r.reason}</p>
          {!r.handled && <Button onClick={() => handle(r.id)}>처리 완료</Button>}
        </div>
      ))}
    </div>
  );
}
