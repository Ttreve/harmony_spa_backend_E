import { Link } from "react-router-dom";
import { ROLE_LABEL, useAuth } from "../context/AuthContext.jsx";
import { Shield } from "../components/Icons.jsx";

export default function Dashboard() {
  const { user } = useAuth();
  const isSuper = user.role === "SUPER_ADMIN";

  return (
    <>
      <section className="hero">
        <span className="eyebrow">
          <Shield width={14} height={14} /> Panel {ROLE_LABEL[user.role]}
        </span>
        <h1>¡Bienvenido, {user.first_name}!</h1>
        <p className="sub">Has iniciado sesión correctamente en Harmony Spa.</p>
        <span className="chip">
          <Shield width={14} height={14} /> {ROLE_LABEL[user.role]}
        </span>
      </section>

      <section className="panel">
        <h2>Tu espacio de {isSuper ? "administración" : "trabajo"}</h2>
        {isSuper ? (
          <>
            <p className="sub">Gestiona las cuentas de administradores, esteticistas y clientes.</p>
            <Link to="/superadmin/usuarios" className="btn">
              Gestionar usuarios
            </Link>
          </>
        ) : (
          <p className="sub">En próximas etapas, aquí encontrarás las herramientas de tu rol.</p>
        )}
      </section>
    </>
  );
}
