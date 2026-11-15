"""Motor de reglas explicables (funciones puras, sin red ni estado).

Tres niveles, todos configurados en config/umbrales.toml:
  1. Por indicador contra la línea base personal, con persistencia.
  2. Por combinación de indicadores (fatiga, aislamiento, radiación...).
  3. Por contexto de misión (ventana de adaptación, dosis acumulada, día de misión).

La misma función sirve en la Laptop 3 (orquestador) y como respaldo en la
Laptop 1 cuando el orquestador no responde. No diagnostica: avisa por riesgo.

Datos sospechosos: si la entrada trae 'sensores_sospechosos' (lecturas que la
validación de sensores de la Laptop 1 apartó), esos indicadores se excluyen del
cálculo y su semáforo queda en "sospechoso". Un sensor roto no puede activar una
regla, y las alertas que dependen de otras señales no cambian.
"""

import tomllib
from pathlib import Path

from comun.niveles import indice, maximo, subir

RUTA_CONFIG = Path(__file__).resolve().parent / "config" / "umbrales.toml"


def cargar_config(ruta: Path | None = None) -> dict:
    """Lee los umbrales (valores de ejemplo, con fuentes por citar en comentarios)."""
    with open(ruta or RUTA_CONFIG, "rb") as archivo:
        return tomllib.load(archivo)


# --------------------------------------------------------------------------
# Utilidades pequeñas
# --------------------------------------------------------------------------

def _numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


# --------------------------------------------------------------------------
# Datos sospechosos (sensor que parece fallar)
# --------------------------------------------------------------------------

# Qué indicadores usa cada regla de combinación. Sirve para decir qué reglas se
# quedan hoy sin un dato cuando su sensor falla.
ENTRADAS_COMBINACION = {
    "FATIGA": ("sueno_h", "estres", "ejercicio_min", "animo"),
    "AISLAMIENTO": ("animo", "cohesion_equipo"),
    "PERDIDA_MUSCULAR_OSEA": ("ejercicio_min",),
    "RADIACION": ("tasa_dosis_usv_h", "fc_reposo", "temperatura"),
    "CARDIOVASCULAR": ("fc_reposo", "hrv", "sueno_h"),
    "ENERGIA_BAJA": ("ingesta_pct",),
}


def sospechosos(entrada: dict) -> dict:
    """{indicador: ficha} de las lecturas de hoy marcadas como 'dato sospechoso'."""
    return {
        ficha["indicador"]: ficha
        for ficha in (entrada.get("sensores_sospechosos") or [])
        if isinstance(ficha, dict) and isinstance(ficha.get("indicador"), str)
    }


def excluir_sospechosos(entrada: dict) -> dict:
    """Entrada sin las lecturas sospechosas de hoy: quedan como 'sin dato'.

    Un dato sospechoso se excluye del cálculo. Ni las reglas ni los modelos lo ven,
    aunque quien envió la entrada no lo hubiera borrado. Si no hay ninguno devuelve
    la misma entrada, sin copiarla ni cambiarla.
    """
    marcados = sospechosos(entrada)
    if not marcados:
        return entrada
    limpia = dict(entrada)
    limpia["indicadores"] = {**(entrada.get("indicadores") or {}), **{clave: None for clave in marcados}}
    desviaciones = dict(entrada.get("desviaciones_vs_base") or {})
    tendencias = dict(entrada.get("tendencias_7d") or {})
    for clave in marcados:
        if clave in desviaciones:
            desviaciones[clave] = None
        serie = list(tendencias.get(clave) or [])
        if serie:
            serie[-1] = None          # el último valor de la serie es el de hoy
            tendencias[clave] = serie
    limpia["desviaciones_vs_base"] = desviaciones
    limpia["tendencias_7d"] = tendencias
    return limpia


def _reglas_afectadas(indicador: str, config: dict) -> list:
    """Reglas que usan este indicador y hoy se evalúan sin él."""
    afectadas = []
    regla = config["indicadores"].get(indicador)
    if regla:
        afectadas.append(regla["alerta_id"])
    afectadas += [nombre for nombre, entradas in ENTRADAS_COMBINACION.items() if indicador in entradas]
    return afectadas


def _formato(valor: float, decimales: int) -> str:
    return f"{valor:.{decimales}f}"


def _serie(entrada: dict, indicador: str) -> list:
    """Valores de los últimos días terminando en hoy (puede contener None)."""
    serie = list((entrada.get("tendencias_7d") or {}).get(indicador) or [])
    hoy = (entrada.get("indicadores") or {}).get(indicador)
    if not serie:
        serie = [hoy]
    return serie


