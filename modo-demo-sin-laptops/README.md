# Modo demo sin las tres laptops

Levanta el backend y el orquestador en **una sola máquina**. Los modelos no se ejecutan: el orquestador responde
con **respuestas grabadas de ejecuciones reales** de los especialistas. Así los jueces pueden abrir el repositorio
sin el hardware, y la grabación del video es repetible.

**La pantalla lo indica en todo momento:** "Demo en una sola máquina. Las respuestas de los modelos son resultados guardados."

## Arrancar
```bash
./arrancar_demo.sh          # con Docker: docker compose up --build
./arrancar_demo.sh local    # sin Docker: mismos servicios en procesos locales
```
Interfaz: `http://localhost:8100/`.

## Cómo se grabó
`grabar_respuestas.py` recorre todos los estados que la demo puede producir:
- día de misión 1–7,
- evento solar apagado o encendido en cada día,
- Laptop 2 encendida o apagada.

Por cada consulta real guarda la respuesta del especialista, con una clave que depende solo de lo que el
especialista recibe. Resultado: `respuestas-guardadas.json` (88 respuestas, 112 estados).

Regenerar (requiere los modelos en la raíz del repositorio):
```bash
python3 modo-demo-sin-laptops/grabar_respuestas.py
```

## Limitaciones
- Solo cubre los estados recorridos. Si el presentador introduce **datos a mano** que no estaban en la grabación,
  los especialistas quedan como "no hay respuesta guardada para estos datos" y las reglas siguen funcionando.
- Las respuestas guardadas son de los modelos del prototipo y están marcadas como tales en cada respuesta.

## Pruebas
```bash
python3 -m pytest modo-demo-sin-laptops
```
Comprueba que la historia de 7 días y la caída de la Laptop 2 se reproducen igual con respuestas guardadas.
