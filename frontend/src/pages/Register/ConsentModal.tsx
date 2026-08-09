import { useEffect } from "react";

type ConsentType = "terms" | "privacy";

const TITLES: Record<ConsentType, string> = {
  terms: "이용약관",
  privacy: "개인정보처리방침",
};

export function ConsentModal({ type, onClose }: { type: ConsentType; onClose: () => void }) {
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    // 키보드 사용자는 Esc 와 "닫기" 버튼으로 닫을 수 있으므로 배경 클릭 닫기는 예외로 둔다.
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions
    <div
      role="dialog"
      aria-modal="true"
      aria-label={TITLES[type]}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
        display: "flex", alignItems: "center", justifyContent: "center", padding: 16,
      }}
      // 배경(이 요소 자신)을 눌렀을 때만 닫는다. 내용 영역 클릭은 여기까지 올라와도 무시된다.
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{ background: "#FFF5E6", borderRadius: 8, padding: 24, maxWidth: 340, maxHeight: "70vh", overflowY: "auto" }}
      >
        <h2>{TITLES[type]}</h2>
        <p>준비 중입니다 — 팀 문안 확정 후 교체 예정.</p>
        <button type="button" onClick={onClose}>닫기</button>
      </div>
    </div>
  );
}
