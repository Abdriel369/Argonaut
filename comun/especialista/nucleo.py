"""Base común de los 4 modelos especialistas.

Un especialista se describe con una Definicion (variables, generador de datos
sintéticos, tipo de modelo). Aquí están el entrenamiento, el guardado del
artefacto versionado y la predicción con factores explicativos.

Tipos de modelo:
- "logistica": regresión logística (scikit-learn para entrenar, numpy para predecir).
- "boosting":  gradient boosting pequeño con XGBoost (CPU, o CUDA si se detecta).

IMPORTANTE: todo se entrena con datos SINTÉTICOS. Las métricas dicen qué tan bien
el modelo recupera la regla con la que se generaron los datos; no miden validez clínica.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from comun.niveles import nivel_por_riesgo

log = logging.getLogger(__name__)

PALABRA_RIESGO = {"verde": "bajo", "amarillo": "moderado", "naranja": "alto", "rojo": "muy alto"}


@dataclass(frozen=True)
class Variable:
    """Una entrada del modelo, con el rango en que se generaron los datos sintéticos."""

    nombre: str
    etiqueta: str          # nombre sencillo para mostrar
    minimo: float
    maximo: float
    referencia: float      # valor típico sano; se usa para imputar y para explicar
    frase_alto: str        # cómo decirlo cuando está por encima de la referencia
    frase_bajo: str        # cómo decirlo cuando está por debajo
    unidad: str = ""
    monotonia: int = 0     # +1: más valor = más riesgo; -1: al revés; 0: libre (solo boosting)


@dataclass(frozen=True)
class Definicion:
    """Todo lo que distingue a un especialista de otro."""

    nombre: str                 # identificador del contrato: sueno, fatiga-bienestar...
    titulo: str                 # nombre para la interfaz
    riesgo_que_estima: str      # se usa en la explicación: "riesgo alto de ..."
    version: str
    tipo: str                   # "logistica" o "boosting"
    laptop: str                 # dónde vive: "Laptop 2" o "Laptop 3"
    variables: tuple
    generar: Callable           # (n, semilla) -> (X, y) datos sintéticos reproducibles
    extraer: Callable           # (datos de la consulta) -> {variable: valor o None}
    hiperparametros: dict
    n_muestras: int
    semilla: int
    auc_minimo: float           # métrica mínima exigida en las pruebas
    limitaciones: tuple
    cortes_nivel: tuple = (0.20, 0.50, 0.75)   # valores de ejemplo

    @property
    def nombres(self) -> list[str]:
        return [v.nombre for v in self.variables]


def ruta_modelo(definicion: Definicion, carpeta: Path) -> Path:
    return Path(carpeta) / f"modelo-{definicion.nombre}-v{definicion.version}.json"


def ruta_metricas(definicion: Definicion, carpeta: Path) -> Path:
    return Path(carpeta) / f"metricas-{definicion.nombre}-v{definicion.version}.json"


def _sigmoide(z):
    return 1.0 / (1.0 + np.exp(-z))


def auc(y, p) -> float:
    """Área bajo la curva ROC por rangos (equivalente a Mann-Whitney), solo con numpy."""
    y = np.asarray(y)
    orden = np.argsort(p, kind="mergesort")
    rangos = np.empty(len(p))
    rangos[orden] = np.arange(1, len(p) + 1)
    # Empates: se les da el rango medio.
    p_ordenado = np.asarray(p)[orden]
    inicio = 0
    while inicio < len(p):
        fin = inicio
        while fin + 1 < len(p) and p_ordenado[fin + 1] == p_ordenado[inicio]:
            fin += 1
        if fin > inicio:
            rangos[orden[inicio:fin + 1]] = (inicio + fin + 2) / 2.0
        inicio = fin + 1
    positivos = int(y.sum())
    negativos = len(y) - positivos
    if positivos == 0 or negativos == 0:
        return float("nan")
    return float((rangos[y == 1].sum() - positivos * (positivos + 1) / 2.0) / (positivos * negativos))


# --------------------------------------------------------------------------
# Entrenamiento
# --------------------------------------------------------------------------

def entrenar(definicion: Definicion, carpeta: Path, dispositivo: str = "cpu") -> dict:
    """Genera los datos sintéticos, entrena, valida y guarda modelo + métricas.

    Reproducible: misma semilla -> mismos datos -> mismo modelo (en el mismo dispositivo).
    """
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    X, y = definicion.generar(definicion.n_muestras, definicion.semilla)
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)

    # Partición fija 80/20 para validar con datos que el modelo no vio.
    orden = np.random.default_rng(definicion.semilla + 1).permutation(len(y))
    corte = int(0.8 * len(y))
    entreno, prueba = orden[:corte], orden[corte:]

    if definicion.tipo == "logistica":
        from sklearn.linear_model import LogisticRegression

        medias = X[entreno].mean(axis=0)
        escalas = X[entreno].std(axis=0)
        escalas[escalas == 0] = 1.0
        clasificador = LogisticRegression(max_iter=2000, **definicion.hiperparametros)
        clasificador.fit((X[entreno] - medias) / escalas, y[entreno])
        artefacto = {
            "tipo": "logistica",
            "variables": definicion.nombres,
            "medias": medias.tolist(),
            "escalas": escalas.tolist(),
            "coeficientes": clasificador.coef_[0].tolist(),
            "intercepto": float(clasificador.intercept_[0]),
        }
        ruta_modelo(definicion, carpeta).write_text(json.dumps(artefacto, indent=2), encoding="utf-8")
        dispositivo = "cpu"   # un modelo lineal tan pequeño no gana nada con GPU
    elif definicion.tipo == "boosting":
        import xgboost as xgb

        hiper = dict(definicion.hiperparametros)
        rondas = int(hiper.pop("rondas", 150))
        parametros = {
            "objective": "binary:logistic",
            "tree_method": "hist",
            "device": dispositivo,
            "seed": definicion.semilla,
            "nthread": 2,
            "verbosity": 0,
            "monotone_constraints": "(" + ",".join(str(v.monotonia) for v in definicion.variables) + ")",
            **hiper,
        }
        matriz = xgb.DMatrix(X[entreno], label=y[entreno], feature_names=definicion.nombres)
        modelo = xgb.train(parametros, matriz, num_boost_round=rondas)
        modelo.save_model(str(ruta_modelo(definicion, carpeta)))
    else:
        raise ValueError(f"Tipo de modelo desconocido: {definicion.tipo}")

    # Métricas sobre la partición de prueba, usando el artefacto recién guardado.
    cargado = _Artefacto(definicion, carpeta, dispositivo)
    p, contribuciones = cargado.predecir_lote(X[prueba])
    predicho = (p >= 0.5).astype(int)
    real = y[prueba]
    positivos = max(int((real == 1).sum()), 1)
    negativos = max(int((real == 0).sum()), 1)
    importancia = np.abs(contribuciones).mean(axis=0)
    metricas = {
        "especialista": definicion.nombre,
        "version_modelo": definicion.version,
        "tipo_modelo": definicion.tipo,
        "datos_entrenamiento": "sintéticos",
        "semilla": definicion.semilla,
        "n_entrenamiento": int(len(entreno)),
        "n_prueba": int(len(prueba)),
        "prevalencia_riesgo": round(float(y.mean()), 4),
        "auc": round(auc(real, p), 4),
        "exactitud": round(float((predicho == real).mean()), 4),
        "sensibilidad": round(float(((predicho == 1) & (real == 1)).sum() / positivos), 4),
        "especificidad": round(float(((predicho == 0) & (real == 0)).sum() / negativos), 4),
        "brier": round(float(((p - real) ** 2).mean()), 4),
        "importancia_global": {
            nombre: round(float(valor), 4)
            for nombre, valor in sorted(zip(definicion.nombres, importancia), key=lambda par: -par[1])
        },
        "dispositivo_entrenamiento": dispositivo,
        "sha256_modelo": hashlib.sha256(ruta_modelo(definicion, carpeta).read_bytes()).hexdigest(),
        "nota": (
            "Métricas medidas sobre datos sintéticos generados con reglas propias. "
            "Indican que el modelo aprendió esas reglas; NO son evidencia de validez clínica."
        ),
    }
    ruta_metricas(definicion, carpeta).write_text(
        json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Modelo %s v%s entrenado: AUC=%.3f (%s)", definicion.nombre, definicion.version,
             metricas["auc"], dispositivo)
    return metricas


# --------------------------------------------------------------------------
# Predicción
# --------------------------------------------------------------------------

class _Artefacto:
    """Modelo guardado en disco, con una interfaz única para los dos tipos."""

    def __init__(self, definicion: Definicion, carpeta: Path, dispositivo: str):
        self.definicion = definicion
        ruta = ruta_modelo(definicion, carpeta)
        if definicion.tipo == "logistica":
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            if datos["variables"] != definicion.nombres:
                raise ValueError("El artefacto no corresponde a las variables de la definición.")
            self.medias = np.array(datos["medias"])
            self.escalas = np.array(datos["escalas"])
            self.coeficientes = np.array(datos["coeficientes"])
            self.intercepto = float(datos["intercepto"])
            self.referencia = np.array([v.referencia for v in definicion.variables])
        else:
            import xgboost as xgb

            self.xgb = xgb
            self.modelo = xgb.Booster()
            self.modelo.load_model(str(ruta))
            self.modelo.set_param({"device": dispositivo, "nthread": 2})

    def predecir_lote(self, X: np.ndarray):
        """Devuelve (probabilidades, contribuciones por variable en log-odds)."""
        if self.definicion.tipo == "logistica":
            z = ((X - self.medias) / self.escalas) @ self.coeficientes + self.intercepto
            # Aporte de cada variable respecto al valor de referencia sano.
            contribuciones = (X - self.referencia) / self.escalas * self.coeficientes
            return _sigmoide(z), contribuciones
        matriz = self.xgb.DMatrix(X, feature_names=self.definicion.nombres)
        # pred_contribs devuelve valores SHAP por variable (+ una columna de sesgo).
        shap = self.modelo.predict(matriz, pred_contribs=True)
        return _sigmoide(shap.sum(axis=1)), shap[:, :-1]


class ModeloEspecialista:
    """Carga el artefacto (o lo entrena si falta) y responde consultas."""

    def __init__(self, definicion: Definicion, carpeta: Path, dispositivo: str | None = None):
        self.definicion = definicion
        self.carpeta = Path(carpeta)
        if dispositivo is None:
            if definicion.tipo == "boosting":
                from comun.especialista.dispositivo import detectar_dispositivo

                dispositivo = detectar_dispositivo()
            else:
                dispositivo = "cpu"
        self.dispositivo = dispositivo
        if not ruta_modelo(definicion, self.carpeta).exists():
            log.warning("No hay artefacto guardado de %s; se entrena ahora.", definicion.nombre)
            entrenar(definicion, self.carpeta, self.dispositivo)
        self.artefacto = _Artefacto(definicion, self.carpeta, self.dispositivo)
        ruta = ruta_metricas(definicion, self.carpeta)
        self.metricas = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}

    def _vector(self, datos: dict):
        """Arma el vector de entrada. Lo que falta se imputa con la referencia."""
        extraido = self.definicion.extraer(datos)
        x, valores, faltantes, fuera = [], {}, [], []
        for variable in self.definicion.variables:
            crudo = extraido.get(variable.nombre)
            if crudo is None or not np.isfinite(crudo):
                faltantes.append(variable.nombre)
                valores[variable.nombre] = None
                x.append(variable.referencia)
                continue
            valores[variable.nombre] = float(crudo)
            if crudo < variable.minimo or crudo > variable.maximo:
                fuera.append(variable.nombre)   # fuera del rango visto al entrenar
            x.append(min(max(float(crudo), variable.minimo), variable.maximo))
        return np.array([x]), valores, faltantes, fuera

    def predecir(self, datos: dict) -> dict:
        """Respuesta del especialista (sin consulta_id; lo añade la API)."""
        definicion = self.definicion
        X, valores, faltantes, fuera = self._vector(datos)
        probabilidades, contribuciones = self.artefacto.predecir_lote(X)
        riesgo = float(np.clip(probabilidades[0], 0.0, 1.0))
        nivel = nivel_por_riesgo(riesgo, definicion.cortes_nivel)

        factores = []
        for variable, aporte in zip(definicion.variables, contribuciones[0]):
            if variable.nombre in faltantes:
                continue   # un dato imputado no explica nada
            valor = valores[variable.nombre]
            factores.append({
                "indicador": variable.nombre,
                "etiqueta": variable.etiqueta,
                "valor": round(valor, 2),
                "aporte": round(float(aporte), 3),
                "frase": variable.frase_alto if valor >= variable.referencia else variable.frase_bajo,
            })
        factores.sort(key=lambda f: -abs(f["aporte"]))
        factores = factores[:4]

        # Confianza heurística (no calibrada): baja si faltan datos, si están fuera
        # del rango de entrenamiento o si el riesgo queda cerca de la mitad.
        total = len(definicion.variables)
        confianza = (
            (1.0 - 0.5 * len(faltantes) / total)
            * (1.0 - 0.3 * len(fuera) / total)
            * (0.60 + 0.40 * abs(2.0 * riesgo - 1.0))
        )

        suben = [f["frase"] for f in factores if f["aporte"] > 0.05][:2]
        explicacion = f"Riesgo {PALABRA_RIESGO[nivel]} de {definicion.riesgo_que_estima}."
        if suben and nivel != "verde":
            explicacion += " Lo que más pesa: " + " y ".join(suben) + "."
        if faltantes:
            explicacion += " Faltan algunos datos, así que la estimación es menos segura."

        return {
            "especialista": definicion.nombre,
            "riesgo": round(riesgo, 3),
            "nivel": nivel,
            "factores": factores,
            "explicacion_corta": explicacion,
            "confianza": round(float(np.clip(confianza, 0.0, 1.0)), 2),
            "version_modelo": definicion.version,
            "datos_entrenamiento": "sintéticos",
            "dispositivo": self.dispositivo,
            "laptop": definicion.laptop,
            "datos_faltantes": faltantes,
        }

    def info(self) -> dict:
        definicion = self.definicion
        return {
            "especialista": definicion.nombre,
            "titulo": definicion.titulo,
            "version_modelo": definicion.version,
            "tipo_modelo": definicion.tipo,
            "laptop": definicion.laptop,
            "dispositivo": self.dispositivo,
            "nota_dispositivo": (
                "Modelo lineal: la GPU no aporta, siempre corre en CPU."
                if definicion.tipo == "logistica"
                else "XGBoost usa CUDA si detecta una GPU NVIDIA; si no, CPU."
            ),
            "datos_entrenamiento": "sintéticos",
            "variables": [
                {"nombre": v.nombre, "etiqueta": v.etiqueta, "unidad": v.unidad,
                 "minimo": v.minimo, "maximo": v.maximo, "referencia": v.referencia}
                for v in definicion.variables
            ],
            "cortes_nivel": list(definicion.cortes_nivel),
            "metricas": self.metricas,
            "limitaciones": list(definicion.limitaciones),
        }
