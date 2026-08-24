import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../lib/auth";
import { getSurvey, getSurveyCatalog, saveSurvey } from "../../lib/api";
import { QuestionField } from "./QuestionField";
import type {
  AnswerValue,
  FaceChoice,
  Question,
  SurveyResponses,
} from "./types";
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
  const [questions, setQuestions] = useState<Question[]>([]);
  const [faceTypes, setFaceTypes] = useState<FaceChoice[]>([]);
  const [faceAnyId, setFaceAnyId] = useState("any");
  const [catalogFailed, setCatalogFailed] = useState(false);

  const visible = useMemo(
    () => questions.filter((q) => !(q.male_only && user?.gender !== "male")),
    [questions, user?.gender],
  );

  useEffect(() => {
    getSurveyCatalog()
      .then((c) => {
        setQuestions(c.questions);
        setFaceTypes(c.face_types);
        setFaceAnyId(c.face_any_id);
      })
      .catch(() => setCatalogFailed(true));
  }, []);

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
    if (q.no_pref_id) {
      if (v === q.no_pref_id) return false;
      if (Array.isArray(v) && v.includes(q.no_pref_id)) return false;
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
        if (q.no_pref_id) {
          if (v === q.no_pref_id) return false;
          if (Array.isArray(v) && v.includes(q.no_pref_id)) return false;
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

  if (catalogFailed) {
    return (
      <div className={styles.wrap}>
        <h1 className={styles.title}>가치관 설문</h1>
        <p className={styles.err}>설문을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.</p>
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className={styles.wrap}>
        <h1 className={styles.title}>가치관 설문</h1>
        <p className={styles.progress}>불러오는 중...</p>
      </div>
    );
  }

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
                onChange={(v) => setValue(q.id, v)}
                faceTypes={faceTypes} faceAnyId={faceAnyId} />
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
