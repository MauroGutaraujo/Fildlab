export function ClienteIdentidad({ razonSocial, ruc }: { razonSocial?: string; ruc?: string }) {
  return (
    <div className="min-w-36 leading-tight">
      <span className="block max-w-64 font-semibold text-slate-900">{razonSocial || "Nombre no disponible"}</span>
      <span className="mt-1 block text-xs font-medium tracking-wide text-slate-500">RUC: {ruc || "No disponible"}</span>
    </div>
  );
}
