"""Librería compartida por las tres laptops.

Contiene solo código sin estado: validación de contratos, niveles de alerta,
logs y la base común de los modelos especialistas. Cada imagen Docker copia
esta carpeta, así que ninguna laptop depende de otra para arrancar.
"""

AVISO = "Prototipo con datos simulados. No es una herramienta de diagnóstico médico."
