"""Lógica del backend: guion de 7 días, validación de sensores, línea base, evaluación,
informes y controles de demo.

Todos los datos son SIMULADOS. La clase no sabe de HTTP entrante: principal.py
expone estos métodos como API.

Multiastronauta: cada método acepta ``astronauta_id`` y, si no se indica, usa el
astronauta activo (AST-01 por defecto). Las firmas antiguas siguen funcionando.
"""

import csv
import io
import logging
import statistics
import time
from datetime import datetime

from backend import aptitud, calculo, sensores
from backend.ajustes import Ajustes
from backend.bd import BaseDatos, ahora
from backend.cliente_orquestador import ClienteOrquestador
from comun import AVISO
from comun.contratos import ErrorContrato, validar
from reglas import motor as motor_reglas

log = logging.getLogger("backend")

RETRASO_ENLACE_MIN = 20   # minutos por sentido hasta la Tierra (escenario Marte, valor ilustrativo)
PRINCIPALES_TENDENCIA_RELOJ = ("sueno_h", "fc_reposo", "hrv", "estres")
CAMPOS_RELOJ = ("sueno_h", "animo", "estres", "ejercicio_min", "fc_reposo", "hrv",
                "spo2", "temperatura", "ingesta_pct")
RIESGO_POR_NIVEL = {"verde": 8, "amarillo": 35, "naranja": 62, "rojo": 88}
AVISO_RELOJ = AVISO + " Simulated watch on the web; it is not a medical device."


class ErrorDatos(ValueError):
    """Dato rechazado por la validación; el mensaje es apto para mostrar al usuario."""


