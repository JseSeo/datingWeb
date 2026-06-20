import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { toggleMatchingPause, withdraw, clearToken } from "../../lib/api";
import styles from "./MyPage.module.css";

const API = import.meta.env.VITE_API_URL;

const STATUS_LABEL: Record<string, string> = {
  pending: "인증 대기",
  active: "활동중",
  suspended: "정지",
  withdrawn: "탈퇴",
};

export default function MyPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [paused, setPaused] = useState(user?.matching_paused ?? false);

  async function handlePause() {
    const next = !paused;
    setPaused(next);
    try {
      await toggleMatchingPause(next);
    } catch {
      setPaused(!next); // 실패 롤백
    }
  }

  function handleLogout() {
    logout();
    navigate("/");
  }

  async function handleWithdraw() {
    if (!window.confirm("정말 탈퇴하시겠어요? 프로필·연락처·설문이 삭제됩니다.")) {
      return;
    }
    await withdraw();
    clearToken();
    navigate("/");
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        {user?.profile_photo ? (
          <img className={styles.photo} src={`${API}${user.profile_photo}`} alt="프로필" />
        ) : (
          <div className={styles.photo} aria-label="기본 프로필" />
        )}
        <div className={styles.name}>{user?.name}</div>
        <div className={styles.school}>{user?.university}</div>
        <span className={styles.badge}>
          {STATUS_LABEL[user?.status ?? "pending"]}
        </span>
      </div>

      <div className={styles.card}>
        <button className={styles.row} onClick={() => navigate("/profile")}>
          <span>프로필 수정</span><span>›</span>
        </button>
        <div className={`${styles.row} ${styles.rowDisabled}`}>
          <span>가치관 설문</span><span className={styles.soon}>준비중</span>
        </div>
      </div>

      <div className={styles.card}>
        <button className={styles.row} onClick={handlePause}>
          <span>매칭 일시중지</span>
          <span>{paused ? "ON" : "OFF"}</span>
        </button>
      </div>

      <div className={styles.card}>
        <button className={styles.row} onClick={handleLogout}>
          <span>로그아웃</span><span>›</span>
        </button>
        <button className={`${styles.row} ${styles.danger}`} onClick={handleWithdraw}>
          <span>회원 탈퇴</span><span>›</span>
        </button>
      </div>
    </div>
  );
}
