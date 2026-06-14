import { Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing/Landing";
import Register from "./pages/Register/Register";
import Login from "./pages/Login/Login";
import Pending from "./pages/Pending/Pending";
import Home from "./pages/Home/Home";
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
      <Route
        path="/home"
        element={
          <ProtectedRoute requireStatus="active">
            <Home />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
