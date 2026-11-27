import { useState } from "react";
import * as api from "../api.js";

const empty = {
  first_name: "", last_name: "", email: "", phone: "", password: "", role: "CLIENTE",
  birth_date: "", address: "", emergency_contact_name: "", emergency_contact_phone: "",
  job_title: "", specialty: "",
};
const nn = (v) => (v === "" ? null : v);

export default function UserForm({ user, onClose, onDone }) {
  const isEdit = Boolean(user.id);
  const [f, setF] = useState(isEdit ? { ...empty, ...user, phone: user.phone || "" } : empty);
  const [error, setError] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      if (isEdit) {
        await api.updateUser(user.id, {
          first_name: f.first_name, last_name: f.last_name, email: f.email, phone: nn(f.phone),
        });
      } else {
        const body = {
          first_name: f.first_name, last_name: f.last_name, email: f.email,
          phone: nn(f.phone), password: f.password, role: f.role,
        };
        if (f.role === "CLIENTE") {
          body.client_profile = {
            birth_date: nn(f.birth_date),
            address: nn(f.address),
            emergency_contact_name: nn(f.emergency_contact_name),
            emergency_contact_phone: nn(f.emergency_contact_phone),
          };
        } else {
          body.employee_profile = { job_title: f.job_title, specialty: nn(f.specialty) };
        }
        await api.createUser(body);
      }
      onDone();
    } catch (err) {
      setError(err.message);
    }
  };

  const field = (label, k, extra = {}) => (
    <label className="field">
      <span>{label}</span>
      <input value={f[k]} onChange={set(k)} {...extra} />
    </label>
  );

  return (
    <div className="overlay" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <h2>{isEdit ? "Editar usuario" : "Nuevo usuario"}</h2>
        <div className="two">
          {field("Nombre", "first_name", { required: true, minLength: 2 })}
          {field("Apellido", "last_name", { required: true, minLength: 2 })}
        </div>
        {field("Correo electrónico", "email", { type: "email", required: true })}
        {field("Teléfono", "phone")}

        {!isEdit && (
          <>
            {field("Contraseña", "password", { type: "password", required: true, minLength: 12 })}
            <label className="field">
              <span>Rol</span>
              <select value={f.role} onChange={set("role")}>
                <option value="CLIENTE">Cliente</option>
                <option value="ESTETICISTA">Esteticista</option>
                <option value="ADMIN">Administrador</option>
              </select>
            </label>

            {f.role === "CLIENTE" ? (
              <>
                {field("Fecha de nacimiento", "birth_date", { type: "date" })}
                {field("Dirección", "address")}
                <div className="two">
                  {field("Contacto de emergencia", "emergency_contact_name")}
                  {field("Teléfono de emergencia", "emergency_contact_phone")}
                </div>
              </>
            ) : (
              <div className="two">
                {field("Cargo", "job_title", { required: true, minLength: 2 })}
                {field("Especialidad", "specialty")}
              </div>
            )}
          </>
        )}

        {error && <p className="alert">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="pill" onClick={onClose}>
            Cancelar
          </button>
          <button className="btn">Guardar</button>
        </div>
      </form>
    </div>
  );
}
