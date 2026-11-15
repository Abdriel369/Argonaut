"""Cálculos puros del backend: línea base, desviaciones, tendencias y validación.

Sin base de datos ni red: todo recibe datos y devuelve datos, para poder probarlo fácil.
"""


def es_numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def indicadores_del_guion(guion: dict, dia: int) -> dict:
    """Valores del guion determinista para un día (1 = primer día)."""
    return {clave: float(valores[dia - 1]) for clave, valores in guion["indicadores"].items()}


def linea_base(perfil: dict, dia: int, registros: dict) -> dict:
    """Línea base personal vigente en 'dia'.

    Días de adaptación: la base pre-vuelo tal cual.
    Después: se recalibra mezclando la base pre-vuelo con la media de los días de adaptación.
    'registros' es {dia: indicadores}.
    """
    base = dict(perfil["linea_base_prevuelo"])
    ajuste = perfil["recalibracion"]
    dias_adaptacion = ajuste["dias_adaptacion"]
    if dia <= dias_adaptacion:
        return base
    peso = ajuste["peso_prevuelo"]
    for indicador in ajuste["indicadores"]:
        observados = [
            registros[d][indicador] for d in range(1, dias_adaptacion + 1)
            if d in registros and es_numero(registros[d].get(indicador))
        ]
        if observados:
            media = sum(observados) / len(observados)
            base[indicador] = round(peso * base[indicador] + (1.0 - peso) * media, 3)
    return base


def desviaciones(indicadores: dict, base: dict) -> dict:
    """Diferencia de hoy contra la base: absoluta y porcentual."""
    salida = {}
    for indicador, referencia in base.items():
        valor = indicadores.get(indicador)
        if not es_numero(valor):
            salida[indicador] = None
            continue
        salida[indicador] = {
            "absoluta": round(valor - referencia, 3),
            "porcentual": round(100.0 * (valor - referencia) / referencia, 2) if referencia else None,
        }
    return salida


def tendencias(registros: dict, dia: int, claves) -> tuple[dict, list]:
    """Últimos 7 días terminando en 'dia'. Devuelve ({indicador: [valores]}, [días])."""
    dias = [d for d in range(max(1, dia - 6), dia + 1)]
    series = {
        clave: [
            (registros[d].get(clave) if d in registros and es_numero(registros[d].get(clave)) else None)
            for d in dias
        ]
        for clave in claves
    }
    return series, dias


def validar_indicadores(nuevos: dict, catalogo: dict) -> tuple[dict, list]:
    """Valida datos ingresados a mano contra el catálogo. Devuelve (aceptados, errores)."""
    aceptados, errores = {}, []
    for clave, valor in nuevos.items():
        ficha = catalogo.get(clave)
        if ficha is None:
            errores.append(f"'{clave}' no es un indicador conocido.")
        elif not ficha.get("editable"):
            errores.append(f"{ficha['nombre']} no se ingresa a mano.")
        elif valor is None:
            aceptados[clave] = None   # borrar el dato: se mostrará "sin dato"
        elif not es_numero(valor):
            errores.append(f"{ficha['nombre']}: el valor debe ser un número.")
        elif not ficha["minimo"] <= valor <= ficha["maximo"]:
            errores.append(f"{ficha['nombre']}: debe estar entre {ficha['minimo']:g} y "
                           f"{ficha['maximo']:g} {ficha['unidad']}.")
        else:
            aceptados[clave] = float(valor)
    return aceptados, errores


AVISO_PROYECCION = ("Proyección heurística de los últimos días. No es un pronóstico "
                    "médico ni un diagnóstico.")
METODO_PROYECCION = "regresión lineal simple, últimos 7 días"


