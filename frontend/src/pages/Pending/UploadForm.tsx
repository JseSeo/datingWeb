import { useState } from "react";
import { uploadVerification, ApiError } from "../../lib/api";
import type { VerificationOut } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import styles from "./Pending.module.css";

const ALLOWED = ["image/jpeg", "image/png", "image/webp"];
const MAX_SIZE = 10 * 1024 * 1024;

export default function UploadForm({
  onUploaded,
}: {
  onUploaded: (v: VerificationOut) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function handleSelect(e: React.ChangeEvent<HTMLInputElement>) {
    setError("");
    const f = e.target.files?.[0];
    if (!f) return;
    if (!ALLOWED.includes(f.type)) {
      setError("JPG, PNG, WEBP 파일만 올릴 수 있어요");
      setFile(null);
      setPreview(null);
      return;
    }
    if (f.size > MAX_SIZE) {
      setError("파일 크기는 10MB 이하여야 해요");
      setFile(null);
      setPreview(null);
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  async function handleSubmit() {
    if (!file) {
      setError("파일을 선택해주세요");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const v = await uploadVerification(file);
      onUploaded(v);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "업로드에 실패했어요");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.form}>
      <input
        aria-label="학생증 파일"
        type="file"
        accept="image/*"
        onChange={handleSelect}
      />
      {preview && <img className={styles.preview} src={preview} alt="미리보기" />}
      {error && <p className={styles.error}>{error}</p>}
      <Button onClick={handleSubmit} disabled={submitting}>
        {submitting ? "제출 중…" : "제출"}
      </Button>
    </div>
  );
}
