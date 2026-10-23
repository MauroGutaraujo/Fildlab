import "fake-indexeddb/auto";
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import { db } from "../db/dexie";

afterEach(async () => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  // Cada test parte de una PWA "limpia": sin esto, datos de un archivo de test
  // se filtran a los siguientes (fake-indexeddb persiste entre tests de un mismo proceso).
  await Promise.all([db.catalogoLocal.clear(), db.ordenesLocal.clear(), db.stockMovilLocal.clear(), db.sesion.clear(), db.stockPorTecnico.clear(), db.borradoresOrden.clear()]);
});
