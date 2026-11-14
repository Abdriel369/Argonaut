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
