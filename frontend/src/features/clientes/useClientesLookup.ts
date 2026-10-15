import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../../api/client";

export type ClienteResumen = { ruc: string; razon_social: string };

function normalizarRazonSocial(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es-PE").replace(/[^a-z0-9]+/g, " ").trim();
}

export function useClientesLookup() {
  const query = useQuery({
    queryKey: ["clientes"],
    queryFn: () => apiFetch<ClienteResumen[]>("/clientes"),
  });
  const porRuc = new Map((query.data ?? []).map((cliente) => [cliente.ruc, cliente]));
  const porRazonSocial = new Map<string, ClienteResumen | null>();
  for (const cliente of query.data ?? []) {
    const key = normalizarRazonSocial(cliente.razon_social);
    if (porRazonSocial.has(key)) porRazonSocial.set(key, null);
    else porRazonSocial.set(key, cliente);
  }

  return {
    isLoading: query.isLoading,
    porRuc,
    porRazonSocial: (razonSocial: string) => porRazonSocial.get(normalizarRazonSocial(razonSocial)) ?? undefined,
  };
}
