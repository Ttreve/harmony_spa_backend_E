import { Link, NavLink, Outlet } from "react-router-dom";
import { HOME, useAuth } from "../context/AuthContext.jsx";
import Logo from "./Logo.jsx";
import { Logout } from "./Icons.jsx";

export default function Layout() {
  const { user, logout } = useAuth();
  const isSuper = user.role === "SUPER_ADMIN";

  return (
    <div className="page">
      <header className="topbar">
        <div className="topbar-in">
          <Link to={HOME[user.role]} className="plain">
            <Logo sparkle />
          </Link>
          <nav className="nav">
            <NavLink to={HOME[user.role]}>Inicio</NavLink>
            {isSuper && <NavLink to="/superadmin/usuarios">Usuarios</NavLink>}
            <NavLink to="/perfil">Mi perfil</NavLink>
          </nav>
          <button className="pill" onClick={logout}>
            <Logout /> Cerrar sesión
          </button>
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </div>
  );
}
