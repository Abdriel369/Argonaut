"""Verificación de la red del router propio.

  Desde la Laptop 1:  python3 scripts/verificar_red.py --desde laptop1
      comprueba el backend local y la conexión HTTP con el orquestador de la Laptop 3,
      y el estado que el orquestador ve de la Laptop 2 y del modelo solar.
  Desde la Laptop 3:  python3 scripts/verificar_red.py --desde laptop3
      comprueba el gateway de la Laptop 2 y cada modelo detrás de él.

Lee las IP y puertos de los archivos .env de cada laptop (o de .env.example si no existen).
No necesita Docker ni internet. Sale con código 1 si algo no responde.
"""

import argparse
import sys
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]


def leer_env(carpeta: Path) -> dict:
    for nombre in (".env", ".env.example"):
        ruta = carpeta / nombre
        if ruta.exists():
            valores = {}
            for linea in ruta.read_text(encoding="utf-8").splitlines():
                linea = linea.split("#", 1)[0].strip()
                if "=" in linea:
                    clave, valor = linea.split("=", 1)
                    valores[clave.strip()] = valor.strip()
            if nombre == ".env.example":
                print(f"  (aviso: usando {carpeta.name}/.env.example; copia .env y ajusta las IP)")
            return valores
    raise SystemExit(f"No hay .env ni .env.example en {carpeta}")


def probar(etiqueta: str, url: str, resultados: list) -> None:
    try:
        respuesta = httpx.get(url, timeout=3.0)
        respuesta.raise_for_status()
        resultados.append(True)
        print(f"  [ok]    {etiqueta:<34} {url}")
    except Exception as error:  # cualquier fallo de red se reporta sin romper el script
        resultados.append(False)
        print(f"  [FALLA] {etiqueta:<34} {url}  ({type(error).__name__})")


def desde_laptop1() -> list:
    env = leer_env(RAIZ / "laptop1-backend-frontend")
    l3 = f"http://{env['IP_LAPTOP3']}:{env.get('PUERTO_ORQUESTADOR', '8300')}"
    resultados = []
    print("Desde la Laptop 1:")
    probar("backend local", f"http://127.0.0.1:{env.get('PUERTO_BACKEND', '8100')}/salud", resultados)
    probar("orquestador (Laptop 3)", f"{l3}/salud", resultados)
    try:
        red = httpx.get(f"{l3}/red", timeout=6.0).json()
        for nombre, estado in (("gateway Laptop 2", red["gateway"]), ("modelo solar", red["modelo_solar"])):
            marca = "ok   " if estado["ok"] else "FALLA"
            print(f"  [{marca}] {nombre:<34} visto desde la Laptop 3: {estado['detalle']}")
            resultados.append(bool(estado["ok"]))
    except Exception as error:
        print(f"  [FALLA] no se pudo leer /red del orquestador ({type(error).__name__})")
        resultados.append(False)
    return resultados


def desde_laptop3() -> list:
    env = leer_env(RAIZ / "laptop3-orquestador")
    l2 = f"http://{env['IP_LAPTOP2']}:{env.get('PUERTO_GATEWAY', '8200')}"
    resultados = []
    print("Desde la Laptop 3:")
    probar("gateway Laptop 2", f"{l2}/salud", resultados)
    probar("modelo solar local", f"http://127.0.0.1:{env.get('PUERTO_MODELO_SOLAR', '8310')}/salud", resultados)
    try:
        estado = httpx.get(f"{l2}/salud", timeout=6.0).json()
        for nombre, modelo in estado.get("modelos", {}).items():
            marca = "ok   " if modelo["ok"] else "FALLA"
            print(f"  [{marca}] modelo {nombre:<26} {modelo['detalle']}")
            resultados.append(bool(modelo["ok"]))
    except Exception as error:
        print(f"  [FALLA] no se pudo leer los modelos del gateway ({type(error).__name__})")
        resultados.append(False)
    return resultados


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--desde", choices=["laptop1", "laptop3"], required=True)
    args = parser.parse_args()
    resultados = desde_laptop1() if args.desde == "laptop1" else desde_laptop3()
    print("Red correcta." if all(resultados) else "Hay conexiones caídas: revisa IP, puertos y que el servicio esté arriba.")
    sys.exit(0 if all(resultados) else 1)
