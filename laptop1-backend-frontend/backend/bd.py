"""Persistencia en SQLite: registros, evaluaciones, alertas, resultados de modelos, informes.

Una sola conexión protegida con un candado; suficiente para un prototipo de una estación.
Todas las tablas llevan ``astronauta_id``. Las claves son compuestas
(astronauta_id, dia) para que cada tripulante tenga su propio historial.

Este módulo migra automáticamente una base del esquema antiguo (solo AST-01):
copia el archivo antes de tocar nada y reasigna las filas existentes a AST-01.
Nunca borra una base sin copia.
"""

import json
import logging
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("backend.bd")

_CREAR = {
    "registros": """
        CREATE TABLE IF NOT EXISTS "registros" (
            astronauta_id TEXT NOT NULL DEFAULT 'AST-01', dia INTEGER NOT NULL,
            indicadores TEXT NOT NULL, manuales TEXT NOT NULL DEFAULT '[]',
            actualizado TEXT NOT NULL, PRIMARY KEY (astronauta_id, dia))""",
    "evaluaciones": """
        CREATE TABLE IF NOT EXISTS "evaluaciones" (
            astronauta_id TEXT NOT NULL DEFAULT 'AST-01', dia INTEGER NOT NULL,
            nivel_global TEXT NOT NULL, modo TEXT NOT NULL, origen TEXT NOT NULL,
            entrada TEXT NOT NULL, resultado TEXT NOT NULL, creado TEXT NOT NULL,
            PRIMARY KEY (astronauta_id, dia))""",
    "alertas": """
        CREATE TABLE IF NOT EXISTS "alertas" (
            id INTEGER PRIMARY KEY AUTOINCREMENT, astronauta_id TEXT NOT NULL DEFAULT 'AST-01',
            dia INTEGER NOT NULL, alerta_id TEXT NOT NULL, nivel TEXT NOT NULL,
            causa TEXT NOT NULL, protocolo_id TEXT NOT NULL, creado TEXT NOT NULL)""",
    "respuestas_modelos": """
        CREATE TABLE IF NOT EXISTS "respuestas_modelos" (
            id INTEGER PRIMARY KEY AUTOINCREMENT, astronauta_id TEXT NOT NULL DEFAULT 'AST-01',
            dia INTEGER NOT NULL, especialista TEXT NOT NULL, riesgo REAL NOT NULL,
            nivel TEXT NOT NULL, confianza REAL NOT NULL, version_modelo TEXT NOT NULL,
            respuesta TEXT NOT NULL, creado TEXT NOT NULL)""",
    "informes": """
        CREATE TABLE IF NOT EXISTS "informes" (
            id TEXT PRIMARY KEY, astronauta_id TEXT NOT NULL DEFAULT 'AST-01',
            dia INTEGER NOT NULL, contenido TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente', creado TEXT NOT NULL, enviado TEXT)""",
    "protocolo_pasos": """
        CREATE TABLE IF NOT EXISTS "protocolo_pasos" (
            astronauta_id TEXT NOT NULL DEFAULT 'AST-01', dia INTEGER NOT NULL,
            alerta_id TEXT NOT NULL, paso_id TEXT NOT NULL, hecho INTEGER NOT NULL,
            actualizado TEXT NOT NULL,
            PRIMARY KEY (astronauta_id, dia, alerta_id, paso_id))""",
    "checkins": """
        CREATE TABLE IF NOT EXISTS "checkins" (
            id INTEGER PRIMARY KEY AUTOINCREMENT, astronauta_id TEXT NOT NULL DEFAULT 'AST-01',
            dia INTEGER NOT NULL, tipo TEXT NOT NULL, datos TEXT NOT NULL, creado TEXT NOT NULL)""",
    "lecturas_reloj": """
        CREATE TABLE IF NOT EXISTS "lecturas_reloj" (
            lectura_id TEXT PRIMARY KEY, astronauta_id TEXT NOT NULL, dia INTEGER NOT NULL,
            capturado_en TEXT NOT NULL, indicadores TEXT NOT NULL, creado TEXT NOT NULL)""",
}

ESQUEMA_TABLAS = """
CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
""" + "".join(_CREAR[t] + ";" for t in _CREAR)

# Los índices se crean DESPUÉS de migrar: una tabla antigua aún no tiene astronauta_id.
ESQUEMA_INDICES = """
CREATE INDEX IF NOT EXISTS idx_alertas_astronauta_dia ON alertas (astronauta_id, dia);
CREATE INDEX IF NOT EXISTS idx_respuestas_astronauta_dia ON respuestas_modelos (astronauta_id, dia);
CREATE INDEX IF NOT EXISTS idx_informes_astronauta_dia ON informes (astronauta_id, dia);
"""

