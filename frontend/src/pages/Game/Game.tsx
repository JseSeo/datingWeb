import { useState } from "react";
import OjakgyoTab from "./OjakgyoTab";
import RedThreadTab from "./RedThreadTab";
import styles from "./Game.module.css";

type Tab = "ojakgyo" | "redthread";

export default function Game() {
  const [tab, setTab] = useState<Tab>("ojakgyo");

  return (
    <div>
      <div className={styles.tabs}>
        <button
          type="button"
          className={tab === "ojakgyo" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("ojakgyo")}
        >
          오작교
        </button>
        <button
          type="button"
          className={tab === "redthread" ? `${styles.tab} ${styles.tabActive}` : styles.tab}
          onClick={() => setTab("redthread")}
        >
          붉은실
        </button>
      </div>
      {tab === "ojakgyo" ? <OjakgyoTab /> : <RedThreadTab />}
    </div>
  );
}
