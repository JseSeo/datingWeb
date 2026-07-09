import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { fetchMe, getMyVerification } from "../../lib/api";
import type { VerificationOut } from "../../lib/types";
import { Button } from "../../components/Button/Button";
import UploadForm from "./UploadForm";
import styles from "./Pending.module.css";

function messageFor(v: VerificationOut | null): string {
  if (v === null) return "학생증을 올려 인증을 완료해주세요.";
  if (v.status === "rejected") return "인증이 반려됐어요. 학생증을 다시 올려주세요.";
  return "학생증 인증이 검토 중입니다. 승인되면 매칭에 참여할 수 있어요.";
}

export default function Pending() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [verification, setVerification] = useState<VerificationOut | null>(null);

  useEffect(() => {
    let active = true;
    (async () => {
      const [me, verif] = await Promise.all([fetchMe(), getMyVerification()]);
      if (!active) return;
      if (me.status === "active") {
        navigate("/home");
        return;
      }
      setVerification(verif);
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [navigate]);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  if (loading) {
    return (
      <div className={styles.wrap}>
        <p className={styles.desc}>확인 중…</p>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>승인 대기 중</h1>
      <p className={styles.desc}>{messageFor(verification)}</p>
      <UploadForm onUploaded={(v) => setVerification(v)} />
      <Button onClick={handleLogout}>로그아웃</Button>
    </div>
  );
}
