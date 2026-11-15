// Pure offline-queue logic for the simulated watch.
//
// The queue lives in localStorage (one key per astronaut). These functions do
// not touch the DOM or storage, so they can be tested with `node --test`.
//
// States:
//   pendiente -> waiting for a retry (network failure or offline)
//   revisar   -> the server rejected the data (4xx); the person must fix it
//   enviada   -> removed from the queue after a successful send

export const MAX_COLA = 20;
export const MAX_REINTENTO_MS = 30000;

export function nuevaEntrada(lectura) {
  return { lectura, estado: "pendiente", intentos: 0, siguiente: 0, error: null };
}

/** Adds a reading; the same lectura_id replaces the previous one. Keeps at most `max`. */
export function agregar(cola, lectura, max = MAX_COLA) {
  if (!lectura || !lectura.lectura_id) throw new Error("lectura_id is required");
  const sinDuplicado = (cola || []).filter((i) => i.lectura.lectura_id !== lectura.lectura_id);
  const siguiente = [...sinDuplicado, nuevaEntrada(lectura)];
  return siguiente.length > max ? siguiente.slice(siguiente.length - max) : siguiente;
}

export function quitar(cola, lecturaId) {
  return (cola || []).filter((i) => i.lectura.lectura_id !== lecturaId);
}

export function marcarRevisar(cola, lecturaId, error) {
  return (cola || []).map((i) => (i.lectura.lectura_id === lecturaId
    ? { ...i, estado: "revisar", error: String(error || "The server rejected this reading.") }
    : i));
}

export function marcarPendiente(cola, lecturaId, intentos, siguiente) {
  return (cola || []).map((i) => (i.lectura.lectura_id === lecturaId
    ? { ...i, estado: "pendiente", intentos, siguiente, error: null }
    : i));
}

/** Replaces the reading of an item that needs review, keeping its state. */
export function reemplazarLectura(cola, lecturaId, lectura) {
  return (cola || []).map((i) => (i.lectura.lectura_id === lecturaId
    ? { ...i, lectura: { ...lectura, lectura_id: lecturaId } }
    : i));
}

/** Exponential backoff: 1 s, 2 s, 4 s ... up to 30 s. */
export function siguienteEspera(intentos) {
  const n = Math.max(0, Number(intentos) || 0);
  return Math.min(MAX_REINTENTO_MS, 1000 * (2 ** n));
}

export function puedeReintentar(item, ahora = Date.now()) {
  return item.estado === "pendiente" && Number(item.siguiente || 0) <= ahora;
}

export function pendientes(cola) {
  return (cola || []).filter((i) => i.estado === "pendiente");
}

export function enRevision(cola) {
  return (cola || []).filter((i) => i.estado === "revisar");
}

export function serializar(cola) {
  return JSON.stringify(cola || []);
}

export function deserializar(texto) {
  try {
    const datos = JSON.parse(texto || "[]");
    if (!Array.isArray(datos)) return [];
    return datos
      .filter((i) => i && i.lectura && typeof i.lectura.lectura_id === "string")
      .map((i) => ({
        lectura: i.lectura,
        estado: i.estado === "revisar" ? "revisar" : "pendiente",
        intentos: Number(i.intentos) || 0,
        siguiente: Number(i.siguiente) || 0,
        error: i.error || null,
      }));
  } catch {
    return [];
  }
}
