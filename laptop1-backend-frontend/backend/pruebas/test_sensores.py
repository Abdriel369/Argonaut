"""Validación de sensores: valor imposible, salto brusco, valor congelado y caso normal.

La capa corre antes de las reglas y de los modelos. Un dato sospechoso se excluye del
cálculo, baja la confianza de los modelos y genera un aviso; nunca sube ni baja por sí
solo el nivel que dan las demás señales.
"""

import asyncio

import pytest

import pila
from backend import sensores
from backend.ajustes import Ajustes
from comun.contratos import errores
from comun.niveles import indice
from fabrica import entrada, servicio_de_prueba

AJUSTES = Ajustes.desde_entorno()
CONFIG = AJUSTES.sensores
HISTORIA = ["verde", "verde", "amarillo", "naranja", "rojo", "amarillo", "verde"]   # ver test_integracion.py


def _guion() -> dict:
    """{dia: indicadores} del guion de 7 días, sin ningún fallo."""
    return servicio_de_prueba().registros_efectivos()


def correr_con_app(funcion, **kwargs):
    async def principal():
        app = pila.crear_pila(**kwargs)
        async with pila.navegador(app) as nav:
            return await funcion(nav)
    return asyncio.run(principal())


# --------------------------------------------------------------------------
# Los tres chequeos (funciones puras)
# --------------------------------------------------------------------------

def test_un_valor_imposible_se_marca_y_se_excluye():
    registros = _guion()
    registros[5]["fc_reposo"] = 250.0
    validados, sospechosos = sensores.validar(registros, {}, CONFIG)
    assert validados[5]["fc_reposo"] is None, "el dato sospechoso no debe entrar en ningún cálculo"
    ficha = sospechosos[5]["fc_reposo"]
    assert ficha["motivo"] == "fuera_de_rango" and ficha["valor_leido"] == 250.0
    assert list(sospechosos) == [5], "los demás días no se tocan"
    assert validados[4]["fc_reposo"] == 69.0


def test_un_salto_brusco_se_marca_aunque_el_valor_sea_posible():
    registros = _guion()
    registros[5]["fc_reposo"] = 128.0      # dentro del rango posible, pero +59 lpm en un día
    validados, sospechosos = sensores.validar(registros, {}, CONFIG)
    ficha = sospechosos[5]["fc_reposo"]
    assert ficha["motivo"] == "cambio_brusco"
    assert ficha["valor_anterior"] == 69.0 and ficha["cambio_maximo"] == 35.0
    assert validados[5]["fc_reposo"] is None
    # Al día siguiente el sensor vuelve a lo normal: se compara con la última lectura válida.
    assert 6 not in sospechosos and validados[6]["fc_reposo"] == 67.0


def test_un_valor_congelado_se_marca_al_llegar_al_limite_de_dias():
    registros = _guion()
    for dia in (2, 3, 4, 5, 6):
        registros[dia]["fc_reposo"] = 64.0     # el día 7 el guion marca 63: el sensor "despierta"
    validados, sospechosos = sensores.validar(registros, {}, CONFIG)
    assert 4 not in sospechosos, "con 3 días iguales todavía no se sospecha"
    assert sospechosos[5]["fc_reposo"]["motivo"] == "valor_congelado"
    assert sospechosos[5]["fc_reposo"]["dias"] == 4
    assert sospechosos[6]["fc_reposo"]["dias"] == 5, "sigue congelado mientras no cambie"
    assert 7 not in sospechosos, "cuando el valor cambia, el sensor vuelve a ser válido"


@pytest.mark.parametrize("evento_dia", [None, 1, 2, 3, 4, 5, 6, 7])
def test_el_guion_normal_no_tiene_falsos_positivos(evento_dia):
    servicio = servicio_de_prueba(evento_dia)
    validados, sospechosos = servicio.registros_validados()
    assert sospechosos == {}, "ningún día del guion (con o sin tormenta solar) debe dar un dato sospechoso"
    assert validados == servicio.registros_efectivos(), "sin fallos la validación no cambia ningún valor"
    for dia in range(1, 8):
        assert "sensores_sospechosos" not in servicio.construir_entrada(dia)


