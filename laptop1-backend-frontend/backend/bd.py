"""Persistencia en SQLite: registros, evaluaciones, alertas, resultados de modelos, informes.

Una sola conexión protegida con un candado; suficiente para un prototipo de una estación.
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS registros (
    dia INTEGER PRIMARY KEY, indicadores TEXT NOT NULL, manuales TEXT NOT NULL DEFAULT '[]',
    actualizado TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evaluaciones (
    dia INTEGER PRIMARY KEY, nivel_global TEXT NOT NULL, modo TEXT NOT NULL, origen TEXT NOT NULL,
    entrada TEXT NOT NULL, resultado TEXT NOT NULL, creado TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, dia INTEGER NOT NULL, alerta_id TEXT NOT NULL,
    nivel TEXT NOT NULL, causa TEXT NOT NULL, protocolo_id TEXT NOT NULL, creado TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS respuestas_modelos (
    id INTEGER PRIMARY KEY AUTOINCREMENT, dia INTEGER NOT NULL, especialista TEXT NOT NULL,
    riesgo REAL NOT NULL, nivel TEXT NOT NULL, confianza REAL NOT NULL, version_modelo TEXT NOT NULL,
    respuesta TEXT NOT NULL, creado TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS informes (
    id TEXT PRIMARY KEY, dia INTEGER NOT NULL, contenido TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente', creado TEXT NOT NULL, enviado TEXT);
CREATE TABLE IF NOT EXISTS protocolo_pasos (
    dia INTEGER NOT NULL, alerta_id TEXT NOT NULL, paso_id TEXT NOT NULL, hecho INTEGER NOT NULL,
    actualizado TEXT NOT NULL, PRIMARY KEY (dia, alerta_id, paso_id));
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT, dia INTEGER NOT NULL, tipo TEXT NOT NULL,
    datos TEXT NOT NULL, creado TEXT NOT NULL);
"""

