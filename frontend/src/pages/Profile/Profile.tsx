import { useState, type FormEvent, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { updateProfile, uploadProfilePhoto, ApiError } from "../../lib/api";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import styles from "./Profile.module.css";

const API = import.meta.env.VITE_API_URL;

export default function Profile() {
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();

  const [bio, setBio] = useState(user?.bio ?? "");
  const [instagram, setInstagram] = useState(user?.instagram ?? "");
  const [kakaoId, setKakaoId] = useState(user?.kakao_id ?? "");
  const [phone, setPhone] = useState(user?.phone ?? "");
  const [photo, setPhoto] = useState(user?.profile_photo ?? null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handlePhoto(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    try {
      const updated = await uploadProfilePhoto(file);
      setPhoto(updated.profile_photo);
      await refreshUser();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "사진 업로드에 실패했습니다");
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!instagram && !kakaoId && !phone) {
      setError("연락처를 1개 이상 입력하세요");
      return;
    }
    setSubmitting(true);
    try {
      await updateProfile({ bio, instagram, kakao_id: kakaoId, phone });
      await refreshUser();
      navigate("/mypage");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "저장에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>프로필 수정</h1>

      <div className={styles.photoRow}>
        {photo ? (
          <img className={styles.photo} src={`${API}${photo}`} alt="프로필 사진" />
        ) : (
          <div className={styles.photo} aria-label="기본 프로필" />
        )}
        <label>
          사진 변경
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handlePhoto}
            style={{ display: "none" }}
          />
        </label>
      </div>

      <p className={styles.readonly}>이름: {user?.name}</p>
      <p className={styles.readonly}>학교: {user?.university}</p>

      <form onSubmit={handleSubmit}>
        <label htmlFor="bio">자기소개</label>
        <textarea
          id="bio"
          className={styles.textarea}
          value={bio}
          onChange={(e) => setBio(e.target.value)}
        />
        <Input id="instagram" label="인스타그램" value={instagram}
          onChange={(e) => setInstagram(e.target.value)} />
        <Input id="kakao" label="카카오톡 ID" value={kakaoId}
          onChange={(e) => setKakaoId(e.target.value)} />
        <Input id="phone" label="전화번호" value={phone}
          onChange={(e) => setPhone(e.target.value)} />
        {error && <p className={styles.error}>{error}</p>}
        <Button type="submit" disabled={submitting}>
          {submitting ? "저장 중..." : "저장"}
        </Button>
      </form>
    </div>
  );
}