TABLAS = ("estado", "registros", "evaluaciones", "alertas", "respuestas_modelos",
          "informes", "protocolo_pasos", "checkins", "lecturas_reloj")


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _columnas(conexion, tabla: str) -> set:
    return {fila[1] for fila in conexion.execute(f'PRAGMA table_info("{tabla}")')}


def _esquema_viejo(conexion) -> bool:
    """True si existe la tabla de registros y no tiene astronauta_id."""
    columnas = _columnas(conexion, "registros")
    return bool(columnas) and "astronauta_id" not in columnas


def _copiar_sql(tabla: str) -> str:
    """INSERT que reasigna las filas antiguas a AST-01, conservando ids."""
    if tabla == "registros":
        return ("INSERT INTO registros (astronauta_id, dia, indicadores, manuales, actualizado) "
                "SELECT 'AST-01', dia, indicadores, manuales, actualizado FROM registros_viejo")
    if tabla == "evaluaciones":
        return ("INSERT INTO evaluaciones (astronauta_id, dia, nivel_global, modo, origen, entrada, "
                "resultado, creado) SELECT 'AST-01', dia, nivel_global, modo, origen, entrada, "
                "resultado, creado FROM evaluaciones_viejo")
    if tabla == "alertas":
        return ("INSERT INTO alertas (id, astronauta_id, dia, alerta_id, nivel, causa, protocolo_id, "
                "creado) SELECT id, 'AST-01', dia, alerta_id, nivel, causa, protocolo_id, creado "
                "FROM alertas_viejo")
    if tabla == "respuestas_modelos":
        return ("INSERT INTO respuestas_modelos (id, astronauta_id, dia, especialista, riesgo, nivel, "
                "confianza, version_modelo, respuesta, creado) SELECT id, 'AST-01', dia, "
                "especialista, riesgo, nivel, confianza, version_modelo, respuesta, creado "
                "FROM respuestas_modelos_viejo")
    if tabla == "informes":
        return ("INSERT INTO informes (id, astronauta_id, dia, contenido, estado, creado, enviado) "
                "SELECT id, 'AST-01', dia, contenido, estado, creado, enviado FROM informes_viejo")
    if tabla == "protocolo_pasos":
        return ("INSERT INTO protocolo_pasos (astronauta_id, dia, alerta_id, paso_id, hecho, "
                "actualizado) SELECT 'AST-01', dia, alerta_id, paso_id, hecho, actualizado "
                "FROM protocolo_pasos_viejo")
    if tabla == "checkins":
        return ("INSERT INTO checkins (id, astronauta_id, dia, tipo, datos, creado) "
                "SELECT id, 'AST-01', dia, tipo, datos, creado FROM checkins_viejo")
    raise KeyError(tabla)


