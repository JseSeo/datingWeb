import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  ApiError,
  listAllUniversities,
  createUniversity,
  setUniversityActive,
  deleteUniversity,
} from "../../lib/api";
import type { UniversityOut } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import { Input } from "../../components/Input/Input";
import styles from "./Admin.module.css";

const GENERIC_ERROR = "요청에 실패했어요. 다시 시도해주세요.";

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : GENERIC_ERROR;
}

export default function UniversityTab() {
  const [items, setItems] = useState<UniversityOut[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function reload() {
    try {
      setItems(await listAllUniversities());
    } catch {
      setError("목록을 불러오지 못했어요.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void reload(); }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (name.trim() === "") { setError("대학명을 입력하세요."); return; }
    try {
      await createUniversity(name.trim());
      setName("");
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleToggle(item: UniversityOut) {
    setError("");
    try {
      await setUniversityActive(item.id, !item.active);
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleDelete(item: UniversityOut) {
    setError("");
    try {
      await deleteUniversity(item.id);
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  if (loading) return <p>불러오는 중…</p>;

  return (
    <div className={styles.panel}>
      <form onSubmit={handleCreate}>
        <Input
          id="university-name"
          label="대학명"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Button type="submit">추가</Button>
      </form>

      <p className={styles.hint}>
        이름은 등록 후 바꿀 수 없습니다. 쓰지 않는 대학은 삭제 대신 끄세요.
      </p>

      {error && <p role="alert">{error}</p>}

      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <span>{item.name}</span>
            <span>{item.active ? "활성" : "비활성"}</span>
            <Button type="button" onClick={() => void handleToggle(item)}>
              {item.active ? "끄기" : "켜기"}
            </Button>
            <Button type="button" onClick={() => void handleDelete(item)}>삭제</Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
