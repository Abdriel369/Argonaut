"""Migración de una base de un solo astronauta al esquema multiastronauta."""

import json
import sqlite3

from backend.ajustes import Ajustes
from backend.bd import BaseDatos
from backend.cliente_orquestador import ClienteOrquestador
from backend.servicio import Servicio

ESQUEMA_VIEJO = """
CREATE TABLE estado (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE registros (
    dia INTEGER PRIMARY KEY, indicadores TEXT NOT NULL, manuales TEXT NOT NULL DEFAULT '[]',
    actualizado TEXT NOT NULL);
CREATE TABLE informes (
    id TEXT PRIMARY KEY, dia INTEGER NOT NULL, contenido TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente', creado TEXT NOT NULL, enviado TEXT);
CREATE TABLE protocolo_pasos (
    dia INTEGER NOT NULL, alerta_id TEXT NOT NULL, paso_id TEXT NOT NULL, hecho INTEGER NOT NULL,
    actualizado TEXT NOT NULL, PRIMARY KEY (dia, alerta_id, paso_id));
"""


def _base_vieja(ruta):
    conexion = sqlite3.connect(ruta)
    conexion.executescript(ESQUEMA_VIEJO)
    conexion.execute(
        "INSERT INTO registros (dia, indicadores, manuales, actualizado) VALUES (?, ?, ?, ?)",
        (1, json.dumps({"sueno_h": 6.6, "animo": 3}), json.dumps(["sueno_h"]), "2026-11-10T00:00:00+00:00"))
    conexion.execute(
        "INSERT INTO informes (id, dia, contenido, estado, creado) VALUES (?, ?, ?, ?, ?)",
        ("INF-AST-01-D01", 1, json.dumps({"id": "INF-AST-01-D01", "dia_mision": 1}),
         "pendiente", "2026-11-10T00:00:00+00:00"))
    conexion.execute(
        "INSERT INTO protocolo_pasos (dia, alerta_id, paso_id, hecho, actualizado) VALUES (?, ?, ?, ?, ?)",
        (1, "SUENO_BAJO", "s1", 1, "2026-11-10T00:00:00+00:00"))
    conexion.commit()
    conexion.close()


def test_la_migracion_conserva_el_historial_de_ast01(ruta_temporal):
    ruta = ruta_temporal / "vieja.db"
    _base_vieja(ruta)
    bd = BaseDatos(str(ruta))

    ast01 = bd.registros("AST-01")
    assert ast01[1]["indicadores"]["sueno_h"] == 6.6
    assert bd.registros("AST-02") == {}
    assert bd.informes(astronauta_id="AST-01")[0]["id"] == "INF-AST-01-D01"
    assert bd.pasos_hechos(1, "AST-01") == {"SUENO_BAJO": ["s1"]}
    assert list(ruta_temporal.glob("vieja.db.pre-multiautonauta-*.bak")), "debe quedar una copia"


def test_al_arrancar_se_siembran_los_otros_cinco_sin_borrar_ast01(ruta_temporal):
    ruta = ruta_temporal / "vieja.db"
    _base_vieja(ruta)
    bd = BaseDatos(str(ruta))
    servicio = Servicio(Ajustes.desde_entorno(), bd, ClienteOrquestador("http://no-usado"))
    assert servicio.roster_ids == ["AST-01", "AST-02", "AST-03", "AST-04", "AST-05", "AST-06"]
    assert servicio.bd.registros("AST-01")[1]["indicadores"]["sueno_h"] == 6.6
    assert servicio.bd.registros("AST-02")[1]["indicadores"]["sueno_h"] == 7.6
    assert servicio.dia_actual == 1