def test_un_dato_ingresado_a_mano_no_se_marca_por_salto():
    # La persona midió y lo anotó: aunque sea un cambio grande, vale (y puede dar su alerta).
    e = entrada(5, sobre={5: {"fc_reposo": 128.0}})
    assert "sensores_sospechosos" not in e and e["indicadores"]["fc_reposo"] == 128.0
    # El mismo valor llegando del sensor sí se marca.
    e = entrada(5, sensor={5: {"fc_reposo": 128.0}})
    assert [s["indicador"] for s in e["sensores_sospechosos"]] == ["fc_reposo"]


def test_tras_un_dato_a_mano_extremo_el_sensor_normal_no_se_marca():
    # Día 3 a mano: 180 lpm. Día 4 el sensor marca 69: cerca de su última lectura propia.
    e = entrada(4, sobre={3: {"fc_reposo": 180.0}})
    assert "sensores_sospechosos" not in e


def test_confirmar_a_mano_un_cambio_real_sirve_de_referencia_al_sensor():
    # Día 4 el sensor salta a 128 y la persona lo confirma a mano; día 5 el sensor marca 126.
    e = entrada(5, sobre={4: {"fc_reposo": 128.0}}, sensor={5: {"fc_reposo": 126.0}})
    assert "sensores_sospechosos" not in e


def test_el_rango_del_sensor_cubre_el_del_catalogo():
    # Un dato que el catálogo acepta a mano nunca debe marcarse por rango.
    for clave, ficha in AJUSTES.catalogo.items():
        limites = CONFIG["indicadores"].get(clave)
        if limites is None:
            continue
        if "minimo" in limites:
            assert limites["minimo"] <= ficha["minimo"], clave
        if "maximo" in limites:
            assert limites["maximo"] >= ficha["maximo"], clave


# --------------------------------------------------------------------------
# La entrada del orquestador con un dato sospechoso
# --------------------------------------------------------------------------

def test_la_entrada_con_dato_sospechoso_cumple_el_contrato_y_lo_excluye():
    e = entrada(5, sensor={5: {"fc_reposo": 250.0}})
    assert errores("entrada_orquestador", e) == []
    assert e["indicadores"]["fc_reposo"] is None
    assert e["desviaciones_vs_base"]["fc_reposo"] is None
    assert e["tendencias_7d"]["fc_reposo"][-1] is None
    assert e["tendencias_7d"]["fc_reposo"][-2] == 69.0, "los días anteriores, válidos, se conservan"
    ficha = e["sensores_sospechosos"][0]
    assert ficha["indicador"] == "fc_reposo" and ficha["nombre"] == "Pulso en reposo"
    assert ficha["motivo"] == "fuera_de_rango" and ficha["valor_leido"] == 250.0


def test_un_dato_sospechoso_en_la_adaptacion_no_entra_en_la_linea_base():
    limpio = entrada(3)
    con_fallo = entrada(3, sensor={2: {"fc_reposo": 250.0}})
    # Base de pulso: mitad pre-vuelo (62), mitad media de los días de adaptación válidos.
    assert limpio["linea_base"]["fc_reposo"] == 62.25      # días 1 y 2: 62 y 63
    assert con_fallo["linea_base"]["fc_reposo"] == 62.0    # solo el día 1: el 250 no cuenta


# --------------------------------------------------------------------------
# Botón "Simular sensor defectuoso" (pila completa: backend, orquestador y modelos reales)
# --------------------------------------------------------------------------

TIPOS = [("imposible", "fuera_de_rango"), ("salto", "cambio_brusco"), ("congelado", "valor_congelado")]


@pytest.mark.parametrize("tipo,motivo", TIPOS)
def test_el_boton_de_demo_marca_el_sensor_de_pulso(tipo, motivo):
    async def caso(nav):
        await nav.post("/api/demo/dia", json={"dia": 5})
        antes = (await nav.get("/api/estado")).json()
        r = await nav.post("/api/demo/sensor-defectuoso", json={"activo": True, "tipo": tipo})
        return antes, r.status_code, r.json()
    antes, codigo, e = correr_con_app(caso)
    assert codigo == 200
    assert e["sensor_defectuoso"] == {"dia": 5, "activo_hoy": True, "indicador": "fc_reposo", "tipo": tipo}
    assert e["indicadores"]["fc_reposo"] is None, "el dato sospechoso no se usa"
    assert [s["motivo"] for s in e["sensores_sospechosos"]] == [motivo]

    r = e["resultado"]
    aviso = r["sensores_sospechosos"][0]
    assert aviso["indicador"] == "fc_reposo" and aviso["motivo"] == motivo
    assert "El sensor de pulso en reposo parece fallar" in aviso["aviso"]
    assert "Revisa el equipo" in aviso["aviso"]
    assert {"FC_ALTA", "CARDIOVASCULAR"} <= set(aviso["reglas_afectadas"])
    assert r["semaforo_indicadores"]["fc_reposo"]["nivel"] == "sospechoso"
    assert "dato sospechoso" in r["explicacion_global"]

    # El día 5 ya estaba en rojo por fatiga (sueño, estrés, ejercicio, ánimo): sigue en rojo.
    assert antes["resultado"]["nivel_global"] == "rojo" and r["nivel_global"] == "rojo"
    fatiga = {a["id"]: a for a in r["alertas"]}["FATIGA"]
    assert fatiga["nivel"] == "rojo"
    # Ninguna alerta se apoya en el pulso.
    assert all("fc_reposo" not in a["indicadores_implicados"] for a in r["alertas"])
    # El informe para el cirujano de vuelo dice qué dato no se usó.
    assert r["informe_cirujano"]["sensores_sospechosos"][0]["indicador"] == "fc_reposo"


