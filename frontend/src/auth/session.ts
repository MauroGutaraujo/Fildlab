// sessionStorage (no localStorage): el token no sobrevive al cierre de la pestaña,
// lo que reduce la ventana de exposición en el equipo compartido de Gerencia.
const KEY = "fildlab.token";

export function getToken(): string | null {
  try {
    return sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    sessionStorage.setItem(KEY, token);
  } catch {
    /* almacenamiento bloqueado: la sesión vivirá solo en memoria de la página */
  }
}

export function clearToken(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    /* nada que limpiar */
  }
}
