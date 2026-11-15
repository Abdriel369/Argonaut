"""Validación de sensores: corre ANTES del motor de reglas y de los modelos.

Tres chequeos por indicador (límites de ejemplo en config/sensores.toml):
  a) rango posible:    el valor está fuera de lo que el cuerpo o el sensor pueden dar;
  b) cambio brusco:    cambió demasiado respecto a la última lectura válida;
  c) valor congelado:  lleva demasiados días marcando exactamente lo mismo.

Una lectura que falla queda como "dato sospechoso": se excluye del cálculo (pasa a
None, igual que un dato que falta) y se guarda el motivo para avisar a la persona.
No se corrige ni se sustituye por otro valor: el sistema no inventa datos.

Sin base de datos ni red: todo recibe datos y devuelve datos.
"""

MOTIVOS = ("fuera_de_rango", "cambio_brusco", "valor_congelado")

# Tipo de fallo del panel de demo -> motivo que debe detectar la validación.
TIPOS_FALLA = {"imposible": "fuera_de_rango", "salto": "cambio_brusco", "congelado": "valor_congelado"}


class ErrorFalla(ValueError):
    """El fallo de demo pedido no se puede simular; el mensaje es apto para mostrar."""


def _numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _limite(limites: dict, clave: str):
    """Límite configurado, o None si falta o vale 0 (chequeo desactivado)."""
    valor = limites.get(clave)
    return valor if _numero(valor) and valor > 0 else None


# --------------------------------------------------------------------------
# Validación
# --------------------------------------------------------------------------

def validar(registros: dict, manuales: dict, config: dict) -> tuple[dict, dict]:
    """Revisa todas las lecturas y aparta las sospechosas.

    registros: {dia: {indicador: valor}}   lecturas tal como llegan (None = sin dato)
    manuales:  {dia: [indicadores]}        datos que una persona ingresó a mano ese día
    config:    contenido de config/sensores.toml

    Devuelve (registros sin los datos sospechosos, {dia: {indicador: ficha}}).
    La ficha dice el motivo y los números necesarios para explicarlo.

    El estado de un día solo depende de ese día y de los anteriores: lo que se
    mostró un día no cambia por lo que pase después.
    """
    validados = {dia: dict(indicadores) for dia, indicadores in registros.items()}
    sospechosos = {}
    for indicador, limites in (config.get("indicadores") or {}).items():
        minimo, maximo = limites.get("minimo"), limites.get("maximo")
        cambio_maximo = _limite(limites, "cambio_maximo")
        dias_congelado = _limite(limites, "dias_congelado")

        ultima_valida = None      # última lectura válida, de sensor o a mano
        ultima_de_sensor = None   # última lectura válida que vino del sensor
        racha_valor, racha_dias, racha_ultimo_dia = None, 0, None

        for dia in sorted(registros):
            valor = registros[dia].get(indicador)
            if not _numero(valor):
                continue
            a_mano = indicador in (manuales.get(dia) or [])

            # Días seguidos con exactamente el mismo valor (para el chequeo c).
            if racha_valor == valor and racha_ultimo_dia == dia - 1:
                racha_dias += 1
            else:
                racha_valor, racha_dias = valor, 1
            racha_ultimo_dia = dia

            ficha = None
            if (_numero(minimo) and valor < minimo) or (_numero(maximo) and valor > maximo):
                ficha = {"motivo": "fuera_de_rango", "minimo": minimo, "maximo": maximo}
            elif not a_mano and cambio_maximo is not None:
                # Se compara con la última lectura válida del sensor y con el último dato
                # válido (que puede ser uno confirmado a mano). Solo es sospechosa si se
                # aleja demasiado de las dos referencias.
                referencias = [r for r in (ultima_de_sensor, ultima_valida) if r is not None]
                if referencias and all(abs(valor - r) > cambio_maximo for r in referencias):
                    cercana = min(referencias, key=lambda r: abs(valor - r))
                    ficha = {"motivo": "cambio_brusco", "valor_anterior": float(cercana),
                             "cambio_maximo": float(cambio_maximo)}
            if ficha is None and not a_mano and dias_congelado is not None and racha_dias >= dias_congelado:
                ficha = {"motivo": "valor_congelado", "dias": racha_dias}

            if ficha is None:
                ultima_valida = valor
                if not a_mano:
                    ultima_de_sensor = valor
                continue
            validados[dia][indicador] = None   # se excluye del cálculo
            sospechosos.setdefault(dia, {})[indicador] = {
                "indicador": indicador, "valor_leido": float(valor), **ficha}
    return validados, sospechosos


