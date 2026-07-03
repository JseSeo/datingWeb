import { NavLink } from "react-router-dom";
import styles from "./TopNav.module.css";

const links = [
  { to: "/home", label: "홈" },
  { to: "/game", label: "게임" },
  { to: "/mypage", label: "마이페이지" },
];

export default function TopNav() {
  return (
    <nav className={styles.nav}>
      {links.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            isActive ? `${styles.link} ${styles.active}` : styles.link
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
