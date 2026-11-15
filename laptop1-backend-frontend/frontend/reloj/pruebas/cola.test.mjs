import test from "node:test";
import assert from "node:assert/strict";

import {
  MAX_COLA, agregar, deserializar, enRevision, marcarPendiente, marcarRevisar,
  pendientes, puedeReintentar, quitar, reemplazarLectura, serializar, siguienteEspera,
} from "../cola.js";

function lectura(id, indicadores = { fc_reposo: 60 }) {
  return {
    lectura_id: id, astronauta_id: "AST-01", capturado_en: "2026-11-15T16:05:00Z",
    origen: "reloj-simulado", indicadores,
  };
}

test("agregar guarda la lectura y no duplica el mismo lectura_id", () => {
  let cola = agregar([], lectura("a"));
  cola = agregar(cola, lectura("a", { fc_reposo: 61 }));
  assert.equal(cola.length, 1);
  assert.equal(cola[0].lectura.indicadores.fc_reposo, 61);
  assert.equal(cola[0].estado, "pendiente");
});

test("la cola respeta el máximo y descarta la lectura más antigua", () => {
  let cola = [];
  for (let i = 0; i < MAX_COLA + 3; i += 1) cola = agregar(cola, lectura(`l${i}`));
  assert.equal(cola.length, MAX_COLA);
  assert.equal(cola[0].lectura.lectura_id, "l3");
  assert.equal(cola.at(-1).lectura.lectura_id, `l${MAX_COLA + 2}`);
});

test("quitar y marcar revisar cambian solo la lectura indicada", () => {
  let cola = agregar(agregar([], lectura("a")), lectura("b"));
  cola = marcarRevisar(cola, "a", "Sleep must be between 0 and 14.");
  assert.equal(enRevision(cola).length, 1);
  assert.match(cola[0].error, /Sleep/);
  assert.equal(pendientes(cola).length, 1);
  cola = quitar(cola, "a");
  assert.deepEqual(cola.map((i) => i.lectura.lectura_id), ["b"]);
});

test("el reintento crece 1, 2, 4 ... hasta 30 segundos", () => {
  assert.equal(siguienteEspera(0), 1000);
  assert.equal(siguienteEspera(1), 2000);
  assert.equal(siguienteEspera(2), 4000);
  assert.equal(siguienteEspera(10), 30000);
});

test("solo se reintenta cuando toca y sigue pendiente", () => {
  let cola = agregar([], lectura("a"));
  cola = marcarPendiente(cola, "a", 1, 5000);
  assert.equal(puedeReintentar(cola[0], 4999), false);
  assert.equal(puedeReintentar(cola[0], 5000), true);
  cola = marcarRevisar(cola, "a", "bad value");
  assert.equal(puedeReintentar(cola[0], 99999), false);
});

test("reemplazar una lectura en revisión conserva su lectura_id", () => {
  let cola = marcarRevisar(agregar([], lectura("a")), "a", "bad value");
  cola = reemplazarLectura(cola, "a", lectura("otro-id", { fc_reposo: 62 }));
  assert.equal(cola[0].lectura.lectura_id, "a");
  assert.equal(cola[0].lectura.indicadores.fc_reposo, 62);
});

test("la cola sobrevive a la serialización y los datos corruptos no rompen", () => {
  const cola = agregar([], lectura("a"));
  assert.deepEqual(deserializar(serializar(cola)), cola);
  assert.deepEqual(deserializar("not json"), []);
  assert.deepEqual(deserializar("{}"), []);
});
