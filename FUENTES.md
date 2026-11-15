# Fuentes de los umbrales

> **Prototipo con datos simulados. No es una herramienta de diagnóstico médico.**

Este documento dice, umbral por umbral, de dónde sale cada número de
`laptop3-orquestador/reglas/config/umbrales.toml`. Cada bloque de ese archivo lleva un campo `fuente`
que resume lo mismo y remite a las referencias [F1] a [F10] de aquí.

## Reglas de este documento

1. **No se inventan citas, números, páginas ni enlaces. No se cita de memoria.** Una fuente solo cuenta si se
   abrió el documento y se comprobó el pasaje. Si no se pudo abrir, no cuenta como verificada.
2. **Fuentes admitidas:** normas y documentos de la NASA, artículos científicos revisados por pares, guías de
   agencias espaciales (ESA, CSA, JAXA) y guías clínicas de sociedades médicas.
3. **De cada fuente se registra:** autores, título, revista o editor, año, DOI o URL, fecha de consulta y la
   licencia, si la indica.
4. **No se copian artículos con derechos de autor.** Solo una cita corta entre comillas con su referencia; el
   resto se parafrasea. En este documento cada fuente lleva una sola cita, de menos de 15 palabras.
5. **No se guardan en el repositorio PDF de artículos protegidos.** Solo la referencia y el enlace.
6. **Si un número no aparece textual en la fuente, no se le atribuye.** Se escribe "principio respaldado por
   [fuente]; corte de diseño propio".
7. **Los cortes son decisiones de diseño.** Un corte como "1 h de sueño bajo tu línea base = amarillo" no está
   en ninguna norma ni artículo. La fuente respalda la idea; el número lo eligió el equipo como valor de
   ejemplo. Ningún corte de `umbrales.toml` es un valor copiado de una fuente.

## Cómo se comprobó cada fuente

| Nivel | Qué significa | Fuentes |
|---|---|---|
| **Verificada por el equipo** | Una persona del equipo abrió el documento y confirmó el dato | [F1], solo el requisito [V1 4030] |
| **Comprobada por el asistente** | El asistente abrió el documento el 2026-11-15 con una herramienta de lectura web y encontró el pasaje. El pasaje apareció igual en al menos dos lecturas independientes | [F1] (otros requisitos), [F2] a [F9] |
| **Solo resumen** | Solo se pudo abrir el resumen, no el artículo. **No cuenta como verificada** | [F10] |
| **No abierta** | Se localizó, pero no se pudo abrir. **No cuenta** | Lista al final |

La herramienta de lectura devuelve el texto por partes. Antes de presentar una cita ante el jurado conviene que
una persona abra el enlace y confirme el pasaje a la vista. Cada referencia trae el dato exacto que hay que
buscar.

## Resumen

De los 18 bloques de `umbrales.toml`:

- **1** tiene el límite verificado por el equipo (dosis acumulada; sus cortes son escalones de diseño).
- **14** tienen un principio respaldado por una fuente abierta y comprobada. Sus cortes son de diseño propio.
- **3** siguen como `FUENTE POR CITAR`: pulso en reposo, variabilidad del pulso y la regla CARDIOVASCULAR.

Aparte del límite de 600 mSv, solo en dos casos aparece en la fuente un número que coincide con un valor del
prototipo: el plan de ejercicio de 2 horas al día ([F4]) y la caída de 3 puntos de saturación ([F8], con
matices). Los 2 días de adaptación caen dentro del rango de 2 a 3 días de [F7]. En todos los demás la fuente
respalda la idea y no el número.

## Estado de cada umbral

