import { useState, type FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { destinationFor } from "../../lib/routing";
import { ApiError } from "../../lib/api";
import { Input } from "../../components/Input/Input";
import { Button } from "../../components/Button/Button";
import styles from "./Login.module.css";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, logout } = useAuth();
  const registered = (location.state as { registered?: boolean } | null)?.registered;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const user = await login(email, password);
      if (user.status === "suspended") {
        logout();
        setError("이용이 정지된 계정입니다. 운영팀에 문의하세요.");
        return;
      }
      navigate(destinationFor(user.status));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "로그인에 실패했습니다");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>로그인</h1>
      {registered && <p className={styles.notice}>가입이 완료되었습니다. 로그인하세요.</p>}
      <form onSubmit={handleSubmit}>
        <Input id="email" label="이메일" type="email" value={email}
          onChange={(e) => setEmail(e.target.value)} />
        <Input id="password" label="비밀번호" type="password" value={password}
          onChange={(e) => setPassword(e.target.value)} />
        {error && <p className={styles.error}>{error}</p>}
        <Button type="submit" disabled={submitting}>
          {submitting ? "처리 중..." : "로그인"}
        </Button>
      </form>
    </div>
  );
}
