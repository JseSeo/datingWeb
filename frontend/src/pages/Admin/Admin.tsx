import { useState } from "react";
import VerificationTab from "./VerificationTab";
import ReportTab from "./ReportTab";
import RoundTab from "./RoundTab";
import styles from "./Admin.module.css";

type Tab = "verification" | "report" | "round";

export default function Admin() {
  const [tab, setTab] = useState<Tab>("verification");

  return (
    <div>
      <h1 className={styles.title}>관리자</h1>
      <div className={styles.tabs} role="tablist">
        <button
          type="button"
          role="tab"
          id="tab-verification"
          aria-selected={tab === "verification"}
          className={tab === "verification" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("verification")}
        >
          학생증 심사
        </button>
        <button
          type="button"
          role="tab"
          id="tab-report"
          aria-selected={tab === "report"}
          className={tab === "report" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("report")}
        >
          신고 · 건의
        </button>
        <button
          type="button"
          role="tab"
          id="tab-round"
          aria-selected={tab === "round"}
          className={tab === "round" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("round")}
        >
          라운드
        </button>
      </div>
      {tab === "verification" && (
        <div role="tabpanel" aria-labelledby="tab-verification" tabIndex={0}>
          <VerificationTab />
        </div>
      )}
      {tab === "report" && (
        <div role="tabpanel" aria-labelledby="tab-report" tabIndex={0}>
          <ReportTab />
        </div>
      )}
      {tab === "round" && (
        <div role="tabpanel" aria-labelledby="tab-round" tabIndex={0}>
          <RoundTab />
        </div>
      )}
    </div>
  );
}
