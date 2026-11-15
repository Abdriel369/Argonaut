"""Lógica del backend: guion de 7 días, validación de sensores, línea base, evaluación,
informes y controles de demo.

Todos los datos son SIMULADOS. La clase no sabe de HTTP entrante: principal.py
expone estos métodos como API.
"""

import csv
import io
import logging
import statistics

from backend import calculo, sensores
from backend.ajustes import Ajustes
from backend.bd import BaseDatos, ahora
from backend.cliente_orquestador import ClienteOrquestador
from comun import AVISO

log = logging.getLogger("backend")

RETRASO_ENLACE_MIN = 20   # minutos por sentido hasta la Tierra (escenario Marte, valor ilustrativo)


class ErrorDatos(ValueError):
    """Dato rechazado por la validación; el mensaje es apto para mostrar al usuario."""


class Servicio:
    def __init__(self, ajustes: Ajustes, bd: BaseDatos, cliente: ClienteOrquestador):
        self.ajustes = ajustes
        self.bd = bd
        self.cliente = cliente
        if not self.bd.registros():
            self._cargar_guion()

    # ------------------------------------------------------------------
    # Guion y estado básico
    # ------------------------------------------------------------------
    def _cargar_guion(self):
        """Carga los 7 días del guion determinista y vuelve al día 1."""
        self.bd.vaciar()
        for dia in range(1, self.ajustes.dias_guion + 1):
            self.bd.guardar_registro(dia, calculo.indicadores_del_guion(self.ajustes.guion, dia), [])
        self.bd.guardar_estado("dia_actual", 1)
        self.bd.guardar_estado("evento_solar_dia", None)
        self.bd.guardar_estado("sensor_defectuoso", None)
        log.info("Guion de %d días cargado.", self.ajustes.dias_guion)

    @property
    def dia_actual(self) -> int:
        return int(self.bd.leer_estado("dia_actual", 1))

    def registros_efectivos(self, crudos: dict | None = None) -> dict:
        """{dia: indicadores} tal como llegan de los sensores: aplica evento solar, dosis
        acumulada, módulos externos y, si está activo, el sensor defectuoso de la demo.

        Estas lecturas todavía NO están validadas: para calcular hay que usar
        registros_validados().
        """
        crudos = crudos if crudos is not None else self.bd.registros()
        evento_dia = self.bd.leer_estado("evento_solar_dia")
        evento = self.ajustes.perfil["evento_solar"]
        modulos = self.ajustes.perfil["modulos_externos"]
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

    def registros_validados(self) -> tuple[dict, dict]:
        """Capa de validación de sensores: corre ANTES de las reglas y de los modelos.

        Devuelve ({dia: indicadores} con los datos sospechosos apartados (None),
                  {dia: [fichas de los datos sospechosos de ese día]}).
        Todo lo que se calcula después (línea base, tendencias, entrada del orquestador,
        exposición músculo-hueso) parte de estos registros.
        """
        crudos = self.bd.registros()
        manuales = {dia: crudos[dia]["manuales"] for dia in crudos}
        validados, sospechosos = sensores.validar(self.registros_efectivos(crudos), manuales,
                                                  self.ajustes.sensores)
        fichas = {}
        for dia, por_indicador in sospechosos.items():
            fichas[dia] = []
            for indicador, ficha in por_indicador.items():
                catalogo = self.ajustes.catalogo.get(indicador, {})
                fichas[dia].append({**ficha, "nombre": catalogo.get("nombre", indicador),
                                    "unidad": catalogo.get("unidad", "")})
        return validados, fichas

    def construir_entrada(self, dia: int) -> dict:
        """Mensaje para el orquestador (contrato entrada_orquestador).

        Los datos sospechosos van como null y se listan en 'sensores_sospechosos'. Ese campo
        solo se incluye cuando hay alguno: un día normal produce el mismo mensaje de siempre.
        """
        registros, sospechosos = self.registros_validados()
        indicadores = registros[dia]
        base = calculo.linea_base(self.ajustes.perfil, dia, registros)
        series, _ = calculo.tendencias(registros, dia, indicadores.keys())
        evento_dia = self.bd.leer_estado("evento_solar_dia")
        entrada = {
            "astronauta_id": self.ajustes.perfil["astronauta"]["id"],
            "dia_mision": dia,
            "indicadores": indicadores,
            "desviaciones_vs_base": calculo.desviaciones(indicadores, base),
            "tendencias_7d": series,
            "linea_base": base,
            "plan": dict(self.ajustes.perfil["plan"]),
            "contexto": {
                "dosis_acumulada": indicadores.get("dosis_acumulada_msv") or 0.0,
                "evento_solar": evento_dia == dia,
            },
        }
        if sospechosos.get(dia):
            entrada["sensores_sospechosos"] = sospechosos[dia]
        return entrada

    # ------------------------------------------------------------------
    # Evaluación
    # ------------------------------------------------------------------
    async def evaluar_dia(self, dia: int) -> dict:
        """Llama al orquestador (o al respaldo local), guarda todo y devuelve el resultado."""
        entrada = self.construir_entrada(dia)
        resultado, conexion = await self.cliente.evaluar(entrada)
        self.bd.guardar_evaluacion(dia, entrada, resultado)
        if resultado["informe_cirujano"]:
            self.bd.guardar_informe(resultado["informe_cirujano"])
        else:
            self.bd.borrar_informe_pendiente(dia)
        self.bd.guardar_estado("conexion_orquestador", conexion)
        return resultado

    async def _completar_historial(self, hasta_dia: int):
        """Si se saltó de día con el deslizador, evalúa los días intermedios que falten."""
        evaluados = {fila["dia"] for fila in self.bd.historial(hasta_dia)}
        for dia in range(1, hasta_dia):
            if dia not in evaluados:
                await self.evaluar_dia(dia)

    async def _datos_cambiaron(self, desde: int | None = None):
        """Tras cualquier cambio de datos: lo evaluado de hoy en adelante ya no vale.

        'desde' permite invalidar también días anteriores (un sensor congelado cambia
        las lecturas de varios días); estado() los vuelve a evaluar.
        """
        dia = self.dia_actual
        self.bd.borrar_evaluaciones_desde(min(dia, desde) if desde else dia)
        await self.evaluar_dia(dia)

    # ------------------------------------------------------------------
    # Lectura para la interfaz
    # ------------------------------------------------------------------
    def _acciones_tomadas(self, dia: int) -> list:
        """Textos de los pasos de protocolo marcados 'ya lo hice' ese día."""
        resultado = self.bd.evaluacion(dia)
        if not resultado:
            return []
        protocolo_de = {a["id"]: resultado["protocolos"].get(a["protocolo_id"]) for a in resultado["alertas"]}
        acciones = []
        for alerta_id, pasos in self.bd.pasos_hechos(dia).items():
            protocolo = protocolo_de.get(alerta_id)
            if not protocolo:
                continue
            textos = {paso["id"]: paso["texto"] for paso in protocolo["pasos"]}
            acciones += [{"alerta": alerta_id, "paso": textos[p]} for p in pasos if p in textos]
        return acciones

    def _informes(self, hasta_dia: int) -> list:
        informes = self.bd.informes(hasta_dia)
        for informe in informes:
            if informe["estado"] == "pendiente":
                informe["contenido"]["acciones_tomadas"] = self._acciones_tomadas(informe["dia"])
        return informes

    async def estado(self) -> dict:
        """Todo lo que la interfaz necesita para pintar el día actual."""
        dia = self.dia_actual
        resultado = self.bd.evaluacion(dia) or await self.evaluar_dia(dia)
        await self._completar_historial(dia)
        registros, sospechosos = self.registros_validados()
        indicadores = registros[dia]
        base = calculo.linea_base(self.ajustes.perfil, dia, registros)
        series, dias = calculo.tendencias(registros, dia, indicadores.keys())
        perfil = self.ajustes.perfil
        evento_dia = self.bd.leer_estado("evento_solar_dia")
        falla = self.bd.leer_estado("sensor_defectuoso") or {}
        modulos = perfil["modulos_externos"]
        return {
            "aviso": AVISO,
            "astronauta": perfil["astronauta"],
            "dia_actual": dia,
            "dias_totales": self.ajustes.dias_guion,
            "nota_dia": self.ajustes.guion.get("notas", {}).get(str(dia), ""),
            "indicadores": indicadores,
            "datos_manuales": self.bd.registros()[dia]["manuales"],
            "linea_base": base,
            "plan": perfil["plan"],
            "desviaciones_vs_base": calculo.desviaciones(indicadores, base),
            "tendencias_7d": series,
            "dias_tendencia": dias,
            "catalogo": self.ajustes.catalogo,
            "resultado": resultado,
            "evento_solar": {"dia": evento_dia, "activo_hoy": evento_dia == dia},
            # Datos de hoy apartados por la validación de sensores (los indicadores van como null).
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
            "pasos_hechos": self.bd.pasos_hechos(dia),
            "informes": self._informes(dia),
            "ultimo_enlace": self.bd.leer_estado("ultimo_enlace"),
            "historial": self.bd.historial(dia),
            "checkins": {
                "reaccion": self.bd.ultimo_checkin(dia, "reaccion"),
                "equipo": self.bd.ultimo_checkin(dia, "equipo"),
                "animo": self.bd.ultimo_checkin(dia, "animo"),
            },
            "conexion_orquestador": self.bd.leer_estado("conexion_orquestador", {"ok": True, "detalle": ""}),
            "retraso_enlace_min": RETRASO_ENLACE_MIN,
        }

    def exportar_csv(self) -> str:
        """Historial hasta el día actual en CSV (una fila por día)."""
        dia_actual = self.dia_actual
        registros, sospechosos = self.registros_validados()
        niveles = {fila["dia"]: fila for fila in self.bd.historial(dia_actual)}
        claves = list(self.ajustes.catalogo.keys())
        salida = io.StringIO()
        escritor = csv.writer(salida)
        escritor.writerow(["# " + AVISO])
        escritor.writerow(["dia_mision"] + claves + ["nivel_global", "modo", "alertas", "datos_sospechosos"])
        for dia in range(1, dia_actual + 1):
            resultado = self.bd.evaluacion(dia) or {}
            alertas = "|".join(a["id"] for a in resultado.get("alertas", []))
            fila = niveles.get(dia, {})
            escritor.writerow(
                [dia] + ["" if registros[dia].get(c) is None else registros[dia].get(c) for c in claves]
                + [fila.get("nivel_global", ""), fila.get("modo", ""), alertas,
                   "|".join(f"{s['indicador']}={s['valor_leido']:g}" for s in sospechosos.get(dia, []))])
        return salida.getvalue()

    # ------------------------------------------------------------------
    # Entrada de datos
    # ------------------------------------------------------------------
    def _actualizar_hoy(self, cambios: dict):
        dia = self.dia_actual
        registro = self.bd.registros()[dia]
        registro["indicadores"].update(cambios)
        self.bd.guardar_registro(dia, registro["indicadores"], registro["manuales"] + list(cambios))

    async def registrar_manual(self, nuevos: dict) -> dict:
        aceptados, errores = calculo.validar_indicadores(nuevos, self.ajustes.catalogo)
        if errores:
            raise ErrorDatos(" ".join(errores))
        if not aceptados:
            raise ErrorDatos("No se recibió ningún indicador.")
        self._actualizar_hoy(aceptados)
        await self._datos_cambiaron()
        return await self.estado()

    async def checkin_animo(self, valor) -> dict:
        if not calculo.es_numero(valor) or not 1 <= valor <= 5:
            raise ErrorDatos("El ánimo va de 1 a 5.")
        self._actualizar_hoy({"animo": float(round(valor))})
        self.bd.guardar_checkin(self.dia_actual, "animo", {"valor": int(round(valor))})
        await self._datos_cambiaron()
        return await self.estado()

    async def checkin_reaccion(self, tiempos_ms) -> dict:
        """Prueba corta de vigilancia: se guarda la mediana de los tiempos de reacción."""
        validos = [float(t) for t in (tiempos_ms or []) if calculo.es_numero(t) and 100 <= t <= 2000]
        if len(validos) < 3:
            raise ErrorDatos("La prueba necesita al menos 3 reacciones válidas.")
        mediana = round(statistics.median(validos))
        self._actualizar_hoy({"tiempo_reaccion_ms": float(mediana)})
        self.bd.guardar_checkin(self.dia_actual, "reaccion", {
            "mediana_ms": mediana, "intentos": len(validos),
            "lapsos": sum(1 for t in validos if t > 500),   # reacciones muy lentas
        })
        await self._datos_cambiaron()
        return await self.estado()

    async def checkin_equipo(self, respuestas: dict) -> dict:
        """Encuesta semanal del equipo: 3 preguntas, escala 1-5 (5 = mejor)."""
        claves = ("comunicacion", "conflictos", "carga")
        valores = [respuestas.get(c) for c in claves]
        if not all(calculo.es_numero(v) and 1 <= v <= 5 for v in valores):
            raise ErrorDatos("Responde las 3 preguntas con un valor de 1 a 5.")
        cohesion = round(sum(valores) / 3.0, 1)
        self._actualizar_hoy({"cohesion_equipo": cohesion})
        self.bd.guardar_checkin(self.dia_actual, "equipo",
                                {**{c: int(v) for c, v in zip(claves, valores)}, "cohesion": cohesion})
        await self._datos_cambiaron()
        return await self.estado()

    def marcar_paso(self, alerta_id: str, paso_id: str, hecho: bool) -> dict:
        self.bd.marcar_paso(self.dia_actual, alerta_id, paso_id, hecho)
        return {"pasos_hechos": self.bd.pasos_hechos(self.dia_actual)}

    # ------------------------------------------------------------------
    # Controles de la demo
    # ------------------------------------------------------------------
    async def fijar_dia(self, dia) -> dict:
        if not isinstance(dia, int) or not 1 <= dia <= self.ajustes.dias_guion:
            raise ErrorDatos(f"El día de misión va de 1 a {self.ajustes.dias_guion}.")
        self.bd.guardar_estado("dia_actual", dia)
        await self.evaluar_dia(dia)   # siempre se reevalúa: refleja el estado actual de la red
        return await self.estado()

    async def reevaluar(self) -> dict:
        await self.evaluar_dia(self.dia_actual)
        return await self.estado()

    async def evento_solar(self, activo: bool) -> dict:
        self.bd.guardar_estado("evento_solar_dia", self.dia_actual if activo else None)
        await self._datos_cambiaron()
        return await self.estado()

    async def sensor_defectuoso(self, activo: bool, tipo: str = "imposible",
                                indicador: str | None = None) -> dict:
        """Simula que un sensor falla hoy (valor imposible, salto brusco o valor congelado).

        El fallo queda ligado al día en que se activa, igual que el evento solar.
        """
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
        await self._datos_cambiaron(desde=min(afectados))
        return await self.estado()

    async def caida_laptop2(self, activa: bool) -> dict:
        aceptado = await self.cliente.caida_laptop2(activa)
        if not aceptado:
            raise ErrorDatos("No se pudo avisar al orquestador (Laptop 3): no responde.")
        await self.evaluar_dia(self.dia_actual)
        return await self.estado()

    async def enlace_tierra(self) -> dict:
        """Simula el enlace con la Tierra: la cola de informes pendientes se marca como enviada."""
        pendientes = {}
        for informe in self.bd.informes():
            if informe["estado"] == "pendiente":
                contenido = informe["contenido"]
                contenido["acciones_tomadas"] = self._acciones_tomadas(informe["dia"])
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
