import { createContext, useContext, useEffect, useState } from "react";
import * as api from "../api.js";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export const ROLE_LABEL = {
  SUPER_ADMIN: "Super Administrador",
  ADMIN: "Administrador",
  ESTETICISTA: "Esteticista",
  CLIENTE: "Cliente",
};

export const HOME = {
  SUPER_ADMIN: "/superadmin/dashboard",
  ADMIN: "/admin/dashboard",
  ESTETICISTA: "/esteticista/dashboard",
  CLIENTE: "/cliente/dashboard",
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  const clear = () => {
    api.clearToken();
    setUser(null);
  };

  useEffect(() => {
    api.setUnauthorizedHandler(clear);
    if (!api.getToken()) return setReady(true);
    api.me().then(setUser).catch(clear).finally(() => setReady(true));
  }, []);

  const login = async (email, password) => {
    const data = await api.login(email, password);
    api.setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch {}
    clear();
  };

  return (
    <AuthContext.Provider value={{ user, setUser, ready, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
