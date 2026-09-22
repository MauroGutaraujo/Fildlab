// Duplicado deliberado de frontend/src/api/client.ts (decisión A del spec de 3.2): la PWA
// no comparte paquete con el panel administrativo, para mantener su bundle desacoplado.
import { obtenerToken } from "../auth/session";

const BASE = `${import.meta.env.VITE_API_URL ?? ""}/api/v1`;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export type ApiInit = Omit<RequestInit, "body"> & { body?: unknown };

function mensaje(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => {
        const campo = (d.loc ?? []).filter((p) => p !== "body").join(".");
        return campo ? `${campo}: ${d.msg}` : (d.msg ?? "");
      })
      .join("; ");
  }
  return fallback;
}

export async function apiFetch<T = unknown>(path: string, init: ApiInit = {}): Promise<T> {
  const { body, headers: h, ...rest } = init;
  const headers = new Headers(h);
  const token = await obtenerToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (body !== undefined) headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...rest,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "No se pudo conectar con el servidor");
  }

  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new ApiError(res.status, mensaje(data?.detail, `Error ${res.status}`));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