| Bloque de `umbrales.toml` | Valores de ejemplo | Fuente | Qué dice la fuente | Qué es diseño propio |
|---|---|---|---|---|
| `contexto.dosis_acumulada` | 50 / 150 / 250 mSv | [F1] [V1 4030], **verificada por el equipo** | Dosis de carrera menor a 600 mSv | Los tres cortes: escalones hacia ese límite |
| `general` (adaptación) | 2 días, umbrales ×1.5 | [F7] | El mareo espacial dura en general 2-3 días en vuelo | El valor de 2 días y el factor 1.5 |
| `indicadores.sueno_h` | 1 / 2.5 / 3.5 h bajo la base; 3 días | [F2] | Los adultos deben dormir 7 h o más por noche | Todos los cortes y los días |
| `indicadores.animo` | 2 / 3 puntos bajo la base; 3 días | [F9] | El confinamiento prolongado afecta la salud conductual, distinto en cada persona | La escala, los cortes y los días |
| `indicadores.estres` | 20 / 35 / 55 puntos sobre la base; 4 días | [F9] | Lo mismo | La escala de 0 a 100, los cortes y los días |
| `indicadores.ejercicio_min` | 30 % / 50 % bajo el plan; 5 días | [F4], [F1] [V1 4024] y [V1 4027] | Unas dos horas de ejercicio al día; mantener fuerza muscular y densidad ósea | Los porcentajes y los días |
| `indicadores.fc_reposo` | +15 % / +25 % / +40 % | **FUENTE POR CITAR** (candidata [F10]) | Sin fuente verificada | Todo |
| `indicadores.hrv` | −20 % / −35 % / −50 % | **FUENTE POR CITAR** (candidata [F10]) | Sin fuente verificada | Todo |
| `indicadores.spo2` | 3 / 5 / 8 puntos bajo la base | [F8] | Rango objetivo 94-98 %; evaluar ante una caída súbita de más de 3 % | Los cortes de 5 y 8 puntos; el de 3 se apoya en la guía con matices |
| `indicadores.temperatura` | +0.8 / +1.3 / +2.0 °C | [F3] | La temperatura central en reposo sube cerca de 1 °C en misiones largas | Los tres cortes |
| `indicadores.ingesta_pct` | menos del 75 % del plan | [F1] [V1 4020], [F5] | Dar el 100 % de las necesidades; ingesta media observada de 74 % | El corte de 75 % |
| `indicadores.tasa_dosis_usv_h` | 60 / 200 / 1000 µSv/h | [F6], [F1] [V1 4031] | Hasta 647 µSv/día dentro de la ISS; protección ante eventos solares | Los tres cortes |
| `combinaciones.FATIGA` | sueño −0.4 h 3 días, estrés +20, ejercicio 120 %, ánimo −2 | [F2], [F9] | Dormir menos de 7 h se asocia a peor rendimiento y más errores | La combinación y sus números |
| `combinaciones.AISLAMIENTO` | ánimo bajando 4 días, cohesión 2.5 o menos | [F9] | Síntomas depresivos y conflictos en confinamiento prolongado | La combinación y sus números |
| `combinaciones.PERDIDA_MUSCULAR_OSEA` | menos del 50 % del plan, 3 y 5 días | [F1] [V1 4024] y [V1 4027], [F4] | Mantener fuerza y hueso; pérdida media de 1 % de densidad ósea al mes | Los porcentajes y los días |
| `combinaciones.RADIACION` | tasa 200 µSv/h, pulso +10 %, temperatura +0.8 °C | [F1] [V1 4031], [F6] | Proteger a la tripulación ante eventos de partículas solares | Todos los números |
| `combinaciones.CARDIOVASCULAR` | pulso +15 %, HRV −20 %, sueño −1 h | **FUENTE POR CITAR** (candidata [F10]) | Sin fuente verificada | Todo |
| `combinaciones.ENERGIA_BAJA` | menos del 60 % del plan, 2 días | [F1] [V1 4020], [F5] | Lo mismo que la comida; media de 64 % en Apolo | El corte de 60 % y los días |

Los límites de la validación de sensores (`laptop1-backend-frontend/backend/config/sensores.toml`) son valores
de ejemplo sin fuente. Están explicados en `laptop1-backend-frontend/SUPUESTOS.md`.

## Referencias

Fecha de consulta de todas: **2026-11-15**.

### [F1] NASA-STD-3001 Volumen 1, Revisión C

- **Autores:** National Aeronautics and Space Administration (NASA).
- **Título:** NASA-STD-3001, Volume 1, Revision C (Crew Health).
- **Editor:** NASA, publicado en standards.nasa.gov.
- **Año:** 2023 (aprobada el 2023-09-15).
- **URL:** https://standards.nasa.gov/sites/default/files/standards/NASA/C//nasa-std-3001-vol-1-rev-c-signature.pdf
- **Licencia:** el documento no indica ninguna.
- **Cómo se comprobó:** [V1 4030] verificado por el equipo. Los demás requisitos los leyó el asistente en tres
  lecturas del PDF, en el cuerpo y en la matriz de requisitos del apéndice.
