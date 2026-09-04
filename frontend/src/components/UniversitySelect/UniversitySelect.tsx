import { useEffect, useState } from "react";
import { listUniversities } from "../../lib/api";
import type { UniversityOut } from "../../lib/types";
import styles from "../Input/Input.module.css";

interface Props {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  /** 가중치 규칙의 단일 대학(university_b="")처럼 "고르지 않음"이 유효한 경우 */
  allowEmpty?: boolean;
  emptyLabel?: string;
}

export function UniversitySelect({
  id, label, value, onChange, required, allowEmpty, emptyLabel = "선택하세요",
}: Props) {
  const [items, setItems] = useState<UniversityOut[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    listUniversities()
      .then((data) => { if (active) setItems(data); })
      .catch(() => { if (active) setItems([]); })
      .finally(() => { if (active) setLoaded(true); });
    return () => { active = false; };
  }, []);

  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>{label}</label>
      <select
        id={id}
        value={value}
        required={required}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{allowEmpty ? emptyLabel : "선택하세요"}</option>
        {items.map((u) => (
          <option key={u.id} value={u.name}>{u.name}</option>
        ))}
      </select>
      {loaded && items.length === 0 && (
        <p role="alert">등록된 대학이 없습니다. 관리자에게 문의하세요.</p>
      )}
    </div>
  );
}
