import { Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing/Landing";
import Register from "./pages/Register/Register";
import Login from "./pages/Login/Login";
import Pending from "./pages/Pending/Pending";
import Home from "./pages/Home/Home";
import Game from "./pages/Game/Game";
import MyPage from "./pages/MyPage/MyPage";
import Profile from "./pages/Profile/Profile";
import MainLayout from "./components/MainLayout/MainLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/register" element={<Register />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/pending"
        element={
          <ProtectedRoute requireStatus="pending">
            <Pending />
          </ProtectedRoute>
        }
      />
      <Route element={<MainLayout />}>
        <Route
          path="/home"
          element={
            <ProtectedRoute requireStatus="active">
              <Home />
            </ProtectedRoute>
          }
        />
        <Route
          path="/game"
          element={
            <ProtectedRoute requireStatus="active">
              <Game />
            </ProtectedRoute>
          }
        />
        <Route
          path="/mypage"
          element={
            <ProtectedRoute>
              <MyPage />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