- **Pasajes** (un solo fragmento citado; el resto, parafraseado):
  - [V1 4030], sección 4.8.2: la dosis efectiva total de carrera por radiación espacial "shall be less than
    600 mSv". Se basa en 3 % REID de mortalidad por cáncer.
  - [V1 4031], sección 4.8.3: el programa debe proteger a la tripulación del evento de partículas solares de
    referencia de diseño, por debajo de una dosis efectiva de 250 mSv.
  - [V1 4020], sección 4.5.2: dar a cada tripulante el 100 % de sus necesidades calculadas de nutrientes y energía.
  - [V1 4024], sección 4.6.2: las contramedidas deben mantener la fuerza del músculo esquelético en 80 % o más
    del valor base.
  - [V1 4027], sección 4.7.2: mantener la densidad mineral ósea de cadera y columna en 95 % o más del valor previo.
- **Qué no respalda:** ningún corte del prototipo. El límite es de carrera y el prototipo lo compara con la dosis
  de una misión simulada. El 250 mSv de [V1 4031] es una dosis por evento solar; coincide en la cifra con el
  corte rojo de dosis acumulada, pero mide otra cosa y no lo justifica.

Cortes de dosis acumulada como parte del límite de 600 mSv: amarillo 50 mSv (8 %), naranja 150 mSv (25 %),
rojo 250 mSv (42 %). Son escalones internos de diseño para avisar con tiempo.

### [F2] Consenso AASM/SRS sobre las horas de sueño

- **Autores:** Watson NF, Badr MS, Belenky G, Bliwise DL, Buxton OM, Buysse D, Dinges DF, Gangwisch J,
  Grandner MA, Kushida C, Malhotra RK, Martin JL, Patel SR, Quan SF, Tasali E.
- **Título:** Recommended Amount of Sleep for a Healthy Adult: A Joint Consensus Statement of the American
  Academy of Sleep Medicine and Sleep Research Society.
- **Revista:** Journal of Clinical Sleep Medicine 11(6):591–592. Publicado también en Sleep 38(6):843–844.
- **Año:** 2015.
- **DOI:** 10.5664/jcsm.4758 (J Clin Sleep Med); 10.5665/sleep.4716 (Sleep).
- **URL abierta:** https://www.aasm.org/resources/pdf/adultsleepdurationconsensus.pdf
- **Licencia:** el PDF no indica ninguna. Se trata como material con derechos de autor.
- **Pasaje:** "Adults should sleep 7 or more hours per night on a regular basis". El consenso añade que dormir
  menos de 7 horas se asocia a peor rendimiento, más errores y más riesgo de accidentes.
- **Qué respalda:** que dormir poco es un riesgo para el rendimiento. La línea base de sueño del perfil (7.2 h)
  queda por encima de esas 7 horas.
- **Qué no respalda:** los cortes de 1, 2.5 y 3.5 h bajo la base, ni los días de persistencia.

### [F3] Temperatura corporal en misiones largas

- **Autores:** Stahn AC, Werner A, Opatz O, Maggioni MA, Steinach M, von Ahlefeld VW, Moore A, Crucian BE,
  Smith SM, Zwart SR, Schlabs T, Mendt S, Trippel T, Koralewski E, Koch J, Choukèr A, Reitz G, Shang P,
  Röcker L, Kirsch KA, Gunga HC.
- **Título:** Increased core body temperature in astronauts during long-duration space missions.
- **Revista:** Scientific Reports 7:16180.
- **Año:** 2017.
- **DOI:** 10.1038/s41598-017-15560-w. **URL abierta:** https://pmc.ncbi.nlm.nih.gov/articles/PMC5701078
- **Licencia:** Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Pasaje:** "At rest CBT was increased by about 1.01 °C on the ISS". El aumento se desarrolló poco a poco
  durante unos dos meses y medio.
- **Qué respalda:** que la temperatura es un indicador que cambia en el espacio y merece vigilancia.
- **Qué no respalda:** los cortes de +0.8, +1.3 y +2.0 °C.
- **Aviso para el diseño:** según este estudio, un astronauta sano en una misión larga puede estar cerca de
  1 °C por encima de su valor en tierra. Con los cortes actuales eso daría amarillo sin enfermedad. El
  prototipo simula 7 días y recalibra la base solo con los días 1 y 2; una misión larga necesitaría recalibrar
  la línea base de temperatura de forma periódica.