def _dias_seguidos(serie: list, cumple) -> int:
    """Cuántos días seguidos, contando hacia atrás desde hoy, cumplen la condición."""
    dias = 0
    for valor in reversed(serie):
        if not _numero(valor) or not cumple(valor):
            break
        dias += 1
    return dias


def _referencia(entrada: dict, indicador: str, regla: dict):
    if regla["referencia"] == "base":
        return (entrada.get("linea_base") or {}).get(indicador)
    if regla["referencia"] == "plan":
        return (entrada.get("plan") or {}).get(indicador)
    return None


def _nivel_valor(valor: float, referencia, regla: dict, factor: float) -> str:
    """Nivel de UN valor según la regla del indicador (nivel 1)."""
    nivel = "verde"
    for nombre in ("amarillo", "naranja", "rojo"):
        umbral = regla.get(nombre)
        if umbral is None:
            continue
        if regla["medida"] == "valor":
            supera = valor >= umbral if regla["sentido"] == "alto" else valor <= umbral
        else:
            if not _numero(referencia) or referencia == 0:
                return "verde"
            diferencia = valor - referencia
            if regla["medida"] == "porcentual":
                diferencia = 100.0 * diferencia / referencia
            magnitud = diferencia if regla["sentido"] == "alto" else -diferencia
            supera = magnitud >= umbral * factor
        if supera:
            nivel = nombre
    return nivel


# --------------------------------------------------------------------------
# Nivel 1: por indicador
# --------------------------------------------------------------------------

def _umbral_en_unidades(referencia, regla: dict, factor: float):
    """Valor del indicador a partir del cual empieza el nivel amarillo (para dibujar la gráfica)."""
    umbral = regla.get("amarillo")
    if umbral is None:
        return None
    if regla["medida"] == "valor":
        return float(umbral)
    if not _numero(referencia):
        return None
    distancia = umbral * factor
    if regla["medida"] == "porcentual":
        distancia = referencia * distancia / 100.0
    return round(referencia + distancia if regla["sentido"] == "alto" else referencia - distancia, 3)


def _evaluar_indicador(entrada: dict, indicador: str, regla: dict, factor_adaptacion: float,
                       sospechoso: dict | None = None) -> dict:
    valor = (entrada.get("indicadores") or {}).get(indicador)
    referencia = _referencia(entrada, indicador, regla)
    estado = {
        "nombre": regla["nombre"], "unidad": regla["unidad"], "valor": valor,
        "referencia": referencia, "nivel": "sin_dato", "dias_fuera": 0,
        "sube_por_persistencia": False, "desviacion": None, "desviacion_pct": None,
        "tendencia": "sin_dato", "frase": None, "sentido": regla["sentido"],
        "umbral_amarillo": None,
    }
    if sospechoso:
        # El sensor parece fallar: no se evalúa. Se guarda lo que marcó, solo para mostrarlo.
        estado.update(nivel="sospechoso", valor=None, valor_leido=sospechoso.get("valor_leido"),
                      motivo_sospecha=sospechoso.get("motivo"))
        return estado
    if not _numero(valor):
        return estado   # un sensor sin dato no rompe nada: se muestra "sin dato"

    factor = factor_adaptacion if regla.get("tolerante") and regla["medida"] != "valor" else 1.0
    estado["umbral_amarillo"] = _umbral_en_unidades(referencia, regla, factor)
    nivel = _nivel_valor(valor, referencia, regla, factor)

    # Persistencia: días seguidos fuera de rango (contra la línea base de hoy).
    serie = _serie(entrada, indicador)
    dias_fuera = _dias_seguidos(serie, lambda v: _nivel_valor(v, referencia, regla, factor) != "verde")
    sube = nivel in ("amarillo", "naranja") and dias_fuera >= regla.get("persistencia_dias", 99)
    if sube:
        nivel = subir(nivel)

    if _numero(referencia):
        estado["desviacion"] = round(valor - referencia, 2)
        estado["desviacion_pct"] = round(100.0 * (valor - referencia) / referencia, 1) if referencia else None

    anteriores = [v for v in serie[:-1] if _numero(v)]
    if anteriores:
        cambio = valor - anteriores[-1]
        minimo_visible = 0.02 * abs(anteriores[-1]) if anteriores[-1] else 0.01
        estado["tendencia"] = "estable" if abs(cambio) <= minimo_visible else ("sube" if cambio > 0 else "baja")
    else:
        estado["tendencia"] = "estable"

    decimales = regla.get("decimales", 0)
    estado["frase"] = regla["frase"].format(
        valor=_formato(valor, decimales),
        referencia=_formato(referencia, decimales) if _numero(referencia) else "—",
    )
    estado.update(nivel=nivel, dias_fuera=dias_fuera, sube_por_persistencia=sube)
    return estado


