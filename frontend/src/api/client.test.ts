import { describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch } from "./client";
import { getToken, setToken } from "../auth/session";
import { mockApi } from "../test/utils";

describe("apiFetch", () => {
  it("adjunta el token Bearer cuando hay sesión", async () => {
    setToken("abc");
    const f = mockApi([{ path: "/api/v1/clientes", body: [] }]);
    await apiFetch("/clientes");
    const headers = new Headers((f.mock.calls[0][1] as RequestInit).headers);
    expect(headers.get("Authorization")).toBe("Bearer abc");
  });

  it("no envía Authorization sin sesión", async () => {
    const f = mockApi([{ path: "/api/v1/clientes", body: [] }]);
    await apiFetch("/clientes");
    const headers = new Headers((f.mock.calls[0][1] as RequestInit | undefined)?.headers);
    expect(headers.has("Authorization")).toBe(false);
  });

  it("serializa el body a JSON", async () => {
    const f = mockApi([{ method: "POST", path: "/api/v1/x", body: {} }]);
    await apiFetch("/x", { method: "POST", body: { a: 1 } });
    const init = f.mock.calls[0][1] as RequestInit;
    expect(init.body).toBe('{"a":1}');
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });

  it("ante 401 limpia la sesión y avisa", async () => {
    setToken("vencido");
    const avisos = vi.fn();
    window.addEventListener("auth:unauthorized", avisos);
    mockApi([{ path: "/api/v1/clientes", status: 401, body: { detail: "No autenticado" } }]);
    await expect(apiFetch("/clientes")).rejects.toBeInstanceOf(ApiError);
    expect(getToken()).toBeNull();
    expect(avisos).toHaveBeenCalled();
    window.removeEventListener("auth:unauthorized", avisos);
  });

  it("expone el detalle del backend en ApiError (409)", async () => {
    mockApi([{ method: "POST", path: "/api/v1/clientes", status: 409, body: { detail: "Ya existe un cliente con ese RUC" } }]);
    await expect(apiFetch("/clientes", { method: "POST", body: {} })).rejects.toMatchObject({
      status: 409,
      message: "Ya existe un cliente con ese RUC",
    });
  });

  it("aplana los errores 422 de validación en un mensaje legible", async () => {
    mockApi([{ method: "POST", path: "/api/v1/clientes", status: 422, body: { detail: [{ loc: ["body", "ruc"], msg: "String should match pattern" }] } }]);
    await expect(apiFetch("/clientes", { method: "POST", body: {} })).rejects.toMatchObject({ status: 422 });
    await apiFetch("/clientes", { method: "POST", body: {} }).catch((e: ApiError) => expect(e.message).toContain("ruc"));
  });

  it("devuelve undefined en 204", async () => {
    mockApi([{ method: "DELETE", path: "/api/v1/clientes/1", status: 204 }]);
    await expect(apiFetch("/clientes/1", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("un fallo de red produce ApiError con status 0", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(apiFetch("/clientes")).rejects.toMatchObject({ status: 0 });
  });
});

describe("token de sesión", () => {
  it("vive en sessionStorage, no en localStorage", () => {
    setToken("t");
    expect(sessionStorage.getItem("fildlab.token")).toBe("t");
    expect(localStorage.getItem("fildlab.token")).toBeNull();
  });
});