def proyeccion_lineal(serie, dias=None, decimales: int = 0, minimo=None, maximo=None,
                      linea_base=None, horizonte: int = 14, max_puntos: int = 7):
    """Proyección heurística a 24 h con una recta de mínimos cuadrados.

    - Usa hasta los últimos ``max_puntos`` valores válidos (ignora None).
    - Con menos de 3 puntos devuelve None: no se inventa una tendencia.
    - Nunca proyecta fuera del rango físico del indicador.
    - ``dias_para_base`` solo se informa si el cruce con la línea base cae dentro
      del horizonte y en la dirección de la pendiente.

    Es una herramienta de demo, no un modelo predictivo ni una evaluación médica.
    """
    pares = []
    for i, valor in enumerate(serie or []):
        if es_numero(valor):
            x = dias[i] if dias and i < len(dias) and es_numero(dias[i]) else i + 1
            pares.append((float(x), float(valor)))
    pares = pares[-max_puntos:]
    if len(pares) < 3:
        return None

    n = len(pares)
    suma_x = sum(x for x, _ in pares)
    suma_y = sum(y for _, y in pares)
    suma_xx = sum(x * x for x, _ in pares)
    suma_xy = sum(x * y for x, y in pares)
    denominador = n * suma_xx - suma_x * suma_x
    pendiente = (n * suma_xy - suma_x * suma_y) / denominador if denominador else 0.0
    intercepto = (suma_y - pendiente * suma_x) / n

    ultimo_x, ultimo_y = pares[-1]
    valor_24h = intercepto + pendiente * (ultimo_x + 1)
    if es_numero(minimo):
        valor_24h = max(minimo, valor_24h)
    if es_numero(maximo):
        valor_24h = min(maximo, valor_24h)
    valor_24h = round(valor_24h, decimales)

    paso = 0.5 * (10 ** -decimales)
    umbral = max(paso, 0.02 * abs(ultimo_y))
    if abs(pendiente) <= umbral:
        direccion = "estable"
    else:
        direccion = "sube" if pendiente > 0 else "baja"

    dias_para_base = None
    if es_numero(linea_base) and abs(pendiente) > 1e-12:
        distancia = linea_base - ultimo_y
        if abs(distancia) <= paso:
            dias_para_base = 0
        else:
            cruce = distancia / pendiente
            if 0 < cruce <= horizonte:
                dias_para_base = max(1, round(cruce))

    return {
        "indicador": None,   # lo completa quien llama, que conoce el catálogo
        "valor_24h": valor_24h,
        "direccion": direccion,
        "pendiente": round(pendiente, 3),
        "dias_para_base": dias_para_base,
        "metodo": METODO_PROYECCION,
        "aviso": AVISO_PROYECCION,
        "puntos": n,
    }


def exposicion_musculo_hueso(registros: dict, dia: int, plan_ejercicio: float, proteccion: float) -> dict:
    """ESTIMACIÓN (no medición) de la exposición de músculos y huesos a la microgravedad.

    Crece con cada día de misión y baja con el ejercicio cumplido: un día sin
    ejercicio suma 1; un día con el plan completo suma solo (1 - proteccion).
    """
    acumulada = 0.0
    for d in range(1, dia + 1):
        ejercicio = (registros.get(d) or {}).get("ejercicio_min")
        cumplimiento = min(1.0, ejercicio / plan_ejercicio) if es_numero(ejercicio) and plan_ejercicio else 0.0
        acumulada += 1.0 - proteccion * cumplimiento
    porcentaje = 100.0 * acumulada / dia
    if porcentaje <= 35:
        nivel, texto = "verde", "Baja"
    elif porcentaje <= 60:
        nivel, texto = "amarillo", "Media"
    else:
        nivel, texto = "naranja", "Alta"
    return {
        "nivel": nivel, "texto": texto,
        "dias_equivalentes_sin_ejercicio": round(acumulada, 1),
        "dias_mision": dia,
        "porcentaje": round(porcentaje),
        "es_estimacion": True,
        "nota": "Exposición estimada a partir de los días de misión y del ejercicio cumplido. No es una medición.",
    }
