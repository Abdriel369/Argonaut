"""Índice de preparación (Readiness) del prototipo.

Es una heurística de demo, comparable y reproducible, calculada SOLO con las
reglas locales. La opinión de los modelos se muestra aparte y no entra en el
índice. No es una probabilidad calibrada ni una evaluación médica.

Fórmula (Anexo B del encargo, pesos en config/tripulacion.toml):

    cobertura = días_con_datos / día

    C_indicadores = media del puntaje de los indicadores principales con dato
    C_plan        = 100 × (0.40·sueño/base + 0.30·ejercicio/plan + 0.30·ingesta/100)
    C_seguridad   = 100 × (1 − riesgo del peor nivel de las reglas)
    C_datos       = 100 × (0.70·cobertura + 0.30·(1 − min(1, sospechosos/3)))

    preparacion = 0.40·C_indicadores + 0.25·C_plan + 0.20·C_seguridad + 0.15·C_datos

Topes: rojo → 45, naranja → 70. Sin cobertura suficiente (o con más de dos
indicadores principales sin dato) el índice es null y el estado es
"sin_datos_suficientes": nunca se muestra un cero engañoso.
"""


def _numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _redondear(valor, decimales=1):
    return None if valor is None else round(valor, decimales)


def ordenar_filas(filas: list) -> list:
    """Orden de la vista de tripulación.

    Índice descendente; quien no tiene datos suficientes va al final (nunca como
    un cero). Desempate: cobertura descendente y luego nombre.
    """
    return sorted(filas, key=lambda f: (
        f.get("preparacion_pct") is None,
        -(f.get("preparacion_pct") or 0),
        -(f.get("cobertura") or 0),
        f.get("nombre") or "",
    ))


def calcular_preparacion(perfil: dict, dia: int, registros: dict, niveles: dict,
                         linea_base: dict, nivel_reglas: str, sospechosos_hoy: int,
                         config: dict) -> dict:
    """Calcula el índice y su desglose para un astronauta y un día.

    ``registros`` es {día: indicadores} ya validado por la capa de sensores.
    ``niveles`` es {indicador: nivel} del semáforo de las reglas locales.
    """
    principales = list(config["principales"])
    indicadores = registros.get(dia) or {}

    dias_con_datos = sum(
        1 for d in range(1, dia + 1)
        if d in registros and any(_numero(v) for v in (registros[d] or {}).values())
    )
    cobertura = (dias_con_datos / dia) if dia else 0.0

    faltantes = sum(1 for clave in principales if not _numero(indicadores.get(clave)))

    puntajes = []
    for clave in principales:
        if not _numero(indicadores.get(clave)):
            continue
        nivel = niveles.get(clave, "verde")
        if nivel in ("sin_dato", "sospechoso"):
            continue
        puntaje = config.get(f"puntaje_{nivel}")
        if puntaje is not None:
            puntajes.append(float(puntaje))
    c_indicadores = sum(puntajes) / len(puntajes) if puntajes else None

    base_sueno = linea_base.get("sueno_h") if linea_base else None
    plan_ejercicio = (perfil.get("plan") or {}).get("ejercicio_min")
    suma_ponderada = 0.0
    peso_disponible = 0.0
    sueno = indicadores.get("sueno_h")
    if _numero(sueno) and _numero(base_sueno) and base_sueno > 0:
        peso = float(config["plan_peso_sueno"])
        suma_ponderada += peso * min(1.0, sueno / base_sueno)
        peso_disponible += peso
    ejercicio = indicadores.get("ejercicio_min")
    if _numero(ejercicio) and _numero(plan_ejercicio) and plan_ejercicio > 0:
        peso = float(config["plan_peso_ejercicio"])
        suma_ponderada += peso * min(1.0, ejercicio / plan_ejercicio)
        peso_disponible += peso
    ingesta = indicadores.get("ingesta_pct")
    if _numero(ingesta):
        peso = float(config["plan_peso_ingesta"])
        suma_ponderada += peso * min(1.0, ingesta / 100.0)
        peso_disponible += peso
    # Si falta un término, se usa el promedio ponderado de los disponibles: no se
    # inventa el valor que falta y los pesos se renormalizan sobre lo que sí hay.
    c_plan = (100.0 * suma_ponderada / peso_disponible) if peso_disponible else None

    riesgo = config.get(f"riesgo_{nivel_reglas}", config["riesgo_verde"])
    c_seguridad = 100.0 * (1.0 - float(riesgo))

    c_datos = 100.0 * (
        0.70 * cobertura + 0.30 * (1.0 - min(1.0, max(0, sospechosos_hoy) / 3.0))
    )

    insuficiente = (
        cobertura < float(config["cobertura_minima"])
        or faltantes > int(config["faltantes_principales_maximos"])
        or c_indicadores is None
        or c_plan is None
    )

    preparacion = None
    if not insuficiente:
        preparacion = (
            float(config["peso_indicadores"]) * c_indicadores
            + float(config["peso_plan"]) * c_plan
            + float(config["peso_seguridad"]) * c_seguridad
            + float(config["peso_datos"]) * c_datos
        )
        if nivel_reglas == "rojo":
            preparacion = min(preparacion, float(config["tope_rojo"]))
        elif nivel_reglas == "naranja":
            preparacion = min(preparacion, float(config["tope_naranja"]))

    return {
        "preparacion_pct": None if preparacion is None else int(round(preparacion)),
        "estado": "sin_datos_suficientes" if insuficiente else "ok",
        "cobertura": round(cobertura, 3),
        "dias_con_datos": dias_con_datos,
        "faltantes_principales": faltantes,
        "sospechosos_hoy": int(sospechosos_hoy),
        "desglose": {
            "indicadores": _redondear(c_indicadores),
            "plan": _redondear(c_plan),
            "seguridad": _redondear(c_seguridad),
            "datos": _redondear(c_datos),
        },
        "pesos": {
            "indicadores": float(config["peso_indicadores"]),
            "plan": float(config["peso_plan"]),
            "seguridad": float(config["peso_seguridad"]),
            "datos": float(config["peso_datos"]),
        },
        "motivo": (
            "Faltan datos suficientes para calcular un índice comparable."
            if insuficiente else ""
        ),
    }