# --------------------------------------------------------------------------
# Nivel 2: combinaciones (cada función devuelve una alerta o None)
# --------------------------------------------------------------------------

def _alerta(id_, regla, nivel, implicados, hechos) -> dict:
    return {
        "id": id_, "origen": "combinacion", "titulo": regla["titulo"], "nivel": nivel,
        "indicadores_implicados": implicados, "hechos": hechos,
        "consecuencia": regla["consecuencia"], "protocolo_id": regla["protocolo_id"],
    }


def regla_fatiga(entrada: dict, regla: dict, semaforo: dict):
    """Sueño bajo la base 3 días + estrés alto + ejercicio alto. Rojo si además cae el ánimo."""
    ind, base, plan = entrada["indicadores"], entrada.get("linea_base") or {}, entrada.get("plan") or {}
    sueno, estres, ejercicio = ind.get("sueno_h"), ind.get("estres"), ind.get("ejercicio_min")
    if not all(_numero(v) for v in (sueno, estres, ejercicio, base.get("sueno_h"), base.get("estres"))):
        return None
    limite_sueno = base["sueno_h"] - regla["margen_sueno_h"]
    dias_bajo = _dias_seguidos(_serie(entrada, "sueno_h"), lambda v: v < limite_sueno)
    estres_alto = estres >= base["estres"] + regla["estres_sobre_base"]
    meta = plan.get("ejercicio_min")
    ejercicio_alto = _numero(meta) and meta > 0 and 100.0 * ejercicio / meta >= regla["ejercicio_pct_plan"]
    if not (dias_bajo >= regla["dias_sueno_bajo"] and estres_alto and ejercicio_alto):
        return None
    hechos = [
        f"llevas {dias_bajo} días durmiendo menos de lo normal (anoche {sueno:.1f} h)",
        semaforo["estres"]["frase"],
        f"entrenaste más de lo planeado ({ejercicio:.0f} min)",
    ]
    implicados = ["sueno_h", "estres", "ejercicio_min"]
    nivel = "amarillo"
    animo = ind.get("animo")
    if _numero(animo) and _numero(base.get("animo")) and animo <= base["animo"] - regla["caida_animo"]:
        nivel = "rojo"
        hechos.append(f"además tu ánimo bajó a {animo:.0f} de 5")
        implicados.append("animo")
    return _alerta("FATIGA", regla, nivel, implicados, hechos)


def regla_aislamiento(entrada: dict, regla: dict, semaforo: dict):
    """Ánimo bajando 4 días + cohesión del equipo baja."""
    serie = [v for v in _serie(entrada, "animo") if _numero(v)][-regla["dias_animo_bajando"]:]
    cohesion = entrada["indicadores"].get("cohesion_equipo")
    if len(serie) < regla["dias_animo_bajando"] or not _numero(cohesion):
        return None
    bajando = all(b <= a for a, b in zip(serie, serie[1:])) and serie[-1] < serie[0]
    if not (bajando and cohesion <= regla["cohesion_baja"]):
        return None
    hechos = [f"tu ánimo lleva {len(serie)} días bajando",
              f"el equipo reporta poca unión ({cohesion:.1f} de 5)"]
    return _alerta("AISLAMIENTO", regla, "naranja", ["animo", "cohesion_equipo"], hechos)


def regla_perdida_muscular_osea(entrada: dict, regla: dict, semaforo: dict):
    """Ejercicio por debajo del 50 % del plan durante 5 días."""
    meta = (entrada.get("plan") or {}).get("ejercicio_min")
    if not _numero(meta) or meta <= 0:
        return None
    dias = _dias_seguidos(_serie(entrada, "ejercicio_min"),
                          lambda v: 100.0 * v / meta < regla["ejercicio_pct_plan"])
    # Contexto (nivel 3): en misiones largas el cuerpo ya está más expuesto; basta un día menos.
    ajuste = 1 if entrada["dia_mision"] >= regla["dias_mision_larga"] else 0
    if dias >= regla["dias"] - ajuste:
        nivel = "naranja"
    elif dias >= regla["dias_aviso"] - ajuste:
        nivel = "amarillo"
    else:
        return None
    hechos = [f"llevas {dias} días con menos de la mitad del ejercicio planeado"]
    return _alerta("PERDIDA_MUSCULAR_OSEA", regla, nivel, ["ejercicio_min"], hechos)


