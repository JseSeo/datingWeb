import type { ButtonHTMLAttributes } from "react";
import styles from "./Button.module.css";

export function Button({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`${styles.button} ${className ?? ""}`} {...props} />;
}
