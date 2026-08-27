import type { FaceChoice, Question, AnswerValue } from "./types";
import styles from "./QuestionField.module.css";

interface Props {
  question: Question;
  value: AnswerValue | undefined;
  onChange: (value: AnswerValue) => void;
  faceTypes: FaceChoice[];
  faceAnyId: string;
}

function toggle(arr: string[], id: string): string[] {
  return arr.includes(id) ? arr.filter((x) => x !== id) : [...arr, id];
}

export function QuestionField({
  question: q,
  value,
  onChange,
  faceTypes,
  faceAnyId,
}: Props) {
  if (q.type === "single") {
    return (
      <div className={styles.field}>
        {q.choices!.map((c) => (
          <label key={c.id} className={styles.choice}>
            <input type="radio" name={q.id} checked={value === c.id}
              onChange={() => onChange(c.id)} />
            {c.label}
          </label>
        ))}
      </div>
    );
  }

  if (q.type === "multi") {
    const arr = Array.isArray(value) ? value : [];
    return (
      <div className={styles.field}>
        <p className={styles.hint}>복수 선택 가능</p>
        {q.choices!.map((c) => (
          <label key={c.id} className={styles.choice}>
            <input type="checkbox" checked={arr.includes(c.id)}
              onChange={() => onChange(toggle(arr, c.id))} />
            {c.label}
          </label>
        ))}
      </div>
    );
  }

  if (q.type === "scale") {
    return (
      <div className={styles.field}>
        <div className={styles.scaleRow}>
          <span className={styles.scaleEnd}>{q.scale_labels?.[0]}</span>
          {[1, 2, 3, 4, 5].map((n) => (
            <label key={n} className={styles.scaleItem}>
              <input type="radio" name={q.id} aria-label={String(n)}
                checked={value === n} onChange={() => onChange(n)} />
              {n}
            </label>
          ))}
          <span className={styles.scaleEnd}>{q.scale_labels?.[1]}</span>
        </div>
      </div>
    );
  }

  if (q.type === "number") {
    return (
      <div className={styles.field}>
        <input type="number" className={styles.number}
          min={q.min ?? undefined} max={q.max ?? undefined}
          value={typeof value === "number" ? value : ""}
          onChange={(e) => {
            const v = e.target.value;
            if (v === "") return;
            const n = parseInt(v, 10);
            if (!Number.isNaN(n)) onChange(n);
          }} />
        {q.unit && <span className={styles.unit}>{q.unit}</span>}
      </div>
    );
  }

  if (q.type === "ranking") {
    const order = Array.isArray(value) && value.length
      ? value
      : q.rank_items!.map((i) => i.id);
    const labelOf = (id: string) => q.rank_items!.find((i) => i.id === id)?.label ?? id;
    const move = (idx: number, dir: -1 | 1) => {
      const next = [...order];
      const j = idx + dir;
      if (j < 0 || j >= next.length) return;
      [next[idx], next[j]] = [next[j], next[idx]];
      onChange(next);
    };
    return (
      <ol className={styles.ranking}>
        {order.map((id, idx) => (
          <li key={id} className={styles.rankItem}>
            <span>{labelOf(id)}</span>
            <span>
              <button type="button" aria-label={`${labelOf(id)} 위로`}
                onClick={() => move(idx, -1)}>▲</button>
              <button type="button" aria-label={`${labelOf(id)} 아래로`}
                onClick={() => move(idx, 1)}>▼</button>
            </span>
          </li>
        ))}
      </ol>
    );
  }

  // image-single | image-multi
  const isMulti = q.type === "image-multi";
  const arr = Array.isArray(value) ? value : [];
  const faceOptions = isMulti
    ? [...faceTypes, { id: faceAnyId, label: "상관없음", image: "" }]
    : faceTypes;
  return (
    <div className={styles.field}>
      {isMulti && <p className={styles.hint}>복수 선택 가능</p>}
      <div className={styles.faceGrid}>
        {faceOptions.map((f) => {
          const selected = isMulti ? arr.includes(f.id) : value === f.id;
          return (
            <label key={f.id} className={styles.faceCell} data-selected={selected}>
              <input
                type={isMulti ? "checkbox" : "radio"}
                name={q.id}
                aria-label={f.label}
                checked={selected}
                onChange={() => onChange(isMulti ? toggle(arr, f.id) : f.id)}
              />
              {f.image && <img src={f.image} alt={f.label} className={styles.faceImg} />}
              <span>{f.label}</span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
