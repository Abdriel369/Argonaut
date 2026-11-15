"""Núcleo del orquestador: la "junta médica de modelos".

Flujo de una evaluación:
  1. Reglas explicables detectan posible riesgo (tres niveles).
  2. Una tabla de enrutamiento decide a qué especialistas consultar.
  3. Se consulta en paralelo al gateway de la Laptop 2 y al modelo solar local.
  4. Fusión: las reglas mandan; un especialista puede subir una alerta un escalón.
  5. Síntesis en lenguaje sencillo + protocolo + escalamiento + informe.

Si la Laptop 2 no responde: MODO DEGRADADO (reglas + modelo solar local).
Este módulo no sabe de HTTP: recibe un "cliente" (ver clientes.py).

Sensores que parecen fallar: los datos sospechosos de la entrada se excluyen antes
del paso 1 y nunca llegan a los modelos (a ellos les falta el dato y baja su
confianza). El resultado lleva un aviso por cada uno; el aviso no cambia el nivel.
"""

import logging
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path

import protocolos as libreria_protocolos
import reglas
from comun import AVISO
from comun.contratos import validar
from comun.niveles import indice, maximo, subir
from orquestador import sintesis
from orquestador.clientes import ESPECIALISTA_LOCAL, ESPECIALISTAS_LAPTOP2
from orquestador.informe import construir_informe

log = logging.getLogger("orquestador")

RUTA_CONFIG = Path(__file__).resolve().parent / "config" / "orquestador.toml"


@dataclass(frozen=True)
class Configuracion:
    reglas: dict
    orquestador: dict


def cargar_configuracion(ruta_reglas: Path | None = None, ruta_orquestador: Path | None = None) -> Configuracion:
    with open(ruta_orquestador or RUTA_CONFIG, "rb") as archivo:
        orquestador = tomllib.load(archivo)
    return Configuracion(reglas=reglas.cargar_config(ruta_reglas), orquestador=orquestador)


def enrutar(senales: list, config: dict) -> dict:
    """Tabla de reglas -> {especialista: [motivos por los que se le consulta]}."""
    convocados = {}
    for ruta in config["rutas"]:
        if ruta["senal"] in senales:
            for especialista in ruta["especialistas"]:
                motivos = convocados.setdefault(especialista, [])
                if ruta["motivo"] not in motivos:
                    motivos.append(ruta["motivo"])
    return convocados


def fusionar(alertas: list, respuestas: dict, config: dict, sin_voto=()) -> list:
    """Combina reglas y especialistas. Las reglas mandan; los modelos solo pueden subir.

    'sin_voto': especialistas cuya opinión hoy no cambia el nivel (les falta un dato
    porque un sensor parece fallar). Se muestran, pero ni suben una alerta ni crean una.
    """
    fusion = config["fusion"]
    especialistas = config["especialistas"]
    resultado = []
    cubiertos = set()
    for alerta in alertas:
        vinculados = [n for n in respuestas if alerta["id"] in especialistas[n]["alertas"]]
        cubiertos.update(vinculados)
        nivel = alerta["nivel"]
        elevadores = [
            n for n in vinculados
            if indice(respuestas[n]["nivel"]) > indice(nivel)
            and respuestas[n]["confianza"] >= fusion["confianza_minima"]
            and n not in sin_voto
        ]
        if elevadores:
            nivel = subir(nivel, fusion["escalones_maximos"])
        resultado.append({**alerta, "nivel_reglas": alerta["nivel"], "nivel": nivel,
                          "especialistas_consultados": vinculados, "elevada_por": elevadores})

    # Un especialista ve riesgo donde las reglas no vieron nada: aviso temprano en amarillo.
    for nombre, respuesta in respuestas.items():
        if nombre in cubiertos or respuesta["nivel"] == "verde" or nombre in sin_voto:
            continue
        if respuesta["confianza"] < fusion["confianza_minima"]:
            continue
        frases = [f["frase"] for f in respuesta["factores"] if f["aporte"] > 0.05][:3]
        resultado.append({
            "id": "SENAL_" + nombre.upper().replace("-", "_"),
            "origen": "especialista",
            "titulo": f"Señal temprana: {especialistas[nombre]['titulo'].lower()}",
            "nivel": "amarillo", "nivel_reglas": "verde",
            "indicadores_implicados": [f["indicador"] for f in respuesta["factores"][:3]],
            "hechos": frases or ["el especialista ve una señal temprana"],
            "consecuencia": "Las reglas no ven riesgo todavía, pero conviene vigilarlo.",
            "protocolo_id": "general",
            "especialistas_consultados": [nombre], "elevada_por": [nombre],
        })
    resultado.sort(key=lambda a: -indice(a["nivel"]))
    return resultado


