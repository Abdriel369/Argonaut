"""Informe para el cirujano de vuelo (en Tierra).

Se genera cuando el nivel global llega al mínimo configurado. La Laptop 1 lo
guarda en una cola "pendiente de enviar" hasta que se simula el enlace con la Tierra.
"""

from comun import AVISO
from comun.niveles import TEXTO_NIVEL


def construir_informe(entrada: dict, evaluacion_reglas: dict, alertas: list, junta: list,
                      nivel_global: str, modo: str, protocolos: dict,
                      sensores_sospechosos: list | None = None) -> dict:
    """Resumen de indicadores, tendencia de 7 días, reglas, especialistas y acciones.

    Si algún sensor parecía fallar, el informe lo dice: el cirujano de vuelo debe saber
    qué datos no se usaron.
    """
    semaforo = evaluacion_reglas["semaforo"]
    indicadores = [
        {
            "indicador": clave, "nombre": estado["nombre"], "valor": estado["valor"],
            "unidad": estado["unidad"], "linea_base": estado["referencia"],
            "desviacion": estado["desviacion"], "nivel": estado["nivel"],
        }
        for clave, estado in semaforo.items()
    ]
    consultados = [
        {
            "especialista": miembro["especialista"], "laptop": miembro["laptop"],
            "riesgo": miembro["respuesta"]["riesgo"], "nivel": miembro["respuesta"]["nivel"],
            "confianza": miembro["respuesta"]["confianza"],
            "version_modelo": miembro["respuesta"]["version_modelo"],
            "datos_entrenamiento": miembro["respuesta"]["datos_entrenamiento"],
        }
        for miembro in junta if miembro["estado"] == "respondio"
    ]
    return {
        "id": f"INF-{entrada['astronauta_id']}-D{entrada['dia_mision']:02d}",
        "astronauta_id": entrada["astronauta_id"],
        "dia_mision": entrada["dia_mision"],
        "nivel_global": nivel_global,
        "nivel_texto": TEXTO_NIVEL[nivel_global],
        "modo": modo,
        "resumen": [
            {"alerta": a["id"], "titulo": a["titulo"], "nivel": a["nivel"],
             "causa": a["causa_en_lenguaje_simple"]}
            for a in alertas
        ],
        "indicadores": indicadores,
        "tendencia_7d": {
            clave: entrada["tendencias_7d"].get(clave, []) for clave in semaforo
        },
        "contexto": entrada["contexto"],
        "reglas_activadas": evaluacion_reglas["reglas_activadas"],
        "especialistas_consultados": consultados,
        "especialistas_no_disponibles": [m["especialista"] for m in junta if m["estado"] == "no_disponible"],
        "sensores_sospechosos": list(sensores_sospechosos or []),
        "acciones_recomendadas": [
            {"protocolo_id": pid, "titulo": protocolo["titulo"],
             "pasos": [paso["texto"] for paso in protocolo["pasos"]]}
            for pid, protocolo in protocolos.items()
        ],
        # La Laptop 1 completa esta lista con los pasos marcados como "ya lo hice".
        "acciones_tomadas": [],
        "nota": AVISO + " Modelos entrenados con datos sintéticos.",
    }
