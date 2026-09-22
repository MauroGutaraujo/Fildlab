import { describe, expect, it, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useGps } from "./useGps";

describe("useGps", () => {
  it("permiso denegado deja un mensaje claro, no crashea", async () => {
    const getCurrentPosition = vi.fn((_ok, err) => err({ code: 1, message: "denegado" }));
    vi.stubGlobal("navigator", { geolocation: { getCurrentPosition } });
    const { result } = renderHook(() => useGps());
    act(() => result.current.solicitar());
    await waitFor(() => expect(result.current.error).toMatch(/permiso/i));
    expect(result.current.lat).toBeNull();
  });

  it("exito guarda lat/lng", async () => {
    const getCurrentPosition = vi.fn((ok) => ok({ coords: { latitude: -8.11, longitude: -79.02 } }));
    vi.stubGlobal("navigator", { geolocation: { getCurrentPosition } });
    const { result } = renderHook(() => useGps());
    act(() => result.current.solicitar());
    await waitFor(() => expect(result.current.lat).toBe(-8.11));
  });

  it("sin soporte de geolocalizacion en el navegador, error claro", async () => {
    vi.stubGlobal("navigator", {});
    const { result } = renderHook(() => useGps());
    act(() => result.current.solicitar());
    await waitFor(() => expect(result.current.error).toMatch(/no disponible/i));
  });
});
