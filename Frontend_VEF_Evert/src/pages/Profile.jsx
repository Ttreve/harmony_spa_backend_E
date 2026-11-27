import { useState } from "react";
import * as api from "../api.js";
import { ROLE_LABEL, useAuth } from "../context/AuthContext.jsx";

export default function Profile() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({
    first_name: user.first_name,
    last_name: user.last_name,
    phone: user.phone || "",
  });
  const [pw, setPw] = useState({ current: "", next: "" });
  const [s1, setS1] = useState({});
  const [s2, setS2] = useState({});

  const saveProfile = async (e) => {
    e.preventDefault();
    setS1({});
    try {
      setUser(await api.updateMe({ ...form, phone: form.phone || null }));
      setS1({ ok: "Perfil actualizado" });
    } catch (err) {
      setS1({ error: err.message });
    }
  };

  const savePassword = async (e) => {
    e.preventDefault();
    setS2({});
    try {
      const r = await api.changePassword(pw.current, pw.next);
      setPw({ current: "", next: "" });
      setS2({ ok: r.message });
    } catch (err) {
      setS2({ error: err.message });
    }
  };

  return (
    <>
      <h1 className="title">Mi perfil</h1>
      <p className="sub">
        {user.email} · {ROLE_LABEL[user.role]}
      </p>

      <div className="cols">
        <form className="panel" onSubmit={saveProfile}>
          <h2>Datos personales</h2>
          <label className="field">
            <span>Nombre</span>
            <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} required minLength={2} />
          </label>
          <label className="field">
            <span>Apellido</span>
            <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} required minLength={2} />
          </label>
          <label className="field">
            <span>Teléfono</span>
            <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </label>
          {s1.error && <p className="alert">{s1.error}</p>}
          {s1.ok && <p className="success">{s1.ok}</p>}
          <button className="btn">Guardar cambios</button>
        </form>

        <form className="panel" onSubmit={savePassword}>
          <h2>Cambiar contraseña</h2>
          <label className="field">
            <span>Contraseña actual</span>
            <input type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} required />
          </label>
          <label className="field">
            <span>Nueva contraseña</span>
            <input type="password" autoComplete="new-password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} required minLength={12} />
          </label>
          <p className="hint">12 a 128 caracteres, con al menos una letra y un número.</p>
          {s2.error && <p className="alert">{s2.error}</p>}
          {s2.ok && <p className="success">{s2.ok}</p>}
          <button className="btn">Actualizar contraseña</button>
        </form>
      </div>
    </>
  );
}
