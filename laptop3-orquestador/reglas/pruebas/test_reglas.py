"""Motor de reglas: el guion de 7 días, la ventana de adaptación y los datos faltantes."""

import pytest

from fabrica import entrada
from reglas import cargar_config, evaluar

CFG = cargar_config()

# Lo que debe verse en la demo (acceptance: días 1-2 verde, 3 y 4 amarillo, 5 crítico, 6 mejora, 7 verde).
NIVELES_GUION = ["verde", "verde", "amarillo", "amarillo", "rojo", "amarillo", "verde"]


@pytest.mark.parametrize("dia,esperado", list(enumerate(NIVELES_GUION, start=1)))
def test_cada_dia_del_guion_da_el_nivel_esperado(dia, esperado):
    assert evaluar(entrada(dia), CFG)["nivel"] == esperado


def test_dia_5_activa_fatiga_con_el_ademas_del_animo():
    r = evaluar(entrada(5), CFG)
    assert "FATIGA" in r["reglas_activadas"]
    assert [a for a in r["alertas"] if a["id"] == "FATIGA"][0]["nivel"] == "rojo"


def test_ventana_de_adaptacion_es_mas_tolerante():
    # Dos días de adaptación: una caída de 1.3 h no alerta; en el día 3 ya alerta.
    dos = evaluar(entrada(2, sobre={2: {"sueno_h": 5.9}}), CFG)
    assert dos["ventana_adaptacion"] is True
    assert dos["semaforo"]["sueno_h"]["nivel"] == "verde"
    tres = evaluar(entrada(3, sobre={3: {"sueno_h": 5.9}}), CFG)
    assert tres["ventana_adaptacion"] is False
    assert tres["semaforo"]["sueno_h"]["nivel"] == "amarillo"


def test_persistencia_sube_un_escalon_tras_varios_dias():
    # Día 5: la caída de sueño lleva 3 días seguidos fuera de rango -> de amarillo a naranja.
    r = evaluar(entrada(5), CFG)
    assert r["semaforo"]["sueno_h"]["nivel"] == "naranja"
    assert r["semaforo"]["sueno_h"]["sube_por_persistencia"] is True


def test_evento_solar_activa_radiacion():
    r = evaluar(entrada(2, evento=True), CFG)
    assert "RADIACION" in r["reglas_activadas"]
    assert r["nivel"] in ("naranja", "rojo")


def test_un_dato_sin_registro_no_rompe_la_evaluacion():
    r = evaluar(entrada(4, sobre={4: {"spo2": None}}), CFG)
    assert r["semaforo"]["spo2"]["nivel"] == "sin_dato"
    assert r["semaforo"]["spo2"]["valor"] is None


def test_el_texto_de_cada_alerta_explica_el_hecho():
    r = evaluar(entrada(5), CFG)
    for alerta in r["alertas"]:
        assert alerta["hechos"], alerta["id"]
        assert alerta["consecuencia"], alerta["id"]


# --------------------------------------------------------------------------
# Datos sospechosos: un sensor que parece fallar
# --------------------------------------------------------------------------

from backend.ajustes import Ajustes  # noqa: E402
from comun.niveles import indice  # noqa: E402
from reglas import excluir_sospechosos  # noqa: E402

LIMITES_SENSORES = Ajustes.desde_entorno().sensores["indicadores"]


def _valor_imposible(indicador: str) -> float:
    limites = LIMITES_SENSORES[indicador]
    return limites["maximo"] * 1.25 if "maximo" in limites else limites["minimo"] - 1.0


def test_un_dato_sospechoso_queda_marcado_y_no_activa_ninguna_regla():
    # Pulso 250: tomado como bueno sería pulso alto en rojo. Marcado como sospechoso no cuenta.
    r = evaluar(entrada(1, sensor={1: {"fc_reposo": 250.0}}), CFG)
    assert r["semaforo"]["fc_reposo"]["nivel"] == "sospechoso"
    assert r["semaforo"]["fc_reposo"]["valor"] is None
    assert r["semaforo"]["fc_reposo"]["valor_leido"] == 250.0
    assert r["nivel"] == "verde" and r["alertas"] == []
    ficha = r["sensores_sospechosos"][0]
    assert ficha["indicador"] == "fc_reposo"
    assert ficha["reglas_afectadas"] == ["FC_ALTA", "RADIACION", "CARDIOVASCULAR"]


