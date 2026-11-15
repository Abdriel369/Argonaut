// Smoke test for the crew views: they must render from the contract examples
// without throwing and without leaking "undefined" into the HTML.
//
//   node laptop1-backend-frontend/frontend/reloj/pruebas/vistas.script.mjs

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { vistaTripulacion, vistaDetalleEquipo } from "../../js/vistas.js";

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const RAIZ = path.resolve(AQUI, "../../../..");
const leer = (nombre) => JSON.parse(
  fs.readFileSync(path.join(RAIZ, "contratos", "ejemplos", nombre), "utf8"));

const trip = leer("tripulacion.json");
const det = leer("detalle_tripulacion.json");
const html = vistaTripulacion(trip, "all");
const detalle = vistaDetalleEquipo(det);
if (!html.includes("Crew") || !html.includes("Mateo")) throw new Error("crew view incomplete");
if (!detalle.includes("Mateo") || !detalle.includes("Indicators")) throw new Error("detail incomplete");
if (html.includes("undefined") || detalle.includes("undefined")) throw new Error("undefined leaked into HTML");
console.log("vistas: crew y detalle renderizan sin errores", html.length, detalle.length);
