import { Link } from "react-router-dom";
import Logo from "../components/Logo.jsx";

export default function Landing() {
  return (
    <div className="landing">
      <header className="topbar">
        <div className="topbar-in">
          <Logo />
          <span className="grow" />
          <Link to="/login" className="pill">
            Iniciar sesión
          </Link>
        </div>
      </header>
      <section className="landing-hero">
        <span className="eyebrow">Bienestar y relajación</span>
        <h1>Un espacio para volver a ti</h1>
        <p className="lead">Tratamientos, calma y cuidado en un solo lugar.</p>
        <Link to="/login" className="btn">
          Ingresar
        </Link>
      </section>
    </div>
  );
}
