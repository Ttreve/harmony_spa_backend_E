import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import Landing from "./pages/Landing.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Users from "./pages/Users.jsx";
import Profile from "./pages/Profile.jsx";

const homes = [
  ["superadmin", "SUPER_ADMIN"],
  ["admin", "ADMIN"],
  ["esteticista", "ESTETICISTA"],
  ["cliente", "CLIENTE"],
];

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        {homes.map(([path, role]) => (
          <Route
            key={path}
            path={`/${path}/dashboard`}
            element={
              <ProtectedRoute roles={[role]}>
                <Dashboard />
              </ProtectedRoute>
            }
          />
        ))}
        <Route
          path="/superadmin/usuarios"
          element={
            <ProtectedRoute roles={["SUPER_ADMIN"]}>
              <Users />
            </ProtectedRoute>
          }
        />
        <Route path="/perfil" element={<Profile />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