async def evaluar(entrada: dict, cliente, config: Configuracion, origen: str = "orquestador") -> dict:
    """Evalúa un día de misión y devuelve el resultado final (contrato resultado_final)."""
    validar("entrada_orquestador", entrada)
    # Un dato sospechoso se excluye del cálculo: ni las reglas ni los modelos lo ven.
    entrada = reglas.excluir_sospechosos(entrada)
    cfg = config.orquestador
    consulta_id = f"{entrada['astronauta_id']}-D{entrada['dia_mision']}-{uuid.uuid4().hex[:8]}"

    # 1. Reglas
    evaluacion = reglas.evaluar(entrada, config.reglas)

    # 2. Enrutamiento por tabla
    convocados = enrutar(evaluacion["senales"], cfg)

    # 3. Consultas (con modo degradado si la Laptop 2 no está)
    estado_l2 = await cliente.gateway_disponible()
    if not estado_l2[0]:
        # Reglas + modelo solar local: el especialista de la Laptop 3 se consulta siempre.
        convocados.setdefault(ESPECIALISTA_LOCAL, []).insert(
            0, "Modo degradado: se consulta siempre al especialista local")
    respuestas, fallidos = ({}, {})
    if convocados:
        respuestas, fallidos = await cliente.consultar(consulta_id, list(convocados), entrada, estado_l2)

    no_disponibles = set(fallidos)
    if not estado_l2[0]:
        no_disponibles.update(ESPECIALISTAS_LAPTOP2)
    no_disponibles = [n for n in cfg["especialistas"] if n in no_disponibles]
    modo = "degradado" if no_disponibles else "completo"

    # 4. Fusión
    # Con un dato sospechoso, el especialista al que le faltan datos opina pero no cambia el nivel.
    sin_voto = set()
    if evaluacion["sensores_sospechosos"] and cfg["fusion"].get("sin_voto_con_dato_sospechoso", True):
        sin_voto = {nombre for nombre, respuesta in respuestas.items() if respuesta.get("datos_faltantes")}
    alertas = fusionar(evaluacion["alertas"], respuestas, cfg, sin_voto)
    nivel_global = maximo(*[a["nivel"] for a in alertas])

    # 5. Síntesis, protocolos, junta, escalamiento e informe
    protocolos_usados = {}
    alertas_finales = []
    for alerta in alertas:
        protocolo = libreria_protocolos.obtener(alerta["protocolo_id"])
        protocolos_usados[protocolo["id"]] = protocolo
        alertas_finales.append({
            "id": alerta["id"],
            "titulo": alerta["titulo"],
            "nivel": alerta["nivel"],
            "nivel_reglas": alerta["nivel_reglas"],
            "causa_en_lenguaje_simple": sintesis.causa_simple(alerta),
            "opinion_junta": sintesis.opinion_especialistas(alerta["especialistas_consultados"], respuestas, cfg),
            "indicadores_implicados": alerta["indicadores_implicados"],
            "especialistas_consultados": alerta["especialistas_consultados"],
            "elevada_por": alerta["elevada_por"],
            "protocolo_id": protocolo["id"],
        })

    junta = []
    for nombre, datos in cfg["especialistas"].items():
        miembro = {"especialista": nombre, "titulo": datos["titulo"], "laptop": datos["laptop"],
                   "motivo": "", "respuesta": None}
        if nombre in respuestas:
            miembro.update(estado="respondio", respuesta=respuestas[nombre],
                           motivo="; ".join(convocados.get(nombre, [])),
                           opinion_limitada=nombre in sin_voto)
        elif nombre in no_disponibles:
            miembro.update(estado="no_disponible",
                           motivo=fallidos.get(nombre) or f"Laptop 2 no disponible ({estado_l2[1]})")
        else:
            miembro.update(estado="no_convocado", motivo="Las reglas no vieron motivo para consultarlo.")
        junta.append(miembro)

    # Avisos de equipo: un sensor que parece fallar. No son alertas de salud y no cambian el nivel.
    avisos_sensores = [{**ficha, "aviso": sintesis.aviso_sensor(ficha)}
                       for ficha in evaluacion["sensores_sospechosos"]]

    escalamiento = {"nivel": nivel_global, **cfg["escalamiento"][nivel_global]}
    informe = None
    if indice(nivel_global) >= indice(cfg["informe"]["nivel_minimo"]):
        informe = construir_informe(entrada, evaluacion, alertas_finales, junta, nivel_global,
                                    modo, protocolos_usados, avisos_sensores)

    resultado = {
        "nivel_global": nivel_global,
        "alertas": alertas_finales,
        "modo": modo,
        "especialistas_no_disponibles": no_disponibles,
        "escalamiento": escalamiento,
        "informe_cirujano": informe,
        "explicacion_global": sintesis.explicacion_global(
            nivel_global, alertas_finales, evaluacion["ventana_adaptacion"], modo, len(avisos_sensores)),
        "sensores_sospechosos": avisos_sensores,
        "semaforo_indicadores": evaluacion["semaforo"],
        "junta": junta,
        "protocolos": protocolos_usados,
        "reglas_activadas": evaluacion["reglas_activadas"],
        "ventana_adaptacion": evaluacion["ventana_adaptacion"],
        "respuestas_guardadas": bool(getattr(cliente, "respuestas_guardadas", False)),
        "origen": origen,
        "dia_mision": entrada["dia_mision"],
        "aviso": AVISO,
    }
    validar("resultado_final", resultado)
    log.info("dia=%s nivel=%s modo=%s reglas=%s consultados=%s no_disponibles=%s sospechosos=%s",
             entrada["dia_mision"], nivel_global, modo, evaluacion["reglas_activadas"],
             sorted(respuestas), no_disponibles, [f["indicador"] for f in avisos_sensores])
    return resultado