# --------------------------------------------------------------------------
# Simulación de un sensor defectuoso (panel de demo)
# --------------------------------------------------------------------------

def dias_de_la_falla(falla: dict, config: dict) -> list:
    """Días cuya lectura cambia con el fallo simulado. Lanza ErrorFalla si no se puede simular."""
    indicador, tipo, dia = falla.get("indicador"), falla.get("tipo"), falla.get("dia")
    limites = (config.get("indicadores") or {}).get(indicador)
    if limites is None:
        raise ErrorFalla(f"'{indicador}' no tiene validación de sensor configurada.")
    if tipo not in TIPOS_FALLA:
        raise ErrorFalla("El tipo de fallo debe ser imposible, salto o congelado.")
    if tipo == "imposible":
        if not _numero(limites.get("maximo")):
            raise ErrorFalla("Ese sensor no tiene un máximo posible configurado.")
        return [dia]
    if tipo == "salto":
        if _limite(limites, "cambio_maximo") is None:
            raise ErrorFalla("Ese sensor no tiene chequeo de cambio brusco.")
        if dia < 2:
            raise ErrorFalla("Para simular un salto brusco hace falta al menos un día anterior.")
        return [dia]
    dias = _limite(limites, "dias_congelado")
    if dias is None:
        raise ErrorFalla("Ese sensor no tiene chequeo de valor congelado.")
    dias = int(dias)
    if dia < dias:
        raise ErrorFalla(f"Para simular un valor congelado hacen falta al menos {dias} días de misión.")
    return list(range(dia - dias + 1, dia + 1))


def aplicar_falla(registros: dict, manuales: dict, falla: dict | None, config: dict) -> dict:
    """Devuelve los registros con las lecturas que daría el sensor defectuoso.

    Un dato ingresado a mano tiene prioridad sobre el sensor: si la persona volvió a
    medir y lo anotó, ese día no se toca. Si el fallo ya no se puede simular
    (por ejemplo, faltan datos), no cambia nada.
    """
    if not falla:
        return registros
    try:
        dias = dias_de_la_falla(falla, config)
    except ErrorFalla:
        return registros
    indicador, tipo, dia = falla["indicador"], falla["tipo"], falla["dia"]
    limites = config["indicadores"][indicador]
    demo = config.get("demo") or {}
    if any(d not in registros for d in dias):
        return registros

    if tipo == "imposible":
        lecturas = {dia: float(round(limites["maximo"] * demo.get("factor_imposible", 1.25)))}
    elif tipo == "salto":
        anterior = (registros.get(dia - 1) or {}).get(indicador)
        if not _numero(anterior):
            return registros
        salto = limites["cambio_maximo"] * demo.get("factor_salto", 1.7)
        valor = anterior + salto
        if _numero(limites.get("maximo")) and valor > limites["maximo"]:
            valor = anterior - salto     # si no cabe hacia arriba, el salto es hacia abajo
        lecturas = {dia: float(round(valor))}
    else:
        trabado = registros[dias[0]].get(indicador)
        if not _numero(trabado):
            return registros
        lecturas = {d: trabado for d in dias}

    salida = {d: dict(indicadores) for d, indicadores in registros.items()}
    for d, valor in lecturas.items():
        if indicador not in (manuales.get(d) or []):
            salida[d][indicador] = valor
    return salida
