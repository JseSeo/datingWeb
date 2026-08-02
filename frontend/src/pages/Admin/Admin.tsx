import { useState } from "react";
import VerificationTab from "./VerificationTab";
import ReportTab from "./ReportTab";
import styles from "./Admin.module.css";

type Tab = "verification" | "report";

export default function Admin() {
  const [tab, setTab] = useState<Tab>("verification");

  return (
    <div>
      <div className={styles.tabs}>
        <button
          type="button"
          className={tab === "verification" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("verification")}
        >
          학생증 심사
        </button>
        <button
          type="button"
          className={tab === "report" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("report")}
        >
          신고 · 건의
        </button>
      </div>
      {tab === "verification" ? <VerificationTab /> : <ReportTab />}
    </div>
  );
}