def test_las_reglas_excluyen_el_dato_aunque_la_entrada_lo_traiga_con_valor():
    # Defensa en profundidad: si quien envía olvidó borrar el valor, las reglas lo apartan igual.
    e = entrada(1)
    e["indicadores"]["fc_reposo"] = 250.0
    e["tendencias_7d"]["fc_reposo"][-1] = 250.0
    e["sensores_sospechosos"] = [{"indicador": "fc_reposo", "motivo": "fuera_de_rango", "valor_leido": 250.0}]
    limpia = excluir_sospechosos(e)
    assert limpia["indicadores"]["fc_reposo"] is None and limpia["tendencias_7d"]["fc_reposo"][-1] is None
    assert e["indicadores"]["fc_reposo"] == 250.0, "no se modifica la entrada original"
    assert evaluar(e, CFG)["nivel"] == "verde"
    sin_marcas = entrada(1)
    assert excluir_sospechosos(sin_marcas) is sin_marcas, "sin datos sospechosos la entrada no se toca"


@pytest.mark.parametrize("dia", range(1, 8))
@pytest.mark.parametrize("indicador", sorted(LIMITES_SENSORES))
def test_un_sensor_roto_no_sube_el_nivel_ni_baja_alertas_de_otras_senales(dia, indicador):
    normal = evaluar(entrada(dia), CFG)
    roto = evaluar(entrada(dia, sensor={dia: {indicador: _valor_imposible(indicador)}}), CFG)
    assert [s["indicador"] for s in roto["sensores_sospechosos"]] == [indicador]
    # 1. Por sí solo no sube nada: el nivel nunca es mayor que sin el fallo.
    assert indice(roto["nivel"]) <= indice(normal["nivel"])
    # 2. Las alertas que no usan ese indicador siguen ahí, al mismo nivel o más.
    despues = {a["id"]: a for a in roto["alertas"]}
    for alerta in normal["alertas"]:
        if indicador in alerta["indicadores_implicados"]:
            continue
        assert alerta["id"] in despues, (alerta["id"], "desapareció por un sensor ajeno")
        assert indice(despues[alerta["id"]]["nivel"]) >= indice(alerta["nivel"])
    # 3. La lectura sospechosa no se evalúa: su semáforo no da nivel y su alerta propia no salta.
    #    (Una regla de combinación sí puede seguir usando los días anteriores, que eran válidos:
    #    por ejemplo "llevas varios días durmiendo poco" aunque falte el sueño de hoy.)
    if indicador in CFG["indicadores"]:
        assert roto["semaforo"][indicador]["nivel"] == "sospechoso"
        assert CFG["indicadores"][indicador]["alerta_id"] not in despues


# --------------------------------------------------------------------------
# Fuentes de los umbrales (ver FUENTES.md en la raíz del repositorio)
# --------------------------------------------------------------------------

import re  # noqa: E402
from pathlib import Path  # noqa: E402

PENDIENTE = "FUENTE POR CITAR"
# Bloques que siguen sin fuente verificada. Sacar uno de aquí exige abrir el documento,
# comprobar el pasaje y anotar la referencia completa en FUENTES.md.
PENDIENTES = {("indicadores", "fc_reposo"), ("indicadores", "hrv"), ("combinaciones", "CARDIOVASCULAR")}
# Referencias que no cuentan como verificadas (solo se abrió el resumen): no pueden respaldar un umbral.
NO_VERIFICADAS = {"F10"}


