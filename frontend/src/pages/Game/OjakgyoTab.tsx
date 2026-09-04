import { useState, type FormEvent } from "react";
import { postOjakgyo, ApiError } from "../../lib/api";
import { Input } from "../../components/Input/Input";
import { UniversitySelect } from "../../components/UniversitySelect/UniversitySelect";
import { Button } from "../../components/Button/Button";
import styles from "./Game.module.css";

export default function OjakgyoTab() {
  const [aName, setAName] = useState("");
  const [aUniv, setAUniv] = useState("");
  const [aYear, setAYear] = useState("");
  const [bName, setBName] = useState("");
  const [bUniv, setBUniv] = useState("");
  const [bYear, setBYear] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function reset() {
    setAName(""); setAUniv(""); setAYear("");
    setBName(""); setBUniv(""); setBYear("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");
    const a = [aName.trim(), aUniv.trim()];
    const b = [bName.trim(), bUniv.trim()];
    if (a[0] === b[0] && a[1] === b[1]) {
      setError("두 사람이 같아요");
      return;
    }
    setSubmitting(true);
    try {
      await postOjakgyo({
        person_a_name: aName,
        person_a_university: aUniv,
        person_b_name: bName,
        person_b_university: bUniv,
        person_a_admission_year: Number(aYear) || null,
        person_b_admission_year: Number(bYear) || null,
      });
      setMessage("중매 완료!");
      reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "중매에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <p className={styles.hint}>마음이 잘 맞을 것 같은 두 사람을 이어주세요.</p>
      <Input id="a-name" label="사람1 이름" value={aName}
        onChange={(e) => setAName(e.target.value)} />
      <UniversitySelect id="a-univ" label="사람1 학교" value={aUniv}
        onChange={setAUniv} required />
      <Input id="a-year" label="사람1 학번" type="number" value={aYear}
        onChange={(e) => setAYear(e.target.value)} />
      <Input id="b-name" label="사람2 이름" value={bName}
        onChange={(e) => setBName(e.target.value)} />
      <UniversitySelect id="b-univ" label="사람2 학교" value={bUniv}
        onChange={setBUniv} required />
      <Input id="b-year" label="사람2 학번" type="number" value={bYear}
        onChange={(e) => setBYear(e.target.value)} />
      <p className={styles.hint}>선택 입력. 동명이인이 있으면 학번 없이는 지목이 반영되지 않을 수 있습니다.</p>
      {error && <p className={styles.error}>{error}</p>}
      {message && <p className={styles.success}>{message}</p>}
      <Button type="submit" disabled={submitting}>
        {submitting ? "처리 중..." : "중매하기"}
      </Button>
    </form>
  );
}