TABLAS = ("estado", "registros", "evaluaciones", "alertas", "respuestas_modelos",
          "informes", "protocolo_pasos", "checkins")


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BaseDatos:
    def __init__(self, ruta: str):
        if ruta != ":memory:":
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self._conexion = sqlite3.connect(ruta, check_same_thread=False)
        self._conexion.row_factory = sqlite3.Row
        self._candado = threading.Lock()
        with self._candado:
            self._conexion.executescript(ESQUEMA)
            self._conexion.commit()

    # -- utilidades -----------------------------------------------------------
    def ejecutar(self, sql: str, parametros=()):
        with self._candado:
            cursor = self._conexion.execute(sql, parametros)
            self._conexion.commit()
            return cursor

    def consultar(self, sql: str, parametros=()) -> list:
        with self._candado:
            return [dict(fila) for fila in self._conexion.execute(sql, parametros).fetchall()]

    def vaciar(self):
        with self._candado:
            for tabla in TABLAS:
                self._conexion.execute(f"DELETE FROM {tabla}")
            self._conexion.commit()

    # -- estado clave/valor ---------------------------------------------------
    def leer_estado(self, clave: str, defecto=None):
        filas = self.consultar("SELECT valor FROM estado WHERE clave = ?", (clave,))
        return json.loads(filas[0]["valor"]) if filas else defecto

    def guardar_estado(self, clave: str, valor):
        self.ejecutar("INSERT INTO estado (clave, valor) VALUES (?, ?) "
                      "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor", (clave, json.dumps(valor)))

    # -- registros diarios ----------------------------------------------------
    def guardar_registro(self, dia: int, indicadores: dict, manuales: list):
        self.ejecutar(
            "INSERT INTO registros (dia, indicadores, manuales, actualizado) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(dia) DO UPDATE SET indicadores = excluded.indicadores, "
            "manuales = excluded.manuales, actualizado = excluded.actualizado",
            (dia, json.dumps(indicadores), json.dumps(sorted(set(manuales))), ahora()))

    def registros(self) -> dict:
        """{dia: {"indicadores": {...}, "manuales": [...]}}"""
        return {
            fila["dia"]: {"indicadores": json.loads(fila["indicadores"]),
                          "manuales": json.loads(fila["manuales"])}
            for fila in self.consultar("SELECT * FROM registros ORDER BY dia")
        }

    # -- evaluaciones, alertas y resultados de modelos ------------------------
    def guardar_evaluacion(self, dia: int, entrada: dict, resultado: dict):
        momento = ahora()
        self.ejecutar(
            "INSERT INTO evaluaciones (dia, nivel_global, modo, origen, entrada, resultado, creado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(dia) DO UPDATE SET "
            "nivel_global = excluded.nivel_global, modo = excluded.modo, origen = excluded.origen, "
            "entrada = excluded.entrada, resultado = excluded.resultado, creado = excluded.creado",
            (dia, resultado["nivel_global"], resultado["modo"], resultado.get("origen", ""),
             json.dumps(entrada), json.dumps(resultado), momento))
        self.ejecutar("DELETE FROM alertas WHERE dia = ?", (dia,))
        for alerta in resultado["alertas"]:
            self.ejecutar(
                "INSERT INTO alertas (dia, alerta_id, nivel, causa, protocolo_id, creado) VALUES (?, ?, ?, ?, ?, ?)",
                (dia, alerta["id"], alerta["nivel"], alerta["causa_en_lenguaje_simple"],
                 alerta["protocolo_id"], momento))
        self.ejecutar("DELETE FROM respuestas_modelos WHERE dia = ?", (dia,))
        for miembro in resultado.get("junta", []):
            respuesta = miembro.get("respuesta")
            if respuesta:
                self.ejecutar(
                    "INSERT INTO respuestas_modelos (dia, especialista, riesgo, nivel, confianza, "
                    "version_modelo, respuesta, creado) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (dia, respuesta["especialista"], respuesta["riesgo"], respuesta["nivel"],
                     respuesta["confianza"], respuesta["version_modelo"], json.dumps(respuesta), momento))

    def evaluacion(self, dia: int):
        filas = self.consultar("SELECT resultado FROM evaluaciones WHERE dia = ?", (dia,))
        return json.loads(filas[0]["resultado"]) if filas else None

    def borrar_evaluaciones_desde(self, dia: int):
        """Al cambiar un dato, lo evaluado en días posteriores deja de valer."""
        for tabla in ("evaluaciones", "alertas", "respuestas_modelos"):
            self.ejecutar(f"DELETE FROM {tabla} WHERE dia >= ?", (dia,))
        self.ejecutar("DELETE FROM informes WHERE dia >= ? AND estado = 'pendiente'", (dia,))

    def historial(self, hasta_dia: int) -> list:
        return self.consultar(
            "SELECT dia, nivel_global, modo, origen, creado FROM evaluaciones WHERE dia <= ? ORDER BY dia",
            (hasta_dia,))

    # -- informes para el cirujano de vuelo -----------------------------------
    def guardar_informe(self, informe: dict):
        """Entra en la cola 'pendiente'. Si ya se envió, no se toca."""
        existente = self.consultar("SELECT estado FROM informes WHERE id = ?", (informe["id"],))
        if existente and existente[0]["estado"] == "enviado":
            return
        self.ejecutar(
            "INSERT INTO informes (id, dia, contenido, estado, creado) VALUES (?, ?, ?, 'pendiente', ?) "
            "ON CONFLICT(id) DO UPDATE SET contenido = excluded.contenido",
            (informe["id"], informe["dia_mision"], json.dumps(informe), ahora()))

    def borrar_informe_pendiente(self, dia: int):
        self.ejecutar("DELETE FROM informes WHERE dia = ? AND estado = 'pendiente'", (dia,))

    def informes(self, hasta_dia: int | None = None) -> list:
        filas = self.consultar("SELECT * FROM informes ORDER BY dia")
        salida = []
        for fila in filas:
            if hasta_dia is not None and fila["dia"] > hasta_dia:
                continue
            salida.append({**fila, "contenido": json.loads(fila["contenido"])})
        return salida

    def marcar_informes_enviados(self, contenidos: dict) -> int:
        """contenidos = {id: informe ya completado con las acciones tomadas}."""
        momento = ahora()
        for id_, contenido in contenidos.items():
            self.ejecutar("UPDATE informes SET estado = 'enviado', enviado = ?, contenido = ? WHERE id = ?",
                          (momento, json.dumps(contenido), id_))
        return len(contenidos)

    # -- protocolos -----------------------------------------------------------
    def marcar_paso(self, dia: int, alerta_id: str, paso_id: str, hecho: bool):
        self.ejecutar(
            "INSERT INTO protocolo_pasos (dia, alerta_id, paso_id, hecho, actualizado) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(dia, alerta_id, paso_id) DO UPDATE SET hecho = excluded.hecho, "
            "actualizado = excluded.actualizado", (dia, alerta_id, paso_id, int(hecho), ahora()))

    def pasos_hechos(self, dia: int) -> dict:
        """{alerta_id: [paso_id, ...]} de los pasos marcados 'ya lo hice' ese día."""
        salida = {}
        for fila in self.consultar(
                "SELECT alerta_id, paso_id FROM protocolo_pasos WHERE dia = ? AND hecho = 1 ORDER BY paso_id",
                (dia,)):
            salida.setdefault(fila["alerta_id"], []).append(fila["paso_id"])
        return salida

    # -- check-ins ------------------------------------------------------------
    def guardar_checkin(self, dia: int, tipo: str, datos: dict):
        self.ejecutar("INSERT INTO checkins (dia, tipo, datos, creado) VALUES (?, ?, ?, ?)",
                      (dia, tipo, json.dumps(datos), ahora()))

    def ultimo_checkin(self, dia: int, tipo: str):
        filas = self.consultar(
            "SELECT datos, creado FROM checkins WHERE dia = ? AND tipo = ? ORDER BY id DESC LIMIT 1", (dia, tipo))
        return {**json.loads(filas[0]["datos"]), "creado": filas[0]["creado"]} if filas else None
