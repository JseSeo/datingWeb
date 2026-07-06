import { useNavigate } from "react-router-dom";
import { Button } from "../../components/Button/Button";
import styles from "./Landing.module.css";

export default function Landing() {
  const navigate = useNavigate();
  return (
    <div className={styles.wrap}>
      <h1 className={styles.title}>DateDrop</h1>
      <p className={styles.subtitle}>한국 대학생 주간 소개팅 매칭</p>
      <div className={styles.actions}>
        <Button onClick={() => navigate("/register")}>회원가입</Button>
        <button className={styles.linkBtn} onClick={() => navigate("/login")}>
          이미 계정이 있어요
        </button>
      </div>
    </div>
  );
}
