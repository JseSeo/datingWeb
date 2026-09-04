import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { registerUser, ApiError } from "../../lib/api";
import { Input } from "../../components/Input/Input";
import { UniversitySelect } from "../../components/UniversitySelect/UniversitySelect";
import { Button } from "../../components/Button/Button";
import { ConsentModal } from "./ConsentModal";
import styles from "./Register.module.css";

export default function Register() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [university, setUniversity] = useState("");
  const [gender, setGender] = useState<"male" | "female" | "">("");
  const [instagram, setInstagram] = useState("");
  const [kakaoId, setKakaoId] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [agreedTerms, setAgreedTerms] = useState(false);
  const [agreedPrivacy, setAgreedPrivacy] = useState(false);
  const [agreedAge, setAgreedAge] = useState(false);
  const [modal, setModal] = useState<"terms" | "privacy" | null>(null);

  const allAgreed = agreedTerms && agreedPrivacy && agreedAge;

  function toggleAll() {
    const next = !allAgreed;
    setAgreedTerms(next);
    setAgreedPrivacy(next);
    setAgreedAge(next);
  }

  function validate(): string {
    if (!email.includes("@")) return "올바른 이메일을 입력하세요";
    if (password.length < 8) return "비밀번호는 8자 이상이어야 합니다";
    if (!name.trim()) return "이름을 입력하세요";
    if (!university.trim()) return "학교를 선택하세요";
    if (!gender) return "성별을 선택하세요";
    if (!instagram.trim() && !kakaoId.trim() && !phone.trim()) {
      return "연락처를 최소 1개 입력하세요";
    }
    return "";
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const v = validate();
    if (v) { setError(v); return; }
    setError("");
    setSubmitting(true);
    try {
      await registerUser({
        email, password, name: name.trim(), university: university.trim(),
        gender: gender as "male" | "female",
        agreed_terms: agreedTerms, agreed_privacy: agreedPrivacy, agreed_age_14: agreedAge,
        instagram: instagram.trim() || null,
        kakao_id: kakaoId.trim() || null,
        phone: phone.trim() || null,
      });
      navigate("/login", { state: { registered: true } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "가입에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>회원가입</h1>
      <form onSubmit={handleSubmit} noValidate>
        <Input id="email" label="이메일" type="email" value={email}
          onChange={(e) => setEmail(e.target.value)} />
        <Input id="password" label="비밀번호 (8자 이상)" type="password" value={password}
          onChange={(e) => setPassword(e.target.value)} />
        <Input id="name" label="이름" value={name}
          onChange={(e) => setName(e.target.value)} />
        <UniversitySelect id="university" label="학교" value={university}
          onChange={setUniversity} required />
        <fieldset className={styles.gender}>
          <legend>성별</legend>
          <label>
            <input type="radio" name="gender" checked={gender === "male"}
              onChange={() => setGender("male")} /> 남
          </label>
          <label>
            <input type="radio" name="gender" checked={gender === "female"}
              onChange={() => setGender("female")} /> 여
          </label>
        </fieldset>
        <p className={styles.notice}>매칭된 상대가 연락할 수 있도록 최소 1개는 필요합니다.</p>
        <Input id="instagram" label="인스타그램" value={instagram}
          onChange={(e) => setInstagram(e.target.value)} />
        <Input id="kakao" label="카카오톡 ID" value={kakaoId}
          onChange={(e) => setKakaoId(e.target.value)} />
        <Input id="phone" label="전화번호" value={phone}
          onChange={(e) => setPhone(e.target.value)} />
        <fieldset className={styles.consent}>
          <label>
            <input type="checkbox" checked={allAgreed} onChange={toggleAll} />
            전체 동의
          </label>
          <div>
            <label>
              <input type="checkbox" checked={agreedTerms}
                onChange={(e) => setAgreedTerms(e.target.checked)} />
              이용약관 동의 (필수)
            </label>
            <button type="button" onClick={() => setModal("terms")}>보기</button>
          </div>
          <div>
            <label>
              <input type="checkbox" checked={agreedPrivacy}
                onChange={(e) => setAgreedPrivacy(e.target.checked)} />
              개인정보처리방침 동의 (필수)
            </label>
            <button type="button" onClick={() => setModal("privacy")}>보기</button>
          </div>
          <label>
            <input type="checkbox" checked={agreedAge}
              onChange={(e) => setAgreedAge(e.target.checked)} />
            만 14세 이상입니다 (필수)
          </label>
          <p className={styles.notice}>만 14세 미만은 가입할 수 없습니다</p>
        </fieldset>
        {error && <p className={styles.error}>{error}</p>}
        <Button type="submit" disabled={submitting || !allAgreed || !gender}>
          {submitting ? "처리 중..." : "가입하기"}
        </Button>
      </form>
      {modal && <ConsentModal type={modal} onClose={() => setModal(null)} />}
    </div>
  );
}