def test_al_modelo_le_falta_el_dato_sospechoso_y_su_opinion_no_cambia_el_nivel():
    async def caso(nav):
        await nav.post("/api/demo/dia", json={"dia": 5})
        antes = (await nav.get("/api/estado")).json()["resultado"]
        despues = (await nav.post("/api/demo/sensor-defectuoso", json={"activo": True})).json()["resultado"]
        return antes, despues
    antes, despues = correr_con_app(caso)

    def miembro(resultado, nombre):
        return next(m for m in resultado["junta"] if m["especialista"] == nombre)
    cardio_antes, cardio = miembro(antes, "cardiovascular"), miembro(despues, "cardiovascular")
    assert "fc_desv_pct" not in cardio_antes["respuesta"]["datos_faltantes"]
    assert "fc_desv_pct" in cardio["respuesta"]["datos_faltantes"], "el modelo debe saber que le falta el pulso"
    # Sin el pulso el modelo ve menos riesgo (lo rellena con un valor sano)...
    assert cardio["respuesta"]["riesgo"] < cardio_antes["respuesta"]["riesgo"]
    # ...así que su opinión se muestra, pero hoy no puede subir ninguna alerta.
    assert cardio["opinion_limitada"] is True and cardio_antes["opinion_limitada"] is False
    assert all("cardiovascular" not in a["elevada_por"] for a in despues["alertas"])
    # A los especialistas que no usan el pulso no les falta nada y opinan como siempre.
    for nombre in ("sueno", "fatiga-bienestar"):
        assert miembro(despues, nombre)["respuesta"]["datos_faltantes"] == []
        assert miembro(despues, nombre)["opinion_limitada"] is False
        assert miembro(despues, nombre)["respuesta"] == miembro(antes, nombre)["respuesta"] | {
            "consulta_id": miembro(despues, nombre)["respuesta"]["consulta_id"]}
    assert despues["modo"] == "completo", "un sensor roto no es una laptop caída"


@pytest.mark.parametrize("dia", range(1, 8))
@pytest.mark.parametrize("tipo", ["imposible", "salto", "congelado"])
def test_un_sensor_roto_no_sube_el_nivel_ni_da_rojo_por_si_solo(dia, tipo):
    async def caso(nav):
        await nav.post("/api/demo/dia", json={"dia": dia})
        antes = (await nav.get("/api/estado")).json()["resultado"]
        r = await nav.post("/api/demo/sensor-defectuoso", json={"activo": True, "tipo": tipo})
        return antes, r
    antes, respuesta = correr_con_app(caso)
    if respuesta.status_code == 422:
        # Un salto necesita un día anterior y un valor congelado necesita 4 días de misión.
        assert (tipo, dia) in {("salto", 1), ("congelado", 1), ("congelado", 2), ("congelado", 3)}
        return
    despues = respuesta.json()["resultado"]
    assert despues["sensores_sospechosos"], (dia, tipo)
    assert indice(despues["nivel_global"]) <= indice(antes["nivel_global"]), (dia, tipo)
    if antes["nivel_global"] != "rojo":
        assert despues["nivel_global"] != "rojo"
    # Las alertas que no usan el pulso siguen igual, al mismo nivel de reglas o más.
    nuevas = {a["id"]: a for a in despues["alertas"]}
    for alerta in antes["alertas"]:
        if "fc_reposo" in alerta["indicadores_implicados"]:
            continue
        assert alerta["id"] in nuevas, (dia, tipo, alerta["id"])
        assert indice(nuevas[alerta["id"]]["nivel_reglas"]) >= indice(alerta["nivel_reglas"])


