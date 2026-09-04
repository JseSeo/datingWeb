import { useState } from "react";
import VerificationTab from "./VerificationTab";
import ReportTab from "./ReportTab";
import RoundTab from "./RoundTab";
import UniversityWeightTab from "./UniversityWeightTab";
import UniversityTab from "./UniversityTab";
import styles from "./Admin.module.css";

type Tab = "verification" | "report" | "round" | "weight" | "university";

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
        <button
          type="button"
          role="tab"
          id="tab-weight"
          aria-selected={tab === "weight"}
          className={tab === "weight" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("weight")}
        >
          대학 가중치
        </button>
        <button
          type="button"
          role="tab"
          id="tab-university"
          aria-selected={tab === "university"}
          className={tab === "university" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("university")}
        >
          대학 목록
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
      {tab === "weight" && (
        <div role="tabpanel" aria-labelledby="tab-weight" tabIndex={0}>
          <UniversityWeightTab />
        </div>
      )}
      {tab === "university" && (
        <div role="tabpanel" aria-labelledby="tab-university" tabIndex={0}>
          <UniversityTab />
        </div>
      )}
    </div>
  );
}
