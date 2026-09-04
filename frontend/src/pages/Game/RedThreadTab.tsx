import { useState, useEffect, type FormEvent } from "react";
import {
  getRedThread,
  getRedThreadReceived,
  postRedThread,
  ApiError,
} from "../../lib/api";
import { Input } from "../../components/Input/Input";
import { UniversitySelect } from "../../components/UniversitySelect/UniversitySelect";
import { Button } from "../../components/Button/Button";
import styles from "./Game.module.css";

export default function RedThreadTab() {
  const [name1, setName1] = useState("");
  const [univ1, setUniv1] = useState("");
  const [year1, setYear1] = useState("");
  const [name2, setName2] = useState("");
  const [univ2, setUniv2] = useState("");
  const [year2, setYear2] = useState("");
  const [received, setReceived] = useState(0);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([getRedThread(), getRedThreadReceived()])
      .then(([thread, recv]) => {
        const [t1, t2] = thread.targets;
        if (t1) {
          setName1(t1.target_name);
          setUniv1(t1.target_university);
          setYear1(t1.target_admission_year ? String(t1.target_admission_year) : "");
        }
        if (t2) {
          setName2(t2.target_name);
          setUniv2(t2.target_university);
          setYear2(t2.target_admission_year ? String(t2.target_admission_year) : "");
        }
        setReceived(recv.count);
      })
      .catch(() => {
        /* 초기 로드 실패 시 빈 폼 유지 */
      });
  }, []);

  function buildTargets() {
    const out: { target_name: string; target_university: string; target_admission_year: number | null }[] = [];
    if (name1.trim() && univ1.trim()) {
      out.push({
        target_name: name1.trim(),
        target_university: univ1.trim(),
        target_admission_year: Number(year1) || null,
      });
    }
    if (name2.trim() && univ2.trim()) {
      out.push({
        target_name: name2.trim(),
        target_university: univ2.trim(),
        target_admission_year: Number(year2) || null,
      });
    }
    return out;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    const targets = buildTargets();
    if (
      targets.length === 2 &&
      targets[0].target_name === targets[1].target_name &&
      targets[0].target_university === targets[1].target_university
    ) {
      setError("같은 사람을 두 번 넣을 수 없어요");
      return;
    }
    setSubmitting(true);
    try {
      const result = await postRedThread(targets);
      const [t1, t2] = result.targets;
      setName1(t1?.target_name ?? "");
      setUniv1(t1?.target_university ?? "");
      setYear1(t1?.target_admission_year ? String(t1.target_admission_year) : "");
      setName2(t2?.target_name ?? "");
      setUniv2(t2?.target_university ?? "");
      setYear2(t2?.target_admission_year ? String(t2.target_admission_year) : "");
      setMessage("저장됐어요");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "저장에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmit = buildTargets().length >= 1;

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <p className={styles.received}>
        {received > 0 ? `나를 ${received}명이 지목했어요` : "아직 나를 지목한 사람이 없어요"}
      </p>
      <p className={styles.hint}>마음에 둔 상대를 최대 2명까지 적어주세요. (최소 1명)</p>
      <Input id="rt-name1" label="상대1 이름" value={name1}
        onChange={(e) => setName1(e.target.value)} />
      <UniversitySelect id="rt-univ1" label="상대1 학교" value={univ1}
        onChange={setUniv1} />
      <Input id="rt-year1" label="상대1 학번" type="number" value={year1}
        onChange={(e) => setYear1(e.target.value)} />
      <Input id="rt-name2" label="상대2 이름" value={name2}
        onChange={(e) => setName2(e.target.value)} />
      <UniversitySelect id="rt-univ2" label="상대2 학교" value={univ2}
        onChange={setUniv2} />
      <Input id="rt-year2" label="상대2 학번" type="number" value={year2}
        onChange={(e) => setYear2(e.target.value)} />
      <p className={styles.hint}>선택 입력. 동명이인이 있으면 학번 없이는 지목이 반영되지 않을 수 있습니다.</p>
      {error && <p className={styles.error}>{error}</p>}
      {message && <p className={styles.success}>{message}</p>}
      <Button type="submit" disabled={submitting || !canSubmit}>
        {submitting ? "저장 중..." : "저장"}
      </Button>
    </form>
  );
}
