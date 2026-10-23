/** JWT de prueba: estructura y claims reales; el cliente no verifica firmas. */
export function tokenDeTecnico(tecnicoId = 1, exp = Math.floor(Date.now() / 1000) + 3600): string {
  const codificar = (value: unknown) => btoa(JSON.stringify(value)).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
  return `${codificar({ alg: "HS256", typ: "JWT" })}.${codificar({ sub: String(tecnicoId), exp })}.c2ln`;
}