def regla_radiacion(entrada: dict, regla: dict, semaforo: dict):
    """Tasa de dosis alta o evento solar. Rojo si además el pulso o la temperatura están elevados."""
    ind, base = entrada["indicadores"], entrada.get("linea_base") or {}
    tasa = ind.get("tasa_dosis_usv_h")
    evento = bool((entrada.get("contexto") or {}).get("evento_solar"))
    tasa_alta = _numero(tasa) and tasa >= regla["tasa_alta_usv_h"]
    if not (evento or tasa_alta):
        return None
    hechos, implicados = [], ["tasa_dosis_usv_h"]
    if evento:
        hechos.append("hay una tormenta solar en curso")
    if _numero(tasa) and (tasa_alta or evento):
        hechos.append(f"la radiación que llega ahora es de {tasa:.0f} µSv/h")
    nivel = "naranja"
    fc, temperatura = ind.get("fc_reposo"), ind.get("temperatura")
    if _numero(fc) and _numero(base.get("fc_reposo")) and \
            100.0 * (fc - base["fc_reposo"]) / base["fc_reposo"] >= regla["fc_sobre_base_pct"]:
        nivel = "rojo"
        hechos.append(f"tu pulso en reposo está elevado ({fc:.0f})")
        implicados.append("fc_reposo")
    if _numero(temperatura) and _numero(base.get("temperatura")) and \
            temperatura - base["temperatura"] >= regla["temperatura_sobre_base"]:
        nivel = "rojo"
        hechos.append(f"tu temperatura está elevada ({temperatura:.1f} °C)")
        implicados.append("temperatura")
    return _alerta("RADIACION", regla, nivel, implicados, hechos)


def regla_cardiovascular(entrada: dict, regla: dict, semaforo: dict):
    """Pulso en reposo +15 % + HRV baja + sueño pobre."""
    ind, base = entrada["indicadores"], entrada.get("linea_base") or {}
    fc, hrv = ind.get("fc_reposo"), ind.get("hrv")
    sueno = [v for v in _serie(entrada, "sueno_h") if _numero(v)][-3:]
    if not (all(_numero(v) for v in (fc, hrv, base.get("fc_reposo"), base.get("hrv"), base.get("sueno_h")))
            and sueno):
        return None
    fc_alta = 100.0 * (fc - base["fc_reposo"]) / base["fc_reposo"] >= regla["fc_sobre_base_pct"]
    hrv_baja = 100.0 * (hrv - base["hrv"]) / base["hrv"] <= -regla["hrv_bajo_base_pct"]
    sueno_pobre = sum(sueno) / len(sueno) <= base["sueno_h"] - regla["sueno_pobre_h"]
    if not (fc_alta and hrv_baja and sueno_pobre):
        return None
    hechos = [semaforo["fc_reposo"]["frase"], semaforo["hrv"]["frase"], "llevas varios días durmiendo poco"]
    return _alerta("CARDIOVASCULAR", regla, "naranja", ["fc_reposo", "hrv", "sueno_h"], hechos)


def regla_energia_baja(entrada: dict, regla: dict, semaforo: dict):
    """Ingesta por debajo del 60 % de lo planeado."""
    ingesta = entrada["indicadores"].get("ingesta_pct")
    if not _numero(ingesta) or ingesta >= regla["ingesta_pct"]:
        return None
    dias = _dias_seguidos(_serie(entrada, "ingesta_pct"), lambda v: v < regla["ingesta_pct"])
    nivel = "naranja" if dias >= regla["dias_para_naranja"] else "amarillo"
    hechos = [f"comiste el {ingesta:.0f} % de lo planeado"
              + (f" y ya son {dias} días seguidos" if dias > 1 else "")]
    return _alerta("ENERGIA_BAJA", regla, nivel, ["ingesta_pct"], hechos)


COMBINACIONES = {
    "FATIGA": regla_fatiga,
    "AISLAMIENTO": regla_aislamiento,
    "PERDIDA_MUSCULAR_OSEA": regla_perdida_muscular_osea,
    "RADIACION": regla_radiacion,
    "CARDIOVASCULAR": regla_cardiovascular,
    "ENERGIA_BAJA": regla_energia_baja,
}


