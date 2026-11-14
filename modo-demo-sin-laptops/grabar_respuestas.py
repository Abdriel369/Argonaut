"""Graba las respuestas de los modelos para el modo demo (se ejecuta una vez).

Recorre todos los estados que la demo puede producir:
  día 1-7  x  evento solar (ninguno, o en cada día)  x  Laptop 2 encendida / apagada.
Por cada consulta real a un especialista guarda su respuesta, con una clave que
depende solo de lo que el especialista recibe. Así el modo demo responde igual
que el sistema real, sin necesitar los modelos.

Uso (desde la raíz del repositorio):
    python modo-demo-sin-laptops/grabar_respuestas.py
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for ruta in [
    RAIZ, RAIZ / "pruebas-integracion", RAIZ / "laptop1-backend-frontend",
    RAIZ / "laptop2-modelos", RAIZ / "laptop2-modelos" / "datos-sinteticos",
    RAIZ / "laptop2-modelos" / "modelos" / "sueno",
    RAIZ / "laptop2-modelos" / "modelos" / "fatiga-bienestar",
    RAIZ / "laptop2-modelos" / "modelos" / "cardiovascular",
    RAIZ / "laptop3-orquestador", RAIZ / "laptop3-orquestador" / "modelos" / "riesgo-solar",
]:
    sys.path.insert(0, str(ruta))

import pila  # noqa: E402
from orquestador.clientes import ClienteHTTP, clave_guardada  # noqa: E402

SALIDA = RAIZ / "modo-demo-sin-laptops" / "respuestas-guardadas.json"


class ClienteGrabador(ClienteHTTP):
    """Cliente real que además anota cada respuesta de especialista recibida."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grabadas = {}

    async def consultar(self, consulta_id, especialistas, datos, estado_l2=None):
        respuestas, fallidos = await super().consultar(consulta_id, especialistas, datos, estado_l2)
        for nombre, respuesta in respuestas.items():
            clave = clave_guardada(nombre, datos)
            self.grabadas[clave] = {k: v for k, v in respuesta.items() if k != "consulta_id"}
        return respuestas, fallidos


async def grabar() -> dict:
    cliente = pila.crear_cliente_especialistas(clase=ClienteGrabador)
    app = pila.crear_pila(cliente_especialistas=cliente)
    estados = 0
    async with pila.navegador(app) as nav:
        for evento_dia in [None, *range(1, 8)]:
            if evento_dia is None:
                await nav.post("/api/demo/evento-solar", json={"activo": False})
            else:
                await nav.post("/api/demo/dia", json={"dia": evento_dia})
                await nav.post("/api/demo/evento-solar", json={"activo": True})
            for caida in (False, True):
                await nav.post("/api/demo/caida-laptop2", json={"activa": caida})
                for dia in range(1, 8):
                    respuesta = await nav.post("/api/demo/dia", json={"dia": dia})
                    respuesta.raise_for_status()
                    estados += 1
    return {
        "meta": {
            "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "estados_recorridos": estados,
            "consultas_guardadas": len(cliente.grabadas),
            "nota": (
                "Respuestas de los modelos grabadas de ejecuciones reales. "
                "Datos 100 % simulados. No es una herramienta de diagnóstico médico."
            ),
        },
        "respuestas": cliente.grabadas,
    }


if __name__ == "__main__":
    contenido = asyncio.run(grabar())
    SALIDA.write_text(json.dumps(contenido, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{contenido['meta']['consultas_guardadas']} respuestas guardadas en {SALIDA.name} "
          f"({contenido['meta']['estados_recorridos']} estados recorridos)")
