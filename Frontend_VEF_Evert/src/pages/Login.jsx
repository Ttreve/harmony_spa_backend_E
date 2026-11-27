import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { HOME, useAuth } from "../context/AuthContext.jsx";
import Logo from "../components/Logo.jsx";
import { Eye } from "../components/Icons.jsx";

export default function Login() {
  const { user, ready, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (ready && user) return <Navigate to={HOME[user.role]} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const u = await login(email, password);
      navigate(HOME[u.role], { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={submit}>
        <Logo tag="Bienvenido de nuevo" />
        <h1>Iniciar sesión</h1>
        <p className="sub">Ingresa tus credenciales para continuar.</p>

        <label className="field">
          <span>Correo electrónico</span>
          <input
            type="email"
            autoComplete="email"
            placeholder="Ingresa tu correo"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />
        </label>

        <label className="field">
          <span>Contraseña</span>
          <div className="input-icon">
            <input
              type={show ? "text" : "password"}
              autoComplete="current-password"
              placeholder="Ingresa tu contraseña"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button type="button" className="ghost" onClick={() => setShow(!show)} aria-label="Mostrar contraseña">
              <Eye off={show} />
            </button>
          </div>
        </label>

        {error && <p className="alert">{error}</p>}

        <button className="btn block" disabled={loading}>
          {loading ? "Ingresando…" : "Ingresar"}
        </button>
        <Link to="/" className="back">
          ← Volver a la página principal
        </Link>
      </form>
    </div>
  );
}
