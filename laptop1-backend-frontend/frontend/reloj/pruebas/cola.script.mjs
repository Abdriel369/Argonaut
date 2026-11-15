// Plain Node script for the pure queue logic.
//
// `node --test` spawns a child process, which the Windows file sandbox blocks
// with EPERM. This script does not spawn anything, so it also runs there:
//
//   node laptop1-backend-frontend/frontend/reloj/pruebas/cola.script.mjs
//
// The equivalent `node --test` file lives next to it for machines without that
// restriction.

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

let cola = agregar([], lectura("a"));
cola = agregar(cola, lectura("a", { fc_reposo: 61 }));
assert.equal(cola.length, 1);
assert.equal(cola[0].lectura.indicadores.fc_reposo, 61);

cola = [];
for (let i = 0; i < MAX_COLA + 3; i += 1) cola = agregar(cola, lectura(`l${i}`));
assert.equal(cola.length, MAX_COLA);
assert.equal(cola[0].lectura.lectura_id, "l3");
assert.equal(cola.at(-1).lectura.lectura_id, `l${MAX_COLA + 2}`);

let otra = agregar(agregar([], lectura("a")), lectura("b"));
otra = marcarRevisar(otra, "a", "Sleep must be between 0 and 14.");
assert.equal(enRevision(otra).length, 1);
assert.equal(pendientes(otra).length, 1);
otra = quitar(otra, "a");
assert.deepEqual(otra.map((i) => i.lectura.lectura_id), ["b"]);

assert.equal(siguienteEspera(0), 1000);
assert.equal(siguienteEspera(1), 2000);
assert.equal(siguienteEspera(2), 4000);
assert.equal(siguienteEspera(10), 30000);

let reintento = agregar([], lectura("r"));
reintento = marcarPendiente(reintento, "r", 1, 5000);
assert.equal(puedeReintentar(reintento[0], 4999), false);
assert.equal(puedeReintentar(reintento[0], 5000), true);

let revision = marcarRevisar(agregar([], lectura("a")), "a", "bad value");
revision = reemplazarLectura(revision, "a", lectura("otro-id", { fc_reposo: 62 }));
assert.equal(revision[0].lectura.lectura_id, "a");
assert.equal(revision[0].lectura.indicadores.fc_reposo, 62);

assert.deepEqual(deserializar(serializar(cola)), cola);
assert.deepEqual(deserializar("not json"), []);
assert.deepEqual(deserializar("{}"), []);

console.log("cola: todas las comprobaciones pasaron");