class BaseDatos:
    def __init__(self, ruta: str):
        if ruta != ":memory:":
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self.ruta = ruta
        self._conexion = sqlite3.connect(ruta, check_same_thread=False)
        self._conexion.row_factory = sqlite3.Row
        self._candado = threading.Lock()
        with self._candado:
            self._conexion.executescript(ESQUEMA_TABLAS)
            self._conexion.commit()
            if _esquema_viejo(self._conexion):
                self._migrar()
            self._conexion.executescript(ESQUEMA_INDICES)
            self._conexion.commit()

    # -- migración ------------------------------------------------------------
    def _migrar(self):
        """Pasa una base de un solo astronauta al esquema multiastronauta.

        Primero copia el archivo (si es una base en disco). Después reasigna todas
        las filas a AST-01 y conserva ids, días, informes y pasos de protocolo.
        """
        if self.ruta != ":memory:":
            origen = Path(self.ruta)
            if origen.exists():
                respaldo = origen.with_name(
                    f"{origen.name}.pre-multiautonauta-{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak")
                shutil.copy2(origen, respaldo)
                log.warning("Base antigua copiada a %s antes de migrar.", respaldo)
        try:
            with self._conexion:
                for tabla in _CREAR:
                    if not _columnas(self._conexion, tabla):
                        continue
                    if "astronauta_id" in _columnas(self._conexion, tabla):
                        continue
                    self._conexion.execute(f'ALTER TABLE "{tabla}" RENAME TO "{tabla}_viejo"')
                    self._conexion.execute(_CREAR[tabla])
                    self._conexion.execute(_copiar_sql(tabla))
                    self._conexion.execute(f'DROP TABLE "{tabla}_viejo"')
        except Exception:
            log.exception("No se pudo migrar la base; se conserva la copia de seguridad.")
            raise
        log.info("Base migrada al esquema multiastronauta; las filas antiguas son de AST-01.")

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
    def guardar_registro(self, dia: int, indicadores: dict, manuales: list, astronauta_id: str = "AST-01"):
        self.ejecutar(
            "INSERT INTO registros (astronauta_id, dia, indicadores, manuales, actualizado) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(astronauta_id, dia) DO UPDATE SET "
            "indicadores = excluded.indicadores, manuales = excluded.manuales, "
            "actualizado = excluded.actualizado",
            (astronauta_id, dia, json.dumps(indicadores), json.dumps(sorted(set(manuales))), ahora()))

    def registros(self, astronauta_id: str = "AST-01") -> dict:
        """{dia: {"indicadores": {...}, "manuales": [...]}} de un astronauta."""
        return {
            fila["dia"]: {"indicadores": json.loads(fila["indicadores"]),
                          "manuales": json.loads(fila["manuales"])}
            for fila in self.consultar(
                "SELECT * FROM registros WHERE astronauta_id = ? ORDER BY dia", (astronauta_id,))
        }

    def registros_todos(self) -> dict:
        """{astronauta_id: {dia: {...}}} con todos los tripulantes."""
        salida = {}
        for fila in self.consultar("SELECT * FROM registros ORDER BY astronauta_id, dia"):
            salida.setdefault(fila["astronauta_id"], {})[fila["dia"]] = {
                "indicadores": json.loads(fila["indicadores"]),
                "manuales": json.loads(fila["manuales"]),
            }
        return salida

    # -- evaluaciones, alertas y resultados de modelos ------------------------
    def guardar_evaluacion(self, dia: int, entrada: dict, resultado: dict, astronauta_id: str = "AST-01"):
        momento = ahora()
        self.ejecutar(
            "INSERT INTO evaluaciones (astronauta_id, dia, nivel_global, modo, origen, entrada, resultado, creado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(astronauta_id, dia) DO UPDATE SET "
            "nivel_global = excluded.nivel_global, modo = excluded.modo, origen = excluded.origen, "
            "entrada = excluded.entrada, resultado = excluded.resultado, creado = excluded.creado",
            (astronauta_id, dia, resultado["nivel_global"], resultado["modo"],
             resultado.get("origen", ""), json.dumps(entrada), json.dumps(resultado), momento))
        self.ejecutar("DELETE FROM alertas WHERE astronauta_id = ? AND dia = ?", (astronauta_id, dia))
        for alerta in resultado["alertas"]:
            self.ejecutar(
                "INSERT INTO alertas (astronauta_id, dia, alerta_id, nivel, causa, protocolo_id, creado) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (astronauta_id, dia, alerta["id"], alerta["nivel"],
                 alerta["causa_en_lenguaje_simple"], alerta["protocolo_id"], momento))
        self.ejecutar("DELETE FROM respuestas_modelos WHERE astronauta_id = ? AND dia = ?",
                      (astronauta_id, dia))
        for miembro in resultado.get("junta", []):
            respuesta = miembro.get("respuesta")
            if respuesta:
                self.ejecutar(
                    "INSERT INTO respuestas_modelos (astronauta_id, dia, especialista, riesgo, nivel, "
                    "confianza, version_modelo, respuesta, creado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (astronauta_id, dia, respuesta["especialista"], respuesta["riesgo"], respuesta["nivel"],
                     respuesta["confianza"], respuesta["version_modelo"], json.dumps(respuesta), momento))

    def evaluacion(self, dia: int, astronauta_id: str = "AST-01"):
        filas = self.consultar(
            "SELECT resultado FROM evaluaciones WHERE astronauta_id = ? AND dia = ?", (astronauta_id, dia))
        return json.loads(filas[0]["resultado"]) if filas else None

    def borrar_evaluaciones_desde(self, dia: int, astronauta_id: str | None = None):
        """Al cambiar un dato, lo evaluado de ese día en adelante deja de valer.

        Sin ``astronauta_id`` se invalida a toda la tripulación (eventos globales
        de la demo, como la tormenta solar o el sensor defectuoso).
        """
        filtro, parametros = ("", ()) if astronauta_id is None else (
            " AND astronauta_id = ?", (astronauta_id,))
        for tabla in ("evaluaciones", "alertas", "respuestas_modelos"):
            self.ejecutar(f"DELETE FROM {tabla} WHERE dia >= ?{filtro}", (dia,) + parametros)
        self.ejecutar(f"DELETE FROM informes WHERE dia >= ? AND estado = 'pendiente'{filtro}",
                      (dia,) + parametros)

    def historial(self, hasta_dia: int, astronauta_id: str = "AST-01") -> list:
        return self.consultar(
            "SELECT dia, nivel_global, modo, origen, creado FROM evaluaciones "
            "WHERE astronauta_id = ? AND dia <= ? ORDER BY dia", (astronauta_id, hasta_dia))

    # -- informes para el cirujano de vuelo -----------------------------------
    def guardar_informe(self, informe: dict, astronauta_id: str | None = None):
        """Entra en la cola 'pendiente'. Si ya se envió, no se toca."""
        astronauta_id = astronauta_id or informe.get("astronauta_id", "AST-01")
        existente = self.consultar("SELECT estado FROM informes WHERE id = ?", (informe["id"],))
        if existente and existente[0]["estado"] == "enviado":
            return
        self.ejecutar(
            "INSERT INTO informes (id, astronauta_id, dia, contenido, estado, creado) "
            "VALUES (?, ?, ?, ?, 'pendiente', ?) "
            "ON CONFLICT(id) DO UPDATE SET contenido = excluded.contenido, astronauta_id = excluded.astronauta_id",
            (informe["id"], astronauta_id, informe["dia_mision"], json.dumps(informe), ahora()))

    def borrar_informe_pendiente(self, dia: int, astronauta_id: str = "AST-01"):
        self.ejecutar("DELETE FROM informes WHERE astronauta_id = ? AND dia = ? AND estado = 'pendiente'",
                      (astronauta_id, dia))

    def informes(self, hasta_dia: int | None = None, astronauta_id: str | None = None) -> list:
        filas = self.consultar("SELECT * FROM informes ORDER BY dia")
        salida = []
        for fila in filas:
            if hasta_dia is not None and fila["dia"] > hasta_dia:
                continue
            if astronauta_id is not None and fila["astronauta_id"] != astronauta_id:
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
    def marcar_paso(self, dia: int, alerta_id: str, paso_id: str, hecho: bool, astronauta_id: str = "AST-01"):
        self.ejecutar(
            "INSERT INTO protocolo_pasos (astronauta_id, dia, alerta_id, paso_id, hecho, actualizado) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(astronauta_id, dia, alerta_id, paso_id) "
            "DO UPDATE SET hecho = excluded.hecho, actualizado = excluded.actualizado",
            (astronauta_id, dia, alerta_id, paso_id, int(hecho), ahora()))

    def pasos_hechos(self, dia: int, astronauta_id: str = "AST-01") -> dict:
        """{alerta_id: [paso_id, ...]} de los pasos marcados 'ya lo hice' ese día."""
        salida = {}
        for fila in self.consultar(
                "SELECT alerta_id, paso_id FROM protocolo_pasos "
                "WHERE astronauta_id = ? AND dia = ? AND hecho = 1 ORDER BY paso_id",
                (astronauta_id, dia)):
            salida.setdefault(fila["alerta_id"], []).append(fila["paso_id"])
        return salida

    # -- check-ins ------------------------------------------------------------
    def guardar_checkin(self, dia: int, tipo: str, datos: dict, astronauta_id: str = "AST-01"):
        self.ejecutar("INSERT INTO checkins (astronauta_id, dia, tipo, datos, creado) VALUES (?, ?, ?, ?, ?)",
                      (astronauta_id, dia, tipo, json.dumps(datos), ahora()))

    def ultimo_checkin(self, dia: int, tipo: str, astronauta_id: str = "AST-01"):
        filas = self.consultar(
            "SELECT datos, creado FROM checkins WHERE astronauta_id = ? AND dia = ? AND tipo = ? "
            "ORDER BY id DESC LIMIT 1", (astronauta_id, dia, tipo))
        return {**json.loads(filas[0]["datos"]), "creado": filas[0]["creado"]} if filas else None

    # -- reloj: idempotencia de lecturas --------------------------------------
    def lectura_guardada(self, lectura_id: str):
        filas = self.consultar("SELECT * FROM lecturas_reloj WHERE lectura_id = ?", (lectura_id,))
        if not filas:
            return None
        fila = dict(filas[0])
        fila["indicadores"] = json.loads(fila["indicadores"])
        return fila

    def guardar_lectura(self, lectura_id: str, astronauta_id: str, dia: int,
                        capturado_en: str, indicadores: dict):
        self.ejecutar(
            "INSERT OR IGNORE INTO lecturas_reloj "
            "(lectura_id, astronauta_id, dia, capturado_en, indicadores, creado) VALUES (?, ?, ?, ?, ?, ?)",
            (lectura_id, astronauta_id, dia, capturado_en, json.dumps(indicadores), ahora()))
