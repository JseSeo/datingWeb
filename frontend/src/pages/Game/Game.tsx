import { useState } from "react";
import OjakgyoTab from "./OjakgyoTab";
import RedThreadTab from "./RedThreadTab";
import styles from "./Game.module.css";

type Tab = "ojakgyo" | "redthread";

export default function Game() {
  const [tab, setTab] = useState<Tab>("ojakgyo");

  return (
    <div>
      <div className={styles.tabs} role="tablist">
        <button
          type="button"
          role="tab"
          id="tab-ojakgyo"
          aria-selected={tab === "ojakgyo"}
          className={tab === "ojakgyo" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("ojakgyo")}
        >
          오작교
        </button>
        <button
          type="button"
          role="tab"
          id="tab-redthread"
          aria-selected={tab === "redthread"}
          className={tab === "redthread" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("redthread")}
        >
          붉은실
        </button>
      </div>
      {tab === "ojakgyo" ? (
        <div role="tabpanel" aria-labelledby="tab-ojakgyo" tabIndex={0}>
          <OjakgyoTab />
        </div>
      ) : (
        <div role="tabpanel" aria-labelledby="tab-redthread" tabIndex={0}>
          <RedThreadTab />
        </div>
      )}
    </div>
  );
}
