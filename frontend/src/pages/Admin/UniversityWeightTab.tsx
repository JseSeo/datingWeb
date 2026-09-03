import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  ApiError,
  listUniversityWeights,
  createUniversityWeight,
  updateUniversityWeight,
  deleteUniversityWeight,
} from "../../lib/api";
import type { UniversityWeightOut } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import styles from "./Admin.module.css";

const INVALID_INPUT = "대학명과 보너스를 확인하세요.";
const GENERIC_ERROR = "요청에 실패했어요. 다시 시도해주세요.";

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : GENERIC_ERROR;
}

// 단일 규칙은 대학 하나, 쌍 규칙은 둘을 나란히 보여준다
function ruleLabel(weight: UniversityWeightOut): string {
  return weight.university_b === ""
    ? weight.university_a
    : `${weight.university_a} × ${weight.university_b}`;
}

export default function UniversityWeightTab() {
  const [items, setItems] = useState<UniversityWeightOut[]>([]);
  const [uniA, setUniA] = useState("");
  const [uniB, setUniB] = useState("");
  const [bonus, setBonus] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    listUniversityWeights()
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
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError("");
    const parsed = Number(bonus);
    // 빈 문자열은 Number가 0으로 바꾸므로 따로 걸러야 한다
    if (uniA.trim() === "" || bonus.trim() === "" || !Number.isInteger(parsed)) {
      setError(INVALID_INPUT);
      return;
    }
    try {
      const created = await createUniversityWeight({
        university_a: uniA.trim(),
        university_b: uniB.trim(),
        bonus: parsed,
        active: true,
        note: note.trim() === "" ? null : note.trim(),
      });
      setItems((prev) => [...prev, created]);
      setUniA("");
      setUniB("");
      setBonus("");
      setNote("");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleToggle(weight: UniversityWeightOut) {
    setError("");
    try {
      const saved = await updateUniversityWeight(weight.id, {
        university_a: weight.university_a,
        university_b: weight.university_b,
        bonus: weight.bonus,
        active: !weight.active,
        note: weight.note,
      });
      setItems((prev) => prev.map((w) => (w.id === saved.id ? saved : w)));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("이 규칙을 삭제할까요?")) return;
    setError("");
    try {
      await deleteUniversityWeight(id);
      setItems((prev) => prev.filter((w) => w.id !== id));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className={styles.wrap}>
      <form className={styles.formRow} onSubmit={handleCreate}>
        <label className={styles.formLabel} htmlFor="weight-a">
          대학 A
          <input id="weight-a" value={uniA} onChange={(e) => setUniA(e.target.value)} />
        </label>
        <label className={styles.formLabel} htmlFor="weight-b">
          대학 B (비우면 단일 대학 규칙)
          <input id="weight-b" value={uniB} onChange={(e) => setUniB(e.target.value)} />
        </label>
        <label className={styles.formLabel} htmlFor="weight-bonus">
          보너스 (음수는 페널티, 합계 ±50까지만 적용)
          <input
            id="weight-bonus"
            type="number"
            value={bonus}
            onChange={(e) => setBonus(e.target.value)}
          />
        </label>
        <label className={styles.formLabel} htmlFor="weight-note">
          메모
          <input id="weight-note" value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <Button type="submit">추가</Button>
      </form>

      {loading && <p>불러오는 중…</p>}
      {error && <p className={styles.error}>{error}</p>}
      {!loading && !error && items.length === 0 && <p>등록된 규칙 없음</p>}

      {items.map((weight) => (
        <div key={weight.id} className={styles.card}>
          <span className={styles.badge}>{weight.active ? "적용" : "중지"}</span>
          <div className={styles.name}>{ruleLabel(weight)}</div>
          <div className={styles.university}>
            {weight.bonus > 0 ? `+${weight.bonus}점` : `${weight.bonus}점`}
          </div>
          {weight.note && <p className={styles.reason}>{weight.note}</p>}
          <div className={styles.actions}>
            <Button onClick={() => handleToggle(weight)}>
              {weight.active ? "중지" : "적용"}
            </Button>
            <Button onClick={() => handleDelete(weight.id)}>삭제</Button>
          </div>
        </div>
      ))}
    </div>
  );
}
