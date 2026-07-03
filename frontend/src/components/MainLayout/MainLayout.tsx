import { Outlet } from "react-router-dom";
import TopNav from "../TopNav/TopNav";
import styles from "./MainLayout.module.css";

export default function MainLayout() {
  return (
    <>
      <TopNav />
      <main className={styles.main}>
        <Outlet />
      </main>
    </>
  );
}
