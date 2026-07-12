import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../lib/auth";

interface Props {
  children: ReactNode;
  requireStatus?: "pending" | "active";
  requireAdmin?: boolean;
}

export function ProtectedRoute({ children, requireStatus, requireAdmin }: Props) {
  const { user, loading } = useAuth();

  if (loading) return <p>불러오는 중...</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.status === "suspended") return <Navigate to="/login" replace />;

  if (requireAdmin && !user.is_admin) {
    return <Navigate to={user.status === "active" ? "/home" : "/pending"} replace />;
  }

  // 요구 status와 다르면 본인 status의 목적지로 보정
  if (requireStatus && user.status !== requireStatus) {
    return <Navigate to={user.status === "active" ? "/home" : "/pending"} replace />;
  }
  return <>{children}</>;
}
