type ConsentType = "terms" | "privacy";

const TITLES: Record<ConsentType, string> = {
  terms: "이용약관",
  privacy: "개인정보처리방침",
};

export function ConsentModal({ type, onClose }: { type: ConsentType; onClose: () => void }) {
  return (
    <div
      role="dialog"
      aria-label={TITLES[type]}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
        display: "flex", alignItems: "center", justifyContent: "center", padding: 16,
      }}
      onClick={onClose}
    >
      <div
        style={{ background: "#FFF5E6", borderRadius: 8, padding: 24, maxWidth: 340, maxHeight: "70vh", overflowY: "auto" }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2>{TITLES[type]}</h2>
        <p>준비 중입니다 — 팀 문안 확정 후 교체 예정.</p>
        <button type="button" onClick={onClose}>닫기</button>
      </div>
    </div>
  );
}