class Servicio:
    def __init__(self, ajustes: Ajustes, bd: BaseDatos, cliente: ClienteOrquestador):
        self.ajustes = ajustes
        self.bd = bd
        self.cliente = cliente
        self._config_reglas = motor_reglas.cargar_config()
        self._config_preparacion = ajustes.tripulacion["preparacion"]
        self.perfiles = self._cargar_perfiles()
        self.roster_ids = list(self.perfiles)
        self._cache_tripulacion = {}
        self._cache_version = 0
        self._preparacion_cache = {}

        if not self.bd.registros_todos():
            self._cargar_guion()
        else:
            # Una base migrada conserva AST-01 y necesita sembrar a los otros cinco.
            self._sembrar_faltantes()
            if self.bd.leer_estado("dia_actual") is None:
                self.bd.guardar_estado("dia_actual", 1)
            if self.bd.leer_estado("astronauta_activo") not in self.perfiles:
                self.bd.guardar_estado("astronauta_activo", "AST-01")

    # ------------------------------------------------------------------
    # Perfiles y guion
    # ------------------------------------------------------------------
    def _cargar_perfiles(self) -> dict:
        """Perfil completo (astronauta, base, plan, guion) de cada tripulante.

        AST-01 toma perfil.toml y guion_7_dias.toml sin cambios. Los otros cinco
        viven en tripulacion.toml y comparten las secciones de configuración que
        no son propias (recalibración, módulos externos, evento solar).
        """
        base = self.ajustes.perfil
        perfiles = {
            "AST-01": {
                **base,
                "guion": self.ajustes.guion,
                "dias_sin_registro": [],
                "sensor_sospechoso": None,
            }
        }
        for astronauta_id, datos in (self.ajustes.tripulacion.get("astronautas") or {}).items():
            perfiles[astronauta_id] = {
                "astronauta": {
                    "id": astronauta_id,
                    "nombre": datos["nombre"],
                    "rol": datos["rol"],
                    "mision": datos.get("mision", base["astronauta"]["mision"]),
                },
                "linea_base_prevuelo": dict(datos["linea_base_prevuelo"]),
                "plan": dict(datos["plan"]),
                "recalibracion": dict(base["recalibracion"]),
                "modulos_externos": dict(base["modulos_externos"]),
                "musculo_hueso": dict(base["musculo_hueso"]),
                "evento_solar": dict(base["evento_solar"]),
                "guion": {"indicadores": dict(datos["guion"]), "notas": {}},
                "dias_sin_registro": list(datos.get("dias_sin_registro") or []),
                "sensor_sospechoso": datos.get("sensor_sospechoso"),
            }
        return perfiles

    def perfil_de(self, astronauta_id: str) -> dict:
        if astronauta_id not in self.perfiles:
            validos = ", ".join(self.roster_ids)
            raise ErrorDatos(f"Astronauta desconocido: '{astronauta_id}'. IDs válidos: {validos}.")
        return self.perfiles[astronauta_id]

    @property
    def astronauta_activo(self) -> str:
        activo = self.bd.leer_estado("astronauta_activo", "AST-01")
        return activo if activo in self.perfiles else "AST-01"

    def _sembrar_astronauta(self, astronauta_id: str):
        perfil = self.perfiles[astronauta_id]
        sin_registro = set(perfil["dias_sin_registro"])
        for dia in range(1, self.ajustes.dias_guion + 1):
            if dia in sin_registro:
                continue
            indicadores = calculo.indicadores_del_guion(perfil["guion"], dia)
            sospechoso = perfil.get("sensor_sospechoso")
            if sospechoso and int(sospechoso["dia"]) == dia:
                indicadores[sospechoso["indicador"]] = float(sospechoso["valor"])
            self.bd.guardar_registro(dia, indicadores, [], astronauta_id)

    def _sembrar_faltantes(self):
        for astronauta_id in self.roster_ids:
            if not self.bd.registros(astronauta_id):
                self._sembrar_astronauta(astronauta_id)

    def _cargar_guion(self):
        """Carga los 7 días de los seis astronautas y vuelve al día 1."""
        self.bd.vaciar()
        for astronauta_id in self.roster_ids:
            self._sembrar_astronauta(astronauta_id)
        self.bd.guardar_estado("dia_actual", 1)
        self.bd.guardar_estado("astronauta_activo", "AST-01")
        self.bd.guardar_estado("evento_solar_dia", None)
        self.bd.guardar_estado("sensor_defectuoso", None)
        self._invalidar_cache()
        log.info("Guion de %d días cargado para %d astronautas.",
                 self.ajustes.dias_guion, len(self.roster_ids))

    def roster(self) -> list:
        return [
            {"id": a, "nombre": self.perfiles[a]["astronauta"]["nombre"],
             "rol": self.perfiles[a]["astronauta"]["rol"]}
            for a in self.roster_ids
        ]

    @property
    def dia_actual(self) -> int:
        return int(self.bd.leer_estado("dia_actual", 1))

    def _validar_dia(self, dia) -> int:
        if not isinstance(dia, int) or isinstance(dia, bool) or not 1 <= dia <= self.ajustes.dias_guion:
            raise ErrorDatos(f"El día de misión va de 1 a {self.ajustes.dias_guion}.")
        return dia

    def _invalidar_cache(self):
        self._cache_version += 1
        self._cache_tripulacion.clear()
        self._preparacion_cache.clear()

    # ------------------------------------------------------------------
    # Datos efectivos y validados
    # ------------------------------------------------------------------
    def registros_efectivos(self, crudos: dict | None = None, astronauta_id: str | None = None) -> dict:
        """{dia: indicadores} tal como llegan de los sensores: aplica evento solar, dosis
        acumulada, módulos externos y, si está activo, el sensor defectuoso de la demo.

        Estas lecturas todavía NO están validadas: para calcular hay que usar
        registros_validados().
        """
        astronauta_id = astronauta_id or self.astronauta_activo
        perfil = self.perfil_de(astronauta_id)
        crudos = crudos if crudos is not None else self.bd.registros(astronauta_id)
        evento_dia = self.bd.leer_estado("evento_solar_dia")
        evento = perfil["evento_solar"]
        modulos = perfil["modulos_externos"]
        salida, acumulada = {}, 0.0
        for dia in sorted(crudos):
            indicadores = dict(crudos[dia]["indicadores"])
            tasa = indicadores.get("tasa_dosis_usv_h")
            if calculo.es_numero(tasa):
                acumulada += tasa * 24.0 / 1000.0          # µSv/h durante 24 h -> mSv
            if evento_dia == dia:
                indicadores["tasa_dosis_usv_h"] = evento["tasa_dosis_usv_h"]
            if evento_dia is not None and dia >= evento_dia:
                indicadores["dosis_acumulada_msv"] = round(acumulada + evento["dosis_extra_msv"], 2)
            else:
                indicadores["dosis_acumulada_msv"] = round(acumulada, 2)
            if not modulos["presion"]:
                indicadores["presion_sistolica"] = indicadores["presion_diastolica"] = None
            if not modulos["glucosa"]:
                indicadores["glucosa"] = None
            salida[dia] = indicadores
        manuales = {dia: crudos[dia]["manuales"] for dia in crudos}
        return sensores.aplicar_falla(salida, manuales, self.bd.leer_estado("sensor_defectuoso"),
                                      self.ajustes.sensores)

    def registros_validados(self, astronauta_id: str | None = None) -> tuple[dict, dict]:
        """Capa de validación de sensores: corre ANTES de las reglas y de los modelos.

        Devuelve ({dia: indicadores} con los datos sospechosos apartados (None),
                  {dia: [fichas de los datos sospechosos de ese día]}).
        """
        astronauta_id = astronauta_id or self.astronauta_activo
        perfil = self.perfil_de(astronauta_id)
        crudos = self.bd.registros(astronauta_id)
        manuales = {dia: crudos[dia]["manuales"] for dia in crudos}
        validados, sospechosos = sensores.validar(
            self.registros_efectivos(crudos, astronauta_id), manuales, self.ajustes.sensores)
        fichas = {}
        for dia, por_indicador in sospechosos.items():
            fichas[dia] = []
            for indicador, ficha in por_indicador.items():
                catalogo = self.ajustes.catalogo.get(indicador, {})
                fichas[dia].append({**ficha, "nombre": catalogo.get("nombre", indicador),
                                    "unidad": catalogo.get("unidad", "")})
        return validados, fichas

    def _entrada_con(self, astronauta_id: str, dia: int, registros: dict, sospechosos: dict) -> dict:
        """Entrada del orquestador a partir de registros ya validados (sin repetir el cálculo)."""
        perfil = self.perfiles[astronauta_id]
        claves = list(self.ajustes.catalogo.keys())
        hoy = registros.get(dia) or {}
        indicadores = {clave: hoy.get(clave) for clave in claves}
        base = calculo.linea_base(perfil, dia, registros)
        series, _ = calculo.tendencias(registros, dia, claves)
        evento_dia = self.bd.leer_estado("evento_solar_dia")
        entrada = {
            "astronauta_id": astronauta_id,
            "dia_mision": dia,
            "indicadores": indicadores,
            "desviaciones_vs_base": calculo.desviaciones(indicadores, base),
            "tendencias_7d": series,
            "linea_base": base,
            "plan": dict(perfil["plan"]),
            "contexto": {
                "dosis_acumulada": indicadores.get("dosis_acumulada_msv") or 0.0,
                "evento_solar": evento_dia == dia,
            },
        }
        if sospechosos.get(dia):
            entrada["sensores_sospechosos"] = sospechosos[dia]
        return entrada

    def construir_entrada(self, dia: int, astronauta_id: str | None = None) -> dict:
        """Mensaje para el orquestador (contrato entrada_orquestador)."""
        astronauta_id = astronauta_id or self.astronauta_activo
        self.perfil_de(astronauta_id)
        registros, sospechosos = self.registros_validados(astronauta_id)
        return self._entrada_con(astronauta_id, dia, registros, sospechosos)

    # ------------------------------------------------------------------
    # Evaluación
    # ------------------------------------------------------------------
    async def evaluar_dia(self, dia: int, astronauta_id: str | None = None,
                          tiempo_max_s: float | None = None, reintentos: int | None = None) -> dict:
        """Llama al orquestador (o al respaldo local), guarda todo y devuelve el resultado."""
        astronauta_id = astronauta_id or self.astronauta_activo
        self.perfil_de(astronauta_id)
        self._validar_dia(dia)
        entrada = self.construir_entrada(dia, astronauta_id)
        resultado, conexion = await self.cliente.evaluar(entrada, tiempo_max_s, reintentos)
        resultado = {**resultado, "astronauta_id": astronauta_id}
        self.bd.guardar_evaluacion(dia, entrada, resultado, astronauta_id)
        if resultado["informe_cirujano"]:
            self.bd.guardar_informe(resultado["informe_cirujano"], astronauta_id)
        else:
            self.bd.borrar_informe_pendiente(dia, astronauta_id)
        self.bd.guardar_estado("conexion_orquestador", conexion)
        self._invalidar_cache()
        return resultado

    async def _completar_historial(self, hasta_dia: int, astronauta_id: str | None = None):
        """Si se saltó de día con el deslizador, evalúa los días intermedios que falten."""
        astronauta_id = astronauta_id or self.astronauta_activo
        evaluados = {fila["dia"] for fila in self.bd.historial(hasta_dia, astronauta_id)}
        con_datos = set(self.bd.registros(astronauta_id))
        for dia in range(1, hasta_dia):
            if dia not in evaluados and dia in con_datos:
                await self.evaluar_dia(dia, astronauta_id)

    async def _datos_cambiaron(self, desde: int | None = None, astronauta_id: str | None = None,
                               todos: bool = False):
        """Tras cualquier cambio de datos: lo evaluado de hoy en adelante ya no vale.

        ``todos=True`` invalida a toda la tripulación (evento solar, sensor defectuoso
        de la demo). Después se reevalúa solo al astronauta activo; el resto se
        calcula cuando se pide su detalle o su estado de reloj.
        """
        dia = self.dia_actual
        afectados = self.roster_ids if todos else [astronauta_id or self.astronauta_activo]
        for afectado in afectados:
            self.bd.borrar_evaluaciones_desde(min(dia, desde) if desde else dia, afectado)
        self._invalidar_cache()
        await self.evaluar_dia(dia, self.astronauta_activo)

    # ------------------------------------------------------------------
    # Lectura para la interfaz
    # ------------------------------------------------------------------
    def _acciones_tomadas(self, dia: int, astronauta_id: str | None = None) -> list:
        """Textos de los pasos de protocolo marcados 'ya lo hice' ese día."""
        astronauta_id = astronauta_id or self.astronauta_activo
        resultado = self.bd.evaluacion(dia, astronauta_id)
        if not resultado:
            return []
        protocolo_de = {a["id"]: resultado["protocolos"].get(a["protocolo_id"]) for a in resultado["alertas"]}
        acciones = []
        for alerta_id, pasos in self.bd.pasos_hechos(dia, astronauta_id).items():
            protocolo = protocolo_de.get(alerta_id)
            if not protocolo:
                continue
            textos = {paso["id"]: paso["texto"] for paso in protocolo["pasos"]}
            acciones += [{"alerta": alerta_id, "paso": textos[p]} for p in pasos if p in textos]
        return acciones

    def _informes(self, hasta_dia: int, astronauta_id: str | None = None) -> list:
        astronauta_id = astronauta_id or self.astronauta_activo
        informes = self.bd.informes(hasta_dia, astronauta_id)
        for informe in informes:
            if informe["estado"] == "pendiente":
                informe["contenido"]["acciones_tomadas"] = self._acciones_tomadas(
                    informe["dia"], astronauta_id)
        return informes

    async def estado(self, astronauta_id: str | None = None) -> dict:
        """Todo lo que la interfaz necesita para pintar el día del astronauta activo."""
        astronauta_id = astronauta_id or self.astronauta_activo
        perfil = self.perfil_de(astronauta_id)
        dia = self.dia_actual
        resultado = self.bd.evaluacion(dia, astronauta_id) or await self.evaluar_dia(dia, astronauta_id)
        await self._completar_historial(dia, astronauta_id)
        registros, sospechosos = self.registros_validados(astronauta_id)
        crudos = self.bd.registros(astronauta_id)
        hoy = registros.get(dia) or {}
        claves = list(self.ajustes.catalogo.keys())
        indicadores = {clave: hoy.get(clave) for clave in claves}
        base = calculo.linea_base(perfil, dia, registros)
        series, dias = calculo.tendencias(registros, dia, claves)
        evento_dia = self.bd.leer_estado("evento_solar_dia")
        falla = self.bd.leer_estado("sensor_defectuoso") or {}
        modulos = perfil["modulos_externos"]
        registro_hoy = crudos.get(dia) or {"indicadores": {}, "manuales": []}
        return {
            "aviso": AVISO,
            "astronauta": perfil["astronauta"],
            "astronauta_id": astronauta_id,
            "astronauta_activo": self.astronauta_activo,
            "roster": self.roster(),
            "dia_actual": dia,
            "dias_totales": self.ajustes.dias_guion,
            "nota_dia": perfil["guion"].get("notas", {}).get(str(dia), ""),
            "indicadores": indicadores,
            "datos_manuales": registro_hoy["manuales"],
            "linea_base": base,
            "plan": perfil["plan"],
            "desviaciones_vs_base": calculo.desviaciones(indicadores, base),
            "tendencias_7d": series,
            "dias_tendencia": dias,
            "catalogo": self.ajustes.catalogo,
            "resultado": resultado,
            "evento_solar": {"dia": evento_dia, "activo_hoy": evento_dia == dia},
            "sensores_sospechosos": sospechosos.get(dia, []),
            "sensor_defectuoso": {"dia": falla.get("dia"), "activo_hoy": falla.get("dia") == dia,
                                  "indicador": falla.get("indicador"), "tipo": falla.get("tipo")},
            "modulos_externos": {
                "etiqueta": modulos["etiqueta"],
                "presion": ({"sistolica": indicadores.get("presion_sistolica"),
                             "diastolica": indicadores.get("presion_diastolica")}
                            if modulos["presion"] else None),
                "glucosa": indicadores.get("glucosa") if modulos["glucosa"] else None,
            },
            "musculo_hueso": calculo.exposicion_musculo_hueso(
                registros, dia, perfil["plan"]["ejercicio_min"],
                perfil["musculo_hueso"]["proteccion_ejercicio"]),
            "pasos_hechos": self.bd.pasos_hechos(dia, astronauta_id),
            "informes": self._informes(dia, astronauta_id),
            "ultimo_enlace": self.bd.leer_estado("ultimo_enlace"),
            "historial": self.bd.historial(dia, astronauta_id),
            "checkins": {
                "reaccion": self.bd.ultimo_checkin(dia, "reaccion", astronauta_id),
                "equipo": self.bd.ultimo_checkin(dia, "equipo", astronauta_id),
                "animo": self.bd.ultimo_checkin(dia, "animo", astronauta_id),
            },
            "conexion_orquestador": self.bd.leer_estado("conexion_orquestador", {"ok": True, "detalle": ""}),
            "retraso_enlace_min": RETRASO_ENLACE_MIN,
        }

    def exportar_csv(self, astronauta_id: str | None = None) -> str:
        """Historial hasta el día actual en CSV (una fila por día).

        La columna ``dia_mision`` va primero para no romper el formato anterior;
        ``astronauta_id`` se añade en segundo lugar.
        """
        astronauta_id = astronauta_id or self.astronauta_activo
        dia_actual = self.dia_actual
        registros, sospechosos = self.registros_validados(astronauta_id)
        niveles = {fila["dia"]: fila for fila in self.bd.historial(dia_actual, astronauta_id)}
        claves = list(self.ajustes.catalogo.keys())
        salida = io.StringIO()
        escritor = csv.writer(salida)
        escritor.writerow(["# " + AVISO])
        escritor.writerow(["dia_mision", "astronauta_id"] + claves
                          + ["nivel_global", "modo", "alertas", "datos_sospechosos"])
        for dia in range(1, dia_actual + 1):
            resultado = self.bd.evaluacion(dia, astronauta_id) or {}
            alertas = "|".join(a["id"] for a in resultado.get("alertas", []))
            fila = niveles.get(dia, {})
            escritor.writerow(
                [dia, astronauta_id]
                + ["" if (registros.get(dia) or {}).get(c) is None else registros[dia].get(c) for c in claves]
                + [fila.get("nivel_global", ""), fila.get("modo", ""), alertas,
                   "|".join(f"{s['indicador']}={s['valor_leido']:g}" for s in sospechosos.get(dia, []))])
        return salida.getvalue()

    # ------------------------------------------------------------------
    # Entrada de datos
    # ------------------------------------------------------------------
    def _actualizar_hoy(self, cambios: dict, astronauta_id: str | None = None):
        astronauta_id = astronauta_id or self.astronauta_activo
        dia = self.dia_actual
        registro = self.bd.registros(astronauta_id).get(dia) or {
            "indicadores": {clave: None for clave in self.ajustes.catalogo}, "manuales": []}
        registro["indicadores"].update(cambios)
        self.bd.guardar_registro(dia, registro["indicadores"], registro["manuales"] + list(cambios),
                                 astronauta_id)

    async def registrar_manual(self, nuevos: dict, astronauta_id: str | None = None) -> dict:
        astronauta_id = astronauta_id or self.astronauta_activo
        aceptados, errores = calculo.validar_indicadores(nuevos, self.ajustes.catalogo)
        if errores:
            raise ErrorDatos(" ".join(errores))
        if not aceptados:
            raise ErrorDatos("No se recibió ningún indicador.")
        self._actualizar_hoy(aceptados, astronauta_id)
        await self._datos_cambiaron(astronauta_id=astronauta_id)
        return await self.estado(astronauta_id)

    async def checkin_animo(self, valor, astronauta_id: str | None = None) -> dict:
        astronauta_id = astronauta_id or self.astronauta_activo
        if not calculo.es_numero(valor) or not 1 <= valor <= 5:
            raise ErrorDatos("El ánimo va de 1 a 5.")
        self._actualizar_hoy({"animo": float(round(valor))}, astronauta_id)
        self.bd.guardar_checkin(self.dia_actual, "animo", {"valor": int(round(valor))}, astronauta_id)
        await self._datos_cambiaron(astronauta_id=astronauta_id)
        return await self.estado(astronauta_id)

    async def checkin_reaccion(self, tiempos_ms, astronauta_id: str | None = None) -> dict:
        """Prueba corta de vigilancia: se guarda la mediana de los tiempos de reacción."""
        astronauta_id = astronauta_id or self.astronauta_activo
        validos = [float(t) for t in (tiempos_ms or []) if calculo.es_numero(t) and 100 <= t <= 2000]
        if len(validos) < 3:
            raise ErrorDatos("La prueba necesita al menos 3 reacciones válidas.")
        mediana = round(statistics.median(validos))
        self._actualizar_hoy({"tiempo_reaccion_ms": float(mediana)}, astronauta_id)
        self.bd.guardar_checkin(self.dia_actual, "reaccion", {
            "mediana_ms": mediana, "intentos": len(validos),
            "lapsos": sum(1 for t in validos if t > 500),   # reacciones muy lentas
        }, astronauta_id)
        await self._datos_cambiaron(astronauta_id=astronauta_id)
        return await self.estado(astronauta_id)

    async def checkin_equipo(self, respuestas: dict, astronauta_id: str | None = None) -> dict:
        """Encuesta semanal del equipo: 3 preguntas, escala 1-5 (5 = mejor)."""
        astronauta_id = astronauta_id or self.astronauta_activo
        claves = ("comunicacion", "conflictos", "carga")
        valores = [respuestas.get(c) for c in claves]
        if not all(calculo.es_numero(v) and 1 <= v <= 5 for v in valores):
            raise ErrorDatos("Responde las 3 preguntas con un valor de 1 a 5.")
        cohesion = round(sum(valores) / 3.0, 1)
        self._actualizar_hoy({"cohesion_equipo": cohesion}, astronauta_id)
        self.bd.guardar_checkin(self.dia_actual, "equipo",
                                {**{c: int(v) for c, v in zip(claves, valores)}, "cohesion": cohesion},
                                astronauta_id)
        await self._datos_cambiaron(astronauta_id=astronauta_id)
        return await self.estado(astronauta_id)

    def marcar_paso(self, alerta_id: str, paso_id: str, hecho: bool,
                    astronauta_id: str | None = None) -> dict:
        astronauta_id = astronauta_id or self.astronauta_activo
        self.bd.marcar_paso(self.dia_actual, alerta_id, paso_id, hecho, astronauta_id)
        self._invalidar_cache()
        return {"pasos_hechos": self.bd.pasos_hechos(self.dia_actual, astronauta_id)}

    # ------------------------------------------------------------------
    # Controles de la demo
    # ------------------------------------------------------------------
    async def fijar_dia(self, dia) -> dict:
        dia = self._validar_dia(dia)
        self.bd.guardar_estado("dia_actual", dia)
        self._invalidar_cache()
        await self.evaluar_dia(dia, self.astronauta_activo)   # siempre se reevalúa
        return await self.estado()

    async def reevaluar(self) -> dict:
        await self.evaluar_dia(self.dia_actual, self.astronauta_activo)
        return await self.estado()

    async def evento_solar(self, activo: bool) -> dict:
        self.bd.guardar_estado("evento_solar_dia", self.dia_actual if activo else None)
        await self._datos_cambiaron(todos=True)
        return await self.estado()

    async def sensor_defectuoso(self, activo: bool, tipo: str = "imposible",
                                indicador: str | None = None) -> dict:
        """Simula que un sensor falla hoy (valor imposible, salto brusco o valor congelado)."""
        dia = self.dia_actual
        config = self.ajustes.sensores
        previa = self.bd.leer_estado("sensor_defectuoso")
        afectados = [dia]
        if previa:
            try:
                afectados += sensores.dias_de_la_falla(previa, config)
            except sensores.ErrorFalla:
                pass
        nueva = None
        if activo:
            nueva = {"dia": dia, "tipo": tipo,
                     "indicador": indicador or (config.get("demo") or {}).get("indicador", "fc_reposo")}
            try:
                afectados += sensores.dias_de_la_falla(nueva, config)
            except sensores.ErrorFalla as error:
                raise ErrorDatos(str(error))
        self.bd.guardar_estado("sensor_defectuoso", nueva)
        await self._datos_cambiaron(desde=min(afectados), todos=True)
        return await self.estado()

    async def caida_laptop2(self, activa: bool) -> dict:
        aceptado = await self.cliente.caida_laptop2(activa)
        if not aceptado:
            raise ErrorDatos("No se pudo avisar al orquestador (Laptop 3): no responde.")
        # La caída cambia el modo de toda la tripulación: las evaluaciones
        # guardadas de otros astronautas ya no reflejan la red actual.
        self.bd.borrar_evaluaciones_desde(self.dia_actual)
        self._invalidar_cache()
        await self.evaluar_dia(self.dia_actual, self.astronauta_activo)
        return await self.estado()

    async def enlace_tierra(self) -> dict:
        """Simula el enlace con la Tierra: la cola de informes del activo se marca enviada."""
        astronauta_id = self.astronauta_activo
        pendientes = {}
        for informe in self.bd.informes(astronauta_id=astronauta_id):
            if informe["estado"] == "pendiente":
                contenido = informe["contenido"]
                contenido["acciones_tomadas"] = self._acciones_tomadas(informe["dia"], astronauta_id)
                pendientes[informe["id"]] = contenido
        enviados = self.bd.marcar_informes_enviados(pendientes)
        self.bd.guardar_estado("ultimo_enlace", {
            "momento": ahora(), "enviados": enviados, "retraso_min": RETRASO_ENLACE_MIN})
        log.info("Enlace con la Tierra simulado: %d informe(s) enviado(s).", enviados)
        return await self.estado()

    async def reiniciar(self) -> dict:
        self._cargar_guion()
        await self.cliente.caida_laptop2(False)   # si la Laptop 3 no responde, no pasa nada
        return await self.estado()

    async def cambiar_activo(self, astronauta_id: str) -> dict:
        """Cambia el astronauta que muestra el tablero principal (solo demo)."""
        self.perfil_de(astronauta_id)
        self.bd.guardar_estado("astronauta_activo", astronauta_id)
        self._invalidar_cache()
        return await self.estado(astronauta_id)

    # ------------------------------------------------------------------
    # Vista de tripulación e índice de preparación
    # ------------------------------------------------------------------
    def _preparacion_de(self, astronauta_id: str, dia: int, registros: dict,
                        sospechosos: dict) -> dict:
        clave = (astronauta_id, dia, self._cache_version)
        if clave in self._preparacion_cache:
            return self._preparacion_cache[clave]
        perfil = self.perfiles[astronauta_id]
        entrada = self._entrada_con(astronauta_id, dia, registros, sospechosos)
        evaluacion = motor_reglas.evaluar(entrada, self._config_reglas)
        niveles = {clave_ind: estado["nivel"] for clave_ind, estado in evaluacion["semaforo"].items()}
        base = calculo.linea_base(perfil, dia, registros)
        resultado = aptitud.calcular_preparacion(
            perfil, dia, registros, niveles, base, evaluacion["nivel"],
            len(sospechosos.get(dia, [])), self._config_preparacion)
        resultado["_evaluacion"] = evaluacion
        resultado["_base"] = base
        self._preparacion_cache[clave] = resultado
        return resultado

    def _riesgo_modelos_pct(self, astronauta_id: str, dia: int):
        resultado = self.bd.evaluacion(dia, astronauta_id)
        if not resultado:
            return None
        riesgos = [
            m["respuesta"]["riesgo"] for m in resultado.get("junta", [])
            if m.get("respuesta") and m["respuesta"].get("confianza", 0) >= 0.60
        ]
        return round(max(riesgos) * 100) if riesgos else None

    def _resumen_astronauta(self, astronauta_id: str, dia: int) -> dict:
        perfil = self.perfiles[astronauta_id]
        registros, sospechosos = self.registros_validados(astronauta_id)
        prep = self._preparacion_de(astronauta_id, dia, registros, sospechosos)
        evaluacion = prep["_evaluacion"]

        sparkline = []
        for d in range(1, dia + 1):
            if d not in registros:
                sparkline.append(None)
                continue
            p = self._preparacion_de(astronauta_id, d, registros, sospechosos)
            sparkline.append(p["preparacion_pct"])
        validos = [v for v in sparkline if v is not None]
        if prep["preparacion_pct"] is None or not registros.get(dia):
            tendencia = "sin_dato"
        elif len(validos) >= 2:
            delta = validos[-1] - validos[-2]
            tendencia = "estable" if abs(delta) <= 2 else ("sube" if delta > 0 else "baja")
        else:
            tendencia = "sin_dato"

        indicadores_clave = {
            clave: {
                "valor": (registros.get(dia) or {}).get(clave),
                "nivel": (evaluacion["semaforo"].get(clave) or {}).get("nivel", "sin_dato"),
            }
            for clave in self._config_preparacion["principales"]
        }
        return {
            "id": astronauta_id,
            "nombre": perfil["astronauta"]["nombre"],
            "rol": perfil["astronauta"]["rol"],
            "nivel": evaluacion["nivel"],
            "preparacion_pct": prep["preparacion_pct"],
            "desglose": prep["desglose"],
            "cobertura": prep["cobertura"],
            "tendencia": tendencia,
            "riesgo_modelos_pct": self._riesgo_modelos_pct(astronauta_id, dia),
            "estado": prep["estado"],
            "sparkline": sparkline,
            "indicadores_clave": indicadores_clave,
            "alertas": [
                {"id": a["id"], "titulo": a["titulo"], "nivel": a["nivel"],
                 "protocolo_id": a["protocolo_id"]}
                for a in evaluacion["alertas"]
            ],
            "pesos": prep["pesos"],
            "motivo": prep["motivo"],
        }

    def _fila_error(self, astronauta_id: str, error: Exception) -> dict:
        """Fila de respaldo si un astronauta falla: la tabla sigue mostrando a los demás."""
        perfil = self.perfiles[astronauta_id]
        log.exception("No se pudo resumir a %s: %s", astronauta_id, error)
        return {
            "id": astronauta_id, "nombre": perfil["astronauta"]["nombre"],
            "rol": perfil["astronauta"]["rol"], "nivel": "sin_dato",
            "preparacion_pct": None, "desglose": None, "cobertura": 0.0,
            "tendencia": "sin_dato", "riesgo_modelos_pct": None, "estado": "error",
            "sparkline": [], "indicadores_clave": {}, "alertas": [],
            "pesos": {}, "motivo": "No se pudo calcular este astronauta; el resto sigue disponible.",
        }

    def _equipo(self, filas: list, dia: int) -> dict:
        niveles = {nivel: 0 for nivel in ("verde", "amarillo", "naranja", "rojo")}
        for fila in filas:
            if fila["nivel"] in niveles:
                niveles[fila["nivel"]] += 1
        con_indice = [f for f in filas if f["preparacion_pct"] is not None]
        promedio = round(sum(f["preparacion_pct"] for f in con_indice) / len(con_indice)) if con_indice else None
        cobertura_media = round(sum(f["cobertura"] for f in filas) / len(filas), 2) if filas else 0.0

        conteo_debil = {}
        for fila in filas:
            for clave, datos in (fila.get("indicadores_clave") or {}).items():
                # Solo cuentan los niveles realmente observados: un dato que falta
                # no debe convertir su indicador en "el más débil del equipo".
                if datos["nivel"] in ("amarillo", "naranja", "rojo"):
                    conteo_debil[clave] = conteo_debil.get(clave, 0) + 1
        debil = max(conteo_debil, key=conteo_debil.get) if conteo_debil else None

        ordenados = sorted(con_indice, key=lambda f: f["preparacion_pct"], reverse=True)
        return {
            "total": len(filas),
            "niveles": niveles,
            "promedio_preparacion": promedio,
            "mejor": ordenados[0]["id"] if ordenados else None,
            "menor": ordenados[-1]["id"] if ordenados else None,
            "cobertura_media": cobertura_media,
            "indicador_mas_debil": debil,
        }

    async def tripulacion(self, dia: int | None = None) -> dict:
        """Vista general de la tripulación. Solo reglas locales; no llama al orquestador."""
        dia = self._validar_dia(dia if dia is not None else self.dia_actual)
        momento = time.monotonic()
        cache = self._cache_tripulacion.get(dia)
        if cache and cache[0] == self._cache_version and momento - cache[1] < 30:
            return cache[2]

        filas = []
        for astronauta_id in self.roster_ids:
            try:
                filas.append(self._resumen_astronauta(astronauta_id, dia))
            except Exception as error:   # un astronauta que falla no tumba a los demás
                filas.append(self._fila_error(astronauta_id, error))
        filas = aptitud.ordenar_filas(filas)
        for posicion, fila in enumerate(filas, start=1):
            fila["posicion"] = posicion if fila["preparacion_pct"] is not None else None
        conexion = self.bd.leer_estado("conexion_orquestador", {"ok": False, "detalle": ""})
        datos = {
            "dia_mision": dia,
            "equipo": self._equipo(filas, dia),
            "astronautas": filas,
            "origen": "reglas-locales",
            "degradado": not bool(conexion.get("ok")),
            "conexion_orquestador": conexion,
            "aviso": AVISO + " La vista general usa solo reglas locales; el riesgo de los "
                              "modelos se muestra aparte y no entra en el índice.",
        }
        validar("tripulacion", datos)
        self._cache_tripulacion[dia] = (self._cache_version, momento, datos)
        return datos

    async def detalle_tripulacion(self, astronauta_id: str, dia: int | None = None) -> dict:
        """Detalle individual. Intenta el orquestador con un tiempo máximo corto (4 s).

        Si la Laptop 3 no responde, cae al respaldo local y lo indica en ``origen``.
        """
        perfil = self.perfil_de(astronauta_id)
        dia = self._validar_dia(dia if dia is not None else self.dia_actual)
        resultado = self.bd.evaluacion(dia, astronauta_id)
        if resultado is None:
            resultado = await self.evaluar_dia(dia, astronauta_id, tiempo_max_s=4.0, reintentos=0)

        registros, sospechosos = self.registros_validados(astronauta_id)
        resumen = self._resumen_astronauta(astronauta_id, dia)
        base = calculo.linea_base(perfil, dia, registros)
        claves = list(self.ajustes.catalogo.keys())
        series, dias = calculo.tendencias(registros, dia, claves)
        catalogo = self.ajustes.catalogo
        indicadores = []
        semaforo = resultado.get("semaforo_indicadores") or {}
        for clave in claves:
            ficha = catalogo.get(clave, {})
            estado = semaforo.get(clave) or {}
            indicadores.append({
                "clave": clave,
                "nombre": ficha.get("nombre", clave),
                "unidad": ficha.get("unidad", ""),
                "valor": (registros.get(dia) or {}).get(clave),
                "nivel": estado.get("nivel", "sin_dato"),
                "linea_base": base.get(clave),
            })
        datos = {
            "astronauta": {"id": astronauta_id, "nombre": perfil["astronauta"]["nombre"],
                           "rol": perfil["astronauta"]["rol"]},
            "dia_mision": dia,
            "nivel_global": resultado.get("nivel_global", resumen["nivel"]),
            "origen": resultado.get("origen", "respaldo-local"),
            "modo": resultado.get("modo", "degradado"),
            "explicacion": resultado.get("explicacion_global", ""),
            "preparacion": resumen,
            "alertas": resultado.get("alertas", []),
            "junta": resultado.get("junta", []),
            "protocolos": resultado.get("protocolos", {}),
            "sensores_sospechosos": resultado.get("sensores_sospechosos") or sospechosos.get(dia, []),
            "calidad": {
                "cobertura": resumen["cobertura"],
                "estado": resumen["estado"],
                "sospechosos_hoy": len(sospechosos.get(dia, [])),
                "nota": ("Datos suficientes para comparar." if resumen["estado"] == "ok"
                         else "Faltan datos suficientes: el índice no se muestra como un cero."),
            },
            "tendencias": {clave: series.get(clave, []) for clave in claves},
            "dias_tendencia": dias,
            "indicadores": indicadores,
            "riesgo_modelos_pct": resumen["riesgo_modelos_pct"],
            "aviso": AVISO + " No es una evaluación médica ni una decisión de aptitud.",
        }
        validar("detalle_tripulacion", datos)
        return datos

    # ------------------------------------------------------------------
    # Reloj inteligente (simulación web)
    # ------------------------------------------------------------------
    def _campos_reloj(self) -> list:
        campos = []
        for clave in CAMPOS_RELOJ:
            ficha = self.ajustes.catalogo.get(clave)
            if not ficha or not ficha.get("editable"):
                continue
            campos.append({
                "clave": clave, "nombre": ficha["nombre"], "unidad": ficha["unidad"],
                "minimo": ficha["minimo"], "maximo": ficha["maximo"], "paso": ficha["paso"],
                "decimales": ficha.get("decimales", 0), "icono": ficha.get("icono", "sin_dato"),
                "principal": bool(ficha.get("principal")),
            })
        return campos

    def _riesgo_reloj(self, astronauta_id: str, dia: int, nivel: str) -> int:
        modelos = self._riesgo_modelos_pct(astronauta_id, dia)
        return modelos if modelos is not None else RIESGO_POR_NIVEL.get(nivel, 8)

    def _pasos_de(self, resultado: dict, alerta: dict, astronauta_id: str, dia: int) -> list:
        protocolo = (resultado.get("protocolos") or {}).get(alerta.get("protocolo_id"))
        if not protocolo:
            return []
        hechos = set(self.bd.pasos_hechos(dia, astronauta_id).get(alerta["id"], []))
        return [{"id": paso["id"], "texto": paso["texto"], "hecho": paso["id"] in hechos}
                for paso in protocolo["pasos"]]

    async def estado_reloj(self, astronauta_id: str) -> dict:
        """Estado compacto para el reloj. No llama al orquestador en cada sondeo."""
        perfil = self.perfil_de(astronauta_id)
        dia = self.dia_actual
        resultado = self.bd.evaluacion(dia, astronauta_id)
        if resultado is None:
            resultado = await self.evaluar_dia(dia, astronauta_id, tiempo_max_s=3.5, reintentos=0)

        registros, sospechosos = self.registros_validados(astronauta_id)
        hoy = registros.get(dia) or {}
        base = calculo.linea_base(perfil, dia, registros)
        claves = list(self.ajustes.catalogo.keys())
        indicadores = {clave: hoy.get(clave) for clave in claves}
        series, dias = calculo.tendencias(registros, dia, PRINCIPALES_TENDENCIA_RELOJ)

        proyeccion = []
        for clave in PRINCIPALES_TENDENCIA_RELOJ:
            ficha = self.ajustes.catalogo.get(clave, {})
            proy = calculo.proyeccion_lineal(
                series.get(clave, []), dias,
                decimales=int(ficha.get("decimales", 0)),
                minimo=ficha.get("minimo"), maximo=ficha.get("maximo"),
                linea_base=base.get(clave),
                horizonte=int(self._config_preparacion.get("proyeccion_horizonte_dias", 14)),
                max_puntos=int(self._config_preparacion.get("proyeccion_max_puntos", 7)))
            if proy is None:
                proy = {
                    "valor_24h": None, "direccion": "sin_dato", "pendiente": None,
                    "dias_para_base": None, "metodo": calculo.METODO_PROYECCION,
                    "aviso": calculo.AVISO_PROYECCION, "puntos": 0,
                }
            proyeccion.append({**proy, "indicador": clave})

        sin_datos = not any(calculo.es_numero(valor) for valor in hoy.values())
        alertas = resultado.get("alertas", [])
        alertas_reloj = []
        for alerta in alertas:
            pasos = self._pasos_de(resultado, alerta, astronauta_id, dia)
            pendiente = next((p for p in pasos if not p["hecho"]), None)
            alertas_reloj.append({
                "id": alerta["id"], "titulo": alerta.get("titulo", alerta["id"]),
                "nivel": alerta["nivel"], "causa": alerta.get("causa_en_lenguaje_simple", ""),
                "consecuencia": alerta.get("consecuencia", ""),
                "protocolo_id": alerta.get("protocolo_id", "general"),
                "pasos": pasos,
                "siguiente_paso": pendiente,
            })
        principal = alertas_reloj[0] if alertas_reloj else None
        # La evaluación guardada puede ser de antes de una caída: el estado de
        # conexión global manda para no mostrar "completo" cuando ya no lo está.
        estado_conexion = self.bd.leer_estado("conexion_orquestador", {"ok": True, "detalle": ""})
        orquestador_ok = bool(estado_conexion.get("ok", True)) and resultado.get("origen") == "orquestador"
        modo = resultado.get("modo", "degradado") if orquestador_ok else "degradado"
        datos_sospechosos = resultado.get("sensores_sospechosos") or sospechosos.get(dia, [])
        nivel = resultado.get("nivel_global", "verde")
        datos = {
            "astronauta": {"id": astronauta_id, "nombre": perfil["astronauta"]["nombre"],
                           "rol": perfil["astronauta"]["rol"]},
            "dia_mision": dia,
            "actualizado": ahora(),
            "conexion": {
                "orquestador": orquestador_ok,
                "modelos": modo == "completo",
                "modo": modo,
            },
            "nivel_global": nivel,
            "riesgo_pct": self._riesgo_reloj(astronauta_id, dia, nivel),
            "explicacion": ("No hay datos registrados para este astronauta hoy."
                            if sin_datos else resultado.get("explicacion_global", "")),
            "sin_datos": sin_datos,
            "alerta_principal": principal,
            "alertas": alertas_reloj,
            "tendencia": {clave: series.get(clave, []) for clave in PRINCIPALES_TENDENCIA_RELOJ},
            "proyeccion": proyeccion,
            "datos_sospechosos": datos_sospechosos,
            "indicadores": indicadores,
            "linea_base": base,
            "campos": self._campos_reloj(),
            "roster": self.roster(),
            "aviso": AVISO_RELOJ,
        }
        validar("estado_reloj", datos)
        return datos

    def _validar_lectura(self, lectura: dict) -> tuple[str, str, dict]:
        try:
            validar("lectura_reloj", lectura)
        except ErrorContrato as error:
            raise ErrorDatos(str(error))
        astronauta_id = lectura["astronauta_id"]
        self.perfil_de(astronauta_id)
        try:
            datetime.fromisoformat(str(lectura["capturado_en"]).replace("Z", "+00:00"))
        except ValueError:
            raise ErrorDatos("capturado_en debe ser una fecha ISO 8601 válida.")
        aceptados, errores = calculo.validar_indicadores(
            {clave: valor for clave, valor in lectura["indicadores"].items()}, self.ajustes.catalogo)
        if errores:
            raise ErrorDatos(" ".join(errores))
        if not aceptados:
            raise ErrorDatos("La lectura no trae ningún indicador.")
        return lectura["lectura_id"], astronauta_id, aceptados

    async def _aplicar_lectura(self, lectura: dict) -> dict:
        lectura_id, astronauta_id, aceptados = self._validar_lectura(lectura)
        dia = self.dia_actual
        previa = self.bd.lectura_guardada(lectura_id)
        if previa is not None:
            estado = await self.estado_reloj(astronauta_id)
            return {
                "aceptado": True, "lectura_id": lectura_id, "astronauta_id": astronauta_id,
                "dia_mision": previa["dia"], "nivel_global": estado["nivel_global"],
                "estado_reloj": estado, "repetida": True,
            }

        registro = self.bd.registros(astronauta_id).get(dia) or {
            "indicadores": {clave: None for clave in self.ajustes.catalogo}, "manuales": []}
        registro["indicadores"].update(aceptados)
        # El reloj es un sensor simulado: NO marca los datos como ingresados a mano,
        # para que la validación de sensores siga aplicando (saltos, congelados, rango).
        self.bd.guardar_registro(dia, registro["indicadores"], registro["manuales"], astronauta_id)
        self.bd.guardar_lectura(lectura_id, astronauta_id, dia, lectura["capturado_en"], aceptados)

        await self.evaluar_dia(dia, astronauta_id, tiempo_max_s=4.0, reintentos=0)
        estado = await self.estado_reloj(astronauta_id)
        datos = {
            "aceptado": True, "lectura_id": lectura_id, "astronauta_id": astronauta_id,
            "dia_mision": dia, "nivel_global": estado["nivel_global"],
            "estado_reloj": estado, "repetida": False,
        }
        validar("respuesta_lectura_reloj", datos)
        return datos

    async def registrar_lectura_reloj(self, cuerpo: dict) -> dict:
        """Aplica una lectura o un lote pequeño. Idempotente por ``lectura_id``."""
        if isinstance(cuerpo, dict) and isinstance(cuerpo.get("lecturas"), list):
            if not 1 <= len(cuerpo["lecturas"]) <= 20:
                raise ErrorDatos("El lote debe traer entre 1 y 20 lecturas.")
            # Validar todo antes de aplicar: un lote con un dato malo no deja
            # medio lote aplicado.
            for lectura in cuerpo["lecturas"]:
                self._validar_lectura(lectura)
            resultados = [await self._aplicar_lectura(lectura) for lectura in cuerpo["lecturas"]]
            lote = {"aceptado": all(r["aceptado"] for r in resultados), "resultados": resultados}
            validar("respuesta_lote_reloj", lote)
            return lote
        return await self._aplicar_lectura(cuerpo)