### [F4] Ejercicio en la Estación Espacial (Agencia Espacial Canadiense)

- **Autor y editor:** Canadian Space Agency (CSA), Gobierno de Canadá.
- **Título:** Physical activity in space.
- **Año:** página web; fecha de modificación indicada: 2025-12-03.
- **URL:** https://www.asc-csa.gc.ca/eng/astronauts/living-in-space/physical-activity-in-space.asp
- **Licencia:** no indica una licencia abierta. Sus condiciones (https://www.asc-csa.gc.ca/eng/terms.asp)
  permiten reproducir el contenido para uso personal, educativo o informativo no comercial, citando a la CSA.
- **Pasaje:** "astronauts must exercise approximately two hours per day". La página dice también que, pese al
  ejercicio, los astronautas pierden en promedio 1 % de densidad ósea al mes.
- **Qué respalda:** el plan de ejercicio de 120 minutos al día (`plan.ejercicio_min` en `perfil.toml`). Aquí el
  número sí aparece en la fuente.
- **Qué no respalda:** los cortes de 30 % y 50 % bajo el plan, ni los días.

### [F5] Nutrición en vuelos espaciales (NASA)

- **Autores:** Smith SM, Zwart SR (NASA Johnson Space Center; Universities Space Research Association).
- **Título:** Nutrition issues for space exploration.
- **Editor:** NASA Technical Reports Server, documento 20060049121.
- **Año:** el PDF no indica fecha.
- **URL:** https://ntrs.nasa.gov/api/citations/20060049121/downloads/20060049121.pdf
- **Licencia:** el PDF no indica ninguna.
- **Pasaje:** la ingesta media de energía de 15 tripulantes de la ISS "was 74 ± 11% of the WHO recommendation".
  El documento recoge también una media de 64 ± 14 % en las misiones Apolo y dice que algunas tripulaciones de
  la ISS mantuvieron entre 85 y 95 %.
- **Qué respalda:** que comer menos de lo planeado es frecuente en vuelo y preocupa.
- **Qué no respalda:** los cortes de 75 % y 60 %. Las cifras de la fuente son promedios observados, no umbrales
  de alarma. Que queden cerca de los cortes del prototipo es una coincidencia, no una justificación.

### [F6] Radiación medida dentro de la Estación Espacial

- **Autores:** Berger T, Burmeister S, Matthiä D, Przybyla B, Reitz G, Bilski P, Hajek M, Sihver L, Szabo J,
  Ambrozova I, Vanhavere F, Gaza R, Semones E, Yukihara EG, Benton ER, Uchihori Y, Kodaira S, Kitamura H, Boehme M.
- **Título:** DOSIS & DOSIS 3D: radiation measurements with the DOSTEL instruments onboard the Columbus
  Laboratory of the ISS in the years 2009–2016.
- **Revista:** Journal of Space Weather and Space Climate 7:A8.
- **Año:** 2017.
- **DOI:** 10.1051/swsc/2017005. **URL abierta:** https://www.swsc-journal.org/10.1051/swsc/2017005
- **Licencia:** Creative Commons Attribution 4.0 (CC BY 4.0).
- **Pasaje:** a finales de mayo de 2016 la dosis absorbida llegó a 286 µGy/día, "with dose equivalent values of
  647 μSv/day".
- **Qué respalda:** el orden de magnitud de la tasa habitual. 647 µSv/día son unos 27 µSv/h (la división entre
  24 es nuestra, no de la fuente). El guion simulado usa 21 µSv/h.
- **Qué no respalda:** los cortes de 60, 200 y 1000 µSv/h.

### [F7] Adaptación a la microgravedad (NASA)

- **Autores:** Wood SJ, Reschke MF, Harm DL, Paloski WH, Bloomberg JJ.
- **Título:** Which Way is Up? Lessons Learned from Space Shuttle Sensorimotor Research.
- **Editor:** NASA Technical Reports Server, documento 20110016709 (tipo de documento: resumen).
- **Año:** 2011.
- **URL:** https://ntrs.nasa.gov/citations/20110016709
- **Licencia:** el registro de NASA indica que se permite el uso público.
- **Pasaje:** "SMS generally lasted 2-3 days in-flight" (SMS: mareo por movimiento en el espacio).
- **Qué respalda:** que los primeros días el cuerpo se está adaptando y conviene ser más tolerante.
- **Qué no respalda:** el valor exacto de 2 días ni el factor 1.5. La fuente da un rango de 2 a 3 días para un
  síntoma concreto; el prototipo eligió 2 días para todos los indicadores.

### [F8] Saturación de oxígeno (British Thoracic Society)

- **Autores:** British Thoracic Society. El documento cita la guía completa como: O'Driscoll BR et al.,
  Thorax 2017; 72: Suppl 1 i1-i89.
- **Título:** BTS Guideline for oxygen use in adults in healthcare and emergency settings. Web Appendix 5:
  Summary of Guideline and flow charts for emergency oxygen use in ambulances, community and pre-hospital settings.
- **Editor:** British Thoracic Society.
- **Año:** 2017 (mayo).
- **URL:** https://brit-thoracic.org.uk/document-library/guidelines/emergency-oxygen/web-appendix-5-summary-for-ambulance-and-prehospital-settings
- **Licencia:** el documento no indica ninguna. Se trata como material con derechos de autor.
- **Pasaje:** el rango objetivo de saturación para la mayoría de los pacientes es 94-98 %. "A sudden reduction
  of more than 3% in a patient's oxygen saturation" dentro del rango objetivo pide una evaluación más completa.
- **Qué respalda:** el corte amarillo de 3 puntos bajo la base, con dos matices: la guía dice "más de 3 %" y
  el prototipo usa "3 puntos o más"; y la guía habla de pacientes en atención sanitaria, no de astronautas sanos.
- **Qué no respalda:** los cortes de 5 y 8 puntos.

### [F9] Salud conductual en confinamiento prolongado (Mars-500)

- **Autores:** Basner M, Dinges DF, Mollicone DJ, Savelev I, Ecker AJ, Di Antonio A, Jones CW, Hyder EC, Kan K,
  Morukov BV, Sutton JP.
- **Título:** Psychological and Behavioral Changes during Confinement in a 520-Day Simulated Interplanetary
  Mission to Mars.
- **Revista:** PLoS ONE 9(3):e93298.
- **Año:** 2014.
- **DOI:** 10.1371/journal.pone.0093298 (https://doi.org/10.1371/journal.pone.0093298).
- **Licencia:** Creative Commons Attribution (CC BY), © 2014 Basner et al.
- **Cómo se comprobó:** las páginas del editor y de PubMed Central no abrieron con la herramienta. Se leyó el
  PDF de la revista en una copia alojada por un tercero
  (https://www.dawsoncollege.qc.ca/writing/wp-content/uploads/sites/196/Article-Mission-to-Mars.pdf); la licencia
  CC BY permite esa copia. Conviene confirmarlo en el enlace del DOI.
- **Pasaje:** "Behavioral health risks are among the most serious and difficult to mitigate risks" del
  confinamiento en misiones largas. Un tripulante tuvo síntomas de depresión en el 93 % de las semanas y los
  conflictos con el control de misión se reportaron cinco veces más que entre tripulantes.
- **Qué respalda:** vigilar el ánimo, el estrés y la relación con el equipo, y hacerlo persona por persona.
- **Qué no respalda:** ninguna escala ni corte del prototipo. Es una simulación en tierra con 6 personas.

### [F10] Control autonómico en vuelos largos — SOLO RESUMEN, no cuenta como verificada

- **Autores:** Baevsky RM, Baranov VM, Funtova II, Diedrich A, Pashenko AV, Chernikova AG, Drescher J, Jordan J, Tank J.
- **Título:** Autonomic cardiovascular and respiratory control during prolonged spaceflights aboard the
  International Space Station.
- **Revista:** Journal of Applied Physiology 103(1):156–161. American Physiological Society.
- **Año:** 2007.
- **DOI:** 10.1152/japplphysiol.00137.2007.
- **URL abierta:** https://edoc.mdc-berlin.de/id/eprint/9190/ (registro del repositorio institucional, con el resumen).
- **Licencia:** el registro la marca como de acceso cerrado. Con derechos de autor.
- **Pasaje del resumen:** "Impaired autonomic control represents a cardiovascular risk factor during long-term
  spaceflight". El resumen dice también que el pulso medio y la variabilidad no cambiaron durante el vuelo.
- **Por qué no cuenta:** no se pudo abrir el artículo, solo su resumen. Queda como candidata para el pulso, la
  variabilidad del pulso y la regla CARDIOVASCULAR.

## Fuentes localizadas que no se pudieron abrir (no cuentan)

| Fuente | Para qué serviría | Qué pasó |
|---|---|---|
| Barger LK et al. Prevalence of sleep deficiency and use of hypnotic drugs in astronauts before, during, and after spaceflight. Lancet Neurol 2014;13(9):904–912. DOI 10.1016/S1474-4422(14)70122-X | Horas de sueño reales de astronautas en vuelo | PubMed Central pidió una verificación anti-robots. El texto solo se vio en el buscador |
| Task Force ESC/NASPE. Heart rate variability: standards of measurement, physiological interpretation, and clinical use. Circulation 1996;93(5):1043–1065. DOI 10.1161/01.CIR.93.5.1043 | Variabilidad del pulso | No se pudo abrir en la revista. PubMed no trae resumen |
| O'Grady NP et al. SCCM and IDSA Guidelines for Evaluating New Fever in Adult Patients in the ICU. Crit Care Med 2023;51(11):1570–1586. DOI 10.1097/CCM.0000000000006022 | Definición clínica de fiebre | Se abrió el resumen en PubMed, pero la cifra que define la fiebre no está en el resumen |
| Petersen N et al. Exercise in space: the European Space Agency approach to in-flight exercise countermeasures. Extrem Physiol Med 2016;5:9. DOI 10.1186/s13728-016-0050-4 (CC BY 4.0) | Tiempo de ejercicio según la ESA | La página del editor redirige y la herramienta no la siguió |
| O'Driscoll BR, Howard LS, Earis J, Mak V. BTS Guideline for oxygen use (resumen). BMJ Open Respir Res 2017;4:e000170. DOI 10.1136/bmjresp-2016-000170 | Saturación de oxígeno | No abrió. Se usó en su lugar el apéndice de la propia sociedad, [F8] |
| Smith SM et al. The nutritional status of astronauts is altered after long-term space flight aboard the ISS. J Nutr 2005;135(3):437–443. DOI 10.1093/jn/135.3.437 | Ingesta de energía | No se abrió. Se usó [F5] |
| Página del riesgo del NASA Human Research Program sobre pérdida de sueño, desajuste circadiano y sobrecarga de trabajo | Sueño y fatiga | Solo se comprobó el título |
| American Heart Association, página sobre la frecuencia cardíaca en reposo | Pulso en reposo | La herramienta no permitió abrir el enlace |

## Lo que se buscó y no se encontró

- **Horas de sueño y minutos de ejercicio en la norma de la NASA.** En NASA-STD-3001 Vol. 1 Rev. C no hay ningún
  requisito con horas de sueño. En el Vol. 2 Rev. F, las secciones 7.4 (contramedidas fisiológicas) y 7.9 (salud
  conductual y sueño) no dan horas ni minutos. Del Vol. 2 solo se leyeron el índice y esas dos secciones.
  Enlace: https://standards.nasa.gov/system/files/tmp/NASA-STD-3001%20Vol%202%20Rev%20F.pdf
- **Pulso, variabilidad del pulso y temperatura corporal en la norma.** En el Vol. 1 Rev. C no hay requisitos
  con cifras para estos indicadores.
- **Documentos no abiertos:** Human Integration Design Handbook, informes de evidencia del Human Research
  Program, la sección 6.8 (radiación) del Vol. 2 y las páginas de la ESA y la JAXA.

## Cómo añadir o confirmar una fuente

1. Abrir el documento real y localizar la frase. Si no se puede abrir, no cuenta.
2. Añadir aquí una referencia `### [Fn]` con autores, título, revista o editor, año, DOI o URL, fecha de
   consulta, licencia y una sola cita corta.
3. Cambiar el campo `fuente` del bloque en `umbrales.toml`. Si el número del umbral no aparece textual en la
   fuente, escribir "principio respaldado por [Fn]; corte de diseño propio".
4. Actualizar `PENDIENTES` en `laptop3-orquestador/reglas/pruebas/test_reglas.py`. Las pruebas comprueban que
   cada referencia citada en `umbrales.toml` existe aquí con su enlace y su fecha de consulta.
5. No guardar en el repositorio el PDF de un artículo protegido.