def _fuentes_md() -> str:
    carpeta = Path(__file__).resolve()
    for padre in carpeta.parents:
        if (padre / "FUENTES.md").exists():
            return (padre / "FUENTES.md").read_text(encoding="utf-8")
    raise AssertionError("No se encuentra FUENTES.md en la raíz del repositorio")


def _referencias_md() -> dict:
    """{'F1': texto de la sección '### [F1] ...'} de FUENTES.md."""
    partes = re.split(r"^### \[(F\d+)\]", _fuentes_md(), flags=re.MULTILINE)
    return {partes[k]: partes[k + 1].split("\n## ")[0] for k in range(1, len(partes) - 1, 2)}


def _bloques_de_umbrales():
    yield ("general",), CFG["general"]
    for seccion in ("indicadores", "combinaciones", "contexto"):
        for nombre, bloque in CFG[seccion].items():
            yield (seccion, nombre), bloque


def test_cada_umbral_declara_su_fuente():
    for ruta, bloque in _bloques_de_umbrales():
        assert isinstance(bloque.get("fuente"), str) and bloque["fuente"].strip(), ruta


def test_solo_los_pendientes_conocidos_siguen_sin_fuente():
    pendientes = {ruta for ruta, bloque in _bloques_de_umbrales() if bloque["fuente"].startswith(PENDIENTE)}
    assert pendientes == PENDIENTES


def test_ningun_umbral_atribuye_su_numero_a_la_fuente():
    # Regla del proyecto: si el número no aparece textual en la fuente, se escribe
    # "principio respaldado por [fuente]; corte de diseño propio".
    for ruta, bloque in _bloques_de_umbrales():
        fuente = bloque["fuente"]
        if ruta in PENDIENTES:
            continue
        assert "diseño propio" in fuente, (ruta, "debe decir que el corte es de diseño propio")
        citadas = set(re.findall(r"\[(F\d+)\]", fuente))
        assert citadas, (ruta, "debe citar al menos una referencia [Fn] de FUENTES.md")
        assert not citadas & NO_VERIFICADAS, (ruta, "se apoya en una referencia que no cuenta como verificada")


def test_cada_referencia_citada_esta_completa_en_fuentes_md():
    referencias = _referencias_md()
    citadas = {ref for _, bloque in _bloques_de_umbrales() for ref in re.findall(r"\[(F\d+)\]", bloque["fuente"])}
    assert citadas, "umbrales.toml debe citar referencias de FUENTES.md"
    assert "Fecha de consulta" in _fuentes_md()
    for ref in sorted(citadas):
        assert ref in referencias, f"[{ref}] se cita en umbrales.toml pero no está en FUENTES.md"
        ficha = referencias[ref]
        for campo in ("**Autor", "**Título:**", "**Año:**", "**Licencia:**"):
            assert campo in ficha, (ref, f"falta {campo}")
        assert "**Revista:**" in ficha or "**Editor:**" in ficha or "editor:**" in ficha, (ref, "falta revista o editor")
        assert "http" in ficha or "**DOI:**" in ficha, (ref, "falta DOI o URL")
        citas = re.findall(r'"([^"]+)"', ficha)
        assert citas, (ref, "falta la cita corta del pasaje")
        assert all(len(cita.split()) < 15 for cita in citas), (ref, "las citas textuales deben ser cortas")


def test_no_hay_pdf_de_articulos_en_el_repositorio():
    raiz = next(p for p in Path(__file__).resolve().parents if (p / "FUENTES.md").exists())
    pdfs = [str(p.relative_to(raiz)) for p in raiz.rglob("*.pdf") if ".venv" not in p.parts and ".git" not in p.parts]
    assert pdfs == [], f"no se guardan PDF de fuentes en el repositorio: {pdfs}"


def test_los_cortes_de_dosis_son_escalones_por_debajo_del_limite_de_la_norma():
    dosis = CFG["contexto"]["dosis_acumulada"]
    assert dosis["amarillo"] < dosis["naranja"] < dosis["rojo"] < dosis["limite_norma_msv"] == 600.0
