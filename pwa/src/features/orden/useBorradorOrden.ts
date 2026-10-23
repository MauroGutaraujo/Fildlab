import { useCallback, useEffect, useRef, useState } from "react";
import type { BorradorOrden } from "../../db/dexie";
import { abrirBorrador, guardarBorrador, ConflictoBorradorError } from "../../db/ordenes";

export function useBorradorOrden(tecnicoId: number, serie: string, contratoId: number) {
  const [borrador, setBorrador] = useState<BorradorOrden | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflicto, setConflicto] = useState(false);
  const actual = useRef<BorradorOrden | null>(null);
  const cola = useRef<Promise<void>>(Promise.resolve());
  const revision = useRef(0);
  const revisionGuardada = useRef(0);
  const sinGuardar = useRef(false);
  const activo = useRef(false);
  const bloqueado = useRef(false);

  useEffect(() => {
    activo.current = true;
    let cancelado = false;
    abrirBorrador(tecnicoId, serie, contratoId).then((b) => {
      if (cancelado) return;
      actual.current = b;
      revisionGuardada.current = b.revision;
      setBorrador(b);
    }).catch(() => {
      if (!cancelado) setError("No se pudo abrir el borrador. Verifica el almacenamiento y vuelve a abrir el equipo.");
    });
    return () => { cancelado = true; activo.current = false; };
  }, [tecnicoId, serie, contratoId]);

  useEffect(() => {
    const proteger = (event: Event) => {
      if (!sinGuardar.current && !bloqueado.current) return;
      event.preventDefault();
      if (event.type === "beforeunload") (event as BeforeUnloadEvent).returnValue = "";
    };
    window.addEventListener("beforeunload", proteger);
    window.addEventListener("fildlab:antes-navegar", proteger);
    return () => {
      window.removeEventListener("beforeunload", proteger);
      window.removeEventListener("fildlab:antes-navegar", proteger);
    };
  }, []);

  const cambiar = useCallback((cambios: Partial<BorradorOrden>) => {
    if (!actual.current || bloqueado.current) return;
    const nuevo = { ...actual.current, ...cambios };
    actual.current = nuevo;
    setBorrador(nuevo);
    sinGuardar.current = true;
    setGuardando(true);
    setError(null);
    const numero = ++revision.current;
    const tarea = cola.current.catch(() => {}).then(async () => {
      const guardado = await guardarBorrador({ ...nuevo, revision: revisionGuardada.current });
      revisionGuardada.current = guardado.revision;
      if (actual.current) actual.current = { ...actual.current, revision: guardado.revision };
      if (activo.current) setBorrador(actual.current);
    });
    cola.current = tarea;
    void tarea.then(() => {
      if (numero !== revision.current) return;
      sinGuardar.current = false;
      if (activo.current) setGuardando(false);
    }, (e: unknown) => {
      if (numero !== revision.current || !activo.current) return;
      setGuardando(false);
      setConflicto(e instanceof ConflictoBorradorError);
      setError(`No se pudo guardar el borrador. ${e instanceof ConflictoBorradorError ? "Hay una versión más reciente en otra pestaña. Recupera esa versión para continuar." : "No salgas de esta pantalla; libera espacio y reintenta."}`);
    });
  }, []);

  async function esperar(): Promise<BorradorOrden> {
    await cola.current;
    if (!actual.current) throw new Error("El borrador aún no está disponible");
    return actual.current;
  }

  async function recuperar() {
    bloqueado.current = true;
    setGuardando(true);
    try {
      await cola.current.catch(() => {});
      const guardado = await abrirBorrador(tecnicoId, serie, contratoId);
      actual.current = guardado;
      revisionGuardada.current = guardado.revision;
      cola.current = Promise.resolve();
      sinGuardar.current = false;
      setBorrador(guardado);
      setError(null);
      setConflicto(false);
    } catch {
      setError("No se pudo recuperar el borrador. Reintenta cuando el almacenamiento esté disponible.");
    } finally { bloqueado.current = false; setGuardando(false); }
  }

  return { borrador, guardando, error, conflicto, recuperar, cambiar, esperar, bloqueado,
    obtenerActual: () => actual.current,
    reintentar: () => cambiar({}),
    permitirSalida: () => { sinGuardar.current = false; bloqueado.current = false; },
  };
}
