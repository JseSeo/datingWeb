import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../lib/auth";
import { getSurvey, saveSurvey } from "../../lib/api";
import { QUESTIONS } from "./questions";
import { QuestionField } from "./QuestionField";
import type { AnswerValue, Question, SurveyResponses } from "./types";
import styles from "./Survey.module.css";

function isAnswered(_q: Question, v: AnswerValue | undefined): boolean {
  if (v === undefined) return false;
  if (Array.isArray(v)) return v.length > 0;
  if (typeof v === "string") return v !== "";
  return true; // number
}

export default function Survey() {
  const { user } = useAuth();
  const [responses, setResponses] = useState<SurveyResponses>({});
  const [absolute, setAbsolute] = useState<string[]>([]);
  const [status, setStatus] = useState<"" | "saving" | "saved" | "error">("");

  const visible = useMemo(
    () => QUESTIONS.filter((q) => !(q.maleOnly && user?.gender !== "male")),
    [user?.gender],
  );

  useEffect(() => {
    getSurvey().then((res) => {
      const a = res.answers as { responses?: SurveyResponses; absolute?: string[] };
      if (a && a.responses) {
        setResponses(a.responses);
        setAbsolute(a.absolute ?? []);
      }
    });
  }, []);

  const answeredCount = visible.filter((q) => isAnswered(q, responses[q.id])).length;

  function setValue(id: string, v: AnswerValue) {
    setResponses((prev) => ({ ...prev, [id]: v }));
  }

  function canToggleAbsolute(q: Question): boolean {
    if (q.section !== "partner") return false;
    const v = responses[q.id];
    if (!isAnswered(q, v)) return false;
    if (q.noPrefId) {
      if (v === q.noPrefId) return false;
      if (Array.isArray(v) && v.includes(q.noPrefId)) return false;
    }
    if (absolute.length >= 2 && !absolute.includes(q.id)) return false;
    return true;
  }

  function toggleAbsolute(id: string) {
    setAbsolute((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]);
  }

  async function handleSave() {
    setStatus("saving");
    try {
      // 상관없음이 됐거나 미응답/숨김이 된 문항은 absolute에서 정리
      const cleaned = absolute.filter((id) => {
        const q = visible.find((x) => x.id === id);
        if (!q) return false;
        const v = responses[id];
        if (!isAnswered(q, v)) return false;
        if (q.noPrefId) {
          if (v === q.noPrefId) return false;
          if (Array.isArray(v) && v.includes(q.noPrefId)) return false;
        }
        return true;
      });
      await saveSurvey({ responses, absolute: cleaned });
      setStatus("saved");
    } catch {
      setStatus("error");
    }
  }

  const sections: { key: "self" | "partner"; title: string }[] = [
    { key: "self", title: "나에 대해" },
    { key: "partner", title: "원하는 상대" },
  ];

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>가치관 설문</h1>
      <p className={styles.progress}>{answeredCount} / {visible.length} 응답</p>

      {sections.map((sec) => (
        <section key={sec.key}>
          <h2 className={styles.section}>{sec.title}</h2>
          {visible.filter((q) => q.section === sec.key).map((q) => (
            <div key={q.id} className={styles.question}>
              <div className={styles.qHead}>
                <span className={styles.qLabel}>{q.label}</span>
                {q.section === "partner" && (
                  <button type="button" className={styles.star}
                    aria-label={`${q.label} 절대질문`}
                    aria-pressed={absolute.includes(q.id)}
                    disabled={!canToggleAbsolute(q) && !absolute.includes(q.id)}
                    onClick={() => toggleAbsolute(q.id)}>
                    {absolute.includes(q.id) ? "★" : "☆"}
                  </button>
                )}
              </div>
              <QuestionField question={q} value={responses[q.id]}
                onChange={(v) => setValue(q.id, v)} />
            </div>
          ))}
        </section>
      ))}

      <p className={styles.absInfo}>절대질문 {absolute.length} / 2</p>
      {status === "saved" && <p className={styles.ok}>저장되었습니다</p>}
      {status === "error" && <p className={styles.err}>저장에 실패했습니다</p>}
      <button type="button" className={styles.save}
        disabled={status === "saving"} onClick={handleSave}>
        {status === "saving" ? "저장 중..." : "저장"}
      </button>
    </div>
  );
}