def test_sin_validacion_ese_mismo_valor_habria_dado_rojo():
    # Comprobación del propio caso: el 250 que simula la demo, tomado como bueno (a mano),
    # dispara el pulso alto en rojo. Con la validación se queda en aviso de equipo.
    async def caso(nav):
        tomado_como_bueno = (await nav.post("/api/registro", json={"indicadores": {"fc_reposo": 200}})).json()
        await nav.post("/api/demo/reiniciar")
        con_validacion = (await nav.post("/api/demo/sensor-defectuoso", json={"activo": True})).json()
        return tomado_como_bueno["resultado"], con_validacion["resultado"]
    bueno, validado = correr_con_app(caso)
    assert bueno["nivel_global"] == "rojo"
    assert validado["nivel_global"] == "verde" and validado["alertas"] == []
    assert validado["sensores_sospechosos"][0]["motivo"] == "fuera_de_rango"


def test_apagar_el_fallo_devuelve_la_historia_original():
    async def caso(nav):
        niveles = []
        for dia in range(1, 8):
            niveles.append((await nav.post("/api/demo/dia", json={"dia": dia})).json()["resultado"]["nivel_global"])
        await nav.post("/api/demo/dia", json={"dia": 5})
        await nav.post("/api/demo/sensor-defectuoso", json={"activo": True, "tipo": "congelado"})
        apagado = (await nav.post("/api/demo/sensor-defectuoso", json={"activo": False})).json()
        despues = []
        for dia in range(1, 8):
            despues.append((await nav.post("/api/demo/dia", json={"dia": dia})).json()["resultado"]["nivel_global"])
        return niveles, apagado, despues
    niveles, apagado, despues = correr_con_app(caso)
    assert niveles == HISTORIA and despues == HISTORIA
    assert apagado["sensores_sospechosos"] == [] and apagado["indicadores"]["fc_reposo"] == 72.0
    assert apagado["sensor_defectuoso"]["activo_hoy"] is False


def test_medir_de_nuevo_a_mano_quita_el_aviso():
    async def caso(nav):
        await nav.post("/api/demo/dia", json={"dia": 5})
        await nav.post("/api/demo/sensor-defectuoso", json={"activo": True})
        return (await nav.post("/api/registro", json={"indicadores": {"fc_reposo": 71}})).json()
    e = correr_con_app(caso)
    assert e["sensores_sospechosos"] == [] and e["indicadores"]["fc_reposo"] == 71.0
    assert e["resultado"]["sensores_sospechosos"] == []


def test_un_fallo_que_no_se_puede_simular_se_rechaza_con_mensaje_claro():
    async def caso(nav):
        salto = await nav.post("/api/demo/sensor-defectuoso", json={"activo": True, "tipo": "salto"})
        congelado = await nav.post("/api/demo/sensor-defectuoso", json={"activo": True, "tipo": "congelado"})
        raro = await nav.post("/api/demo/sensor-defectuoso", json={"activo": True, "tipo": "explosion"})
        estado = (await nav.get("/api/estado")).json()
        return salto, congelado, raro, estado
    salto, congelado, raro, estado = correr_con_app(caso)   # día 1: no hay días anteriores
    assert salto.status_code == 422 and "día anterior" in salto.json()["detail"]
    assert congelado.status_code == 422 and "4 días" in congelado.json()["detail"]
    assert raro.status_code == 422
    assert estado["sensores_sospechosos"] == [] and estado["sensor_defectuoso"]["activo_hoy"] is False


def test_la_exportacion_csv_marca_el_dato_sospechoso():
    async def caso(nav):
        await nav.post("/api/demo/dia", json={"dia": 3})
        await nav.post("/api/demo/sensor-defectuoso", json={"activo": True})
        return (await nav.get("/api/exportar.csv")).text
    lineas = correr_con_app(caso).splitlines()
    assert lineas[1].endswith("datos_sospechosos")
    dia3 = next(linea for linea in lineas if linea.startswith("3,"))
    assert dia3.endswith("fc_reposo=250")
    columnas = lineas[1].split(",")
    assert dia3.split(",")[columnas.index("fc_reposo")] == "", "el valor sospechoso no se exporta como dato"