# --------------------------------------------------------------------------
# Nivel 3: contexto de misión
# --------------------------------------------------------------------------

def regla_dosis_acumulada(entrada: dict, regla: dict):
    dosis = (entrada.get("contexto") or {}).get("dosis_acumulada")
    if not _numero(dosis):
        return None
    nivel = "verde"
    for nombre in ("amarillo", "naranja", "rojo"):
        if dosis >= regla[nombre]:
            nivel = nombre
    if nivel == "verde":
        return None
    alerta = _alerta(regla["alerta_id"], regla, nivel, ["dosis_acumulada_msv"],
                     [f"ya acumulas {dosis:.0f} mSv de radiación en esta misión"])
    alerta["origen"] = "contexto"
    return alerta


# --------------------------------------------------------------------------
# Evaluación completa
# --------------------------------------------------------------------------

def evaluar(entrada: dict, config: dict) -> dict:
    """Aplica los tres niveles de reglas a la entrada del orquestador.

    Devuelve: nivel global, semáforo por indicador, alertas (con hechos en lenguaje
    sencillo), señales para el enrutamiento y la lista de reglas activadas.
    """
    marcados = sospechosos(entrada)
    entrada = excluir_sospechosos(entrada)   # un dato sospechoso no entra en ningún cálculo
    general = config["general"]
    en_adaptacion = entrada["dia_mision"] <= general["dias_adaptacion"]
    factor = general["factor_tolerancia_adaptacion"] if en_adaptacion else 1.0

    # Nivel 1
    semaforo = {
        indicador: _evaluar_indicador(entrada, indicador, regla, factor, marcados.get(indicador))
        for indicador, regla in config["indicadores"].items()
    }
    alertas_indicador = []
    senales = []
    for indicador, estado in semaforo.items():
        if estado["nivel"] in ("sin_dato", "sospechoso", "verde"):
            continue
        regla = config["indicadores"][indicador]
        senales.append(f"{indicador}:{regla['sentido']}")
        hechos = [estado["frase"]]
        if estado["sube_por_persistencia"]:
            hechos.append(f"ya son {estado['dias_fuera']} días seguidos")
        alertas_indicador.append({
            "id": regla["alerta_id"], "origen": "indicador", "titulo": regla["titulo"],
            "nivel": estado["nivel"], "indicadores_implicados": [indicador], "hechos": hechos,
            "consecuencia": regla["consecuencia"], "protocolo_id": regla["protocolo_id"],
        })

    # Nivel 2
    alertas = []
    for nombre, funcion in COMBINACIONES.items():
        alerta = funcion(entrada, config["combinaciones"][nombre], semaforo)
        if alerta:
            alertas.append(alerta)
            senales.append(f"regla:{nombre}")

    # Nivel 3
    if (entrada.get("contexto") or {}).get("evento_solar"):
        senales.append("evento_solar")
    alerta_dosis = regla_dosis_acumulada(entrada, config["contexto"]["dosis_acumulada"])
    if alerta_dosis:
        alertas.append(alerta_dosis)
        senales.append("dosis_acumulada")

    # Una combinación "absorbe" las alertas sueltas de sus indicadores para no repetir avisos,
    # y nunca queda por debajo del nivel de lo que absorbe.
    cubiertos = {}
    for alerta in alertas:
        if alerta["origen"] == "combinacion":
            for indicador in alerta["indicadores_implicados"]:
                cubiertos.setdefault(indicador, []).append(alerta)
    for suelta in alertas_indicador:
        duenas = cubiertos.get(suelta["indicadores_implicados"][0])
        if duenas:
            principal = max(duenas, key=lambda a: indice(a["nivel"]))
            principal["nivel"] = maximo(principal["nivel"], suelta["nivel"])
        else:
            alertas.append(suelta)

    alertas.sort(key=lambda a: -indice(a["nivel"]))
    return {
        "nivel": maximo(*[a["nivel"] for a in alertas]),
        "semaforo": semaforo,
        "alertas": alertas,
        "senales": sorted(set(senales)),
        "reglas_activadas": [a["id"] for a in alertas],
        "ventana_adaptacion": en_adaptacion,
        "sensores_sospechosos": [
            {**ficha, "reglas_afectadas": _reglas_afectadas(indicador, config)}
            for indicador, ficha in marcados.items()
        ],
    }
