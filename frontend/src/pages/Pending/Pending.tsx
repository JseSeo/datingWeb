import { useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { Button } from "../../components/Button/Button";
import styles from "./Pending.module.css";

export default function Pending() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>승인 대기 중</h1>
      <p className={styles.desc}>
        학생증 인증이 검토 중입니다. 승인되면 매칭에 참여할 수 있어요.
      </p>
      <Button onClick={handleLogout}>로그아웃</Button>
    </div>
  );
}
