// English dictionary for text that the backend sends in Spanish.
//
// The backend (Laptop 1) and the orchestrator (Laptop 3) still produce Spanish
// text: indicator names, alert titles, protocol steps, explanations. This module
// translates that text at render time so the whole page reads in English without
// touching the other services.
//
// If a backend string changes and is not covered here, the helper falls back to a
// generic English sentence, never to the Spanish original.

import { NOMBRES_ESPECIALISTA } from "./util.js";

// ---------------------------------------------------------------------------
// Indicator catalog (names and units shown next to a value)
// ---------------------------------------------------------------------------
export const INDICADORES = {
  sueno_h: { nombre: "Sleep", unidad: "h" },
  animo: { nombre: "Mood", unidad: "of 5" },
  estres: { nombre: "Stress", unidad: "of 100" },
  ejercicio_min: { nombre: "Exercise", unidad: "min" },
  fc_reposo: { nombre: "Resting pulse", unidad: "bpm" },
  hrv: { nombre: "Heart-rate variability", unidad: "ms" },
  spo2: { nombre: "Oxygen level", unidad: "%" },
  temperatura: { nombre: "Temperature", unidad: "°C" },
  ingesta_pct: { nombre: "Food", unidad: "% of plan" },
  tasa_dosis_usv_h: { nombre: "Radiation now", unidad: "µSv/h" },
  dosis_acumulada_msv: { nombre: "Radiation accumulated", unidad: "mSv" },
  cohesion_equipo: { nombre: "Team cohesion", unidad: "of 5" },
  tiempo_reaccion_ms: { nombre: "Reaction time", unidad: "ms" },
  desfase_circadiano_h: { nombre: "Body-clock offset", unidad: "h" },
  luz_brillante_min: { nombre: "Bright light", unidad: "min" },
  presion_sistolica: { nombre: "Systolic pressure", unidad: "mmHg" },
  presion_diastolica: { nombre: "Diastolic pressure", unidad: "mmHg" },
  glucosa: { nombre: "Glucose", unidad: "mg/dL" },
};

// ---------------------------------------------------------------------------
// Alert titles (by alert id, which is stable across languages)
// ---------------------------------------------------------------------------
export const ALERTAS = {
  SUENO_BAJO: "You are sleeping less than usual",
  ANIMO_BAJO: "Your mood is low",
  ESTRES_ALTO: "Your stress is high",
  EJERCICIO_BAJO: "You did little exercise",
  FC_ALTA: "Your resting pulse is high",
  HRV_BAJA: "Your body is recovering less",
  SPO2_BAJA: "Your oxygen level is low",
  TEMPERATURA_ALTA: "Your temperature is elevated",
  INGESTA_BAJA: "You are eating less than planned",
  TASA_DOSIS_ALTA: "The radiation arriving now is high",
  FATIGA: "Fatigue risk",
  AISLAMIENTO: "Signs of isolation",
  PERDIDA_MUSCULAR_OSEA: "Muscle and bone loss risk",
  RADIACION: "Radiation exposure",
  CARDIOVASCULAR: "Signs of heart strain",
  ENERGIA_BAJA: "Low energy from eating little",
  DOSIS_ACUMULADA: "Radiation accumulated in the mission",
};

const CONSECUENCIA_ALERTA = {
  SUENO_BAJO: "With little sleep your attention drops and mistakes are more likely.",
  ANIMO_BAJO: "Sustained low mood drains energy and affects how the crew gets along.",
  ESTRES_ALTO: "Sustained high stress is tiring, costs you sleep and makes it hard to concentrate.",
  EJERCICIO_BAJO: "Without gravity, muscles and bones weaken if they are not exercised.",
  FC_ALTA: "A high resting pulse means your body is under load.",
  HRV_BAJA: "It is a sign that your body is not recovering well.",
  SPO2_BAJA: "With little oxygen in your blood you may feel tired, dizzy or confused.",
  TEMPERATURA_ALTA: "A high temperature means your body is reacting to something.",
  INGESTA_BAJA: "Eating little leaves you without energy to work and train.",
  TASA_DOSIS_ALTA: "It is best to reduce exposure time.",
  FATIGA: "This combination can cause fatigue: less attention, slower reflexes and more mistakes.",
  AISLAMIENTO: "This is a common sign of isolation on long missions and should be addressed early.",
  PERDIDA_MUSCULAR_OSEA: "In microgravity that speeds up muscle and bone loss.",
  RADIACION: "Exposure must be reduced as soon as possible.",
  CARDIOVASCULAR: "Together, these signs show your heart is working harder than it should.",
  ENERGIA_BAJA: "Without enough food you will lack energy to work and train.",
  DOSIS_ACUMULADA: "It is best to limit further exposure and tell the medical team.",
};

// ---------------------------------------------------------------------------
// Protocols (title and steps by protocol id / step id)
// ---------------------------------------------------------------------------
const TITULOS_PROTOCOLO = {
  sueno: "Recover your sleep",
  animo_estres: "Lower stress and look after your mood",
  fatiga: "Fatigue protocol",
  aislamiento: "Reconnect with the crew",
  muscular_oseo: "Get back to exercise",
  radiacion: "Radiation protocol",
  cardiovascular: "Look after your heart",
  energia: "Recover your energy",
  oxigenacion: "Low oxygen",
  temperatura: "High temperature",
  general: "Watch and wait",
};

// Each step is [Spanish text from the backend, English text shown in the UI].
const PASOS = {
  sueno: {
    s1: ["Hoy termina las tareas exigentes al menos 2 horas antes de dormir.",
      "Finish demanding tasks at least 2 hours before bed today."],
    s2: ["Baja las luces y deja las pantallas 1 hora antes de dormir.",
      "Dim the lights and put screens away 1 hour before bed."],
    s3: ["Por la 'mañana', ponte 30 minutos bajo luz brillante: ayuda a ajustar tu reloj interno.",
      "In your 'morning', spend 30 minutes in bright light: it helps reset your body clock."],
    s4: ["Evita la cafeína en las 6 horas previas a dormir.",
      "Avoid caffeine in the 6 hours before bed."],
    s5: ["Mañana registra cuántas horas dormiste para ver si mejoras.",
      "Tomorrow, log how many hours you slept to see if it improves."],
  },
  animo_estres: {
    a1: ["Haz 5 minutos de respiración lenta: toma aire en 4 segundos y suéltalo en 6.",
      "Take 5 minutes of slow breathing: breathe in for 4 seconds and out for 6."],
    a2: ["Revisa tu agenda y pasa a mañana una tarea que no sea urgente.",
      "Review your schedule and move a non-urgent task to tomorrow."],
    a3: ["Dedica 20 minutos a algo que disfrutes: música, mirar la Tierra por la ventana o escribir a tu familia.",
      "Spend 20 minutes on something you enjoy: music, looking at Earth through the window or writing to your family."],
    a4: ["Cuéntale a un compañero cómo te sientes.",
      "Tell a crewmate how you feel."],
  },
  fatiga: {
    f1: ["Detén las tareas delicadas por ahora: con fatiga es más fácil equivocarse.",
      "Pause delicate tasks for now: when you are tired it is easier to make mistakes."],
    f2: ["Avisa a tu comandante para que redistribuya la carga de trabajo de hoy.",
      "Tell your commander so today's workload can be rearranged."],
    f3: ["Toma una siesta corta de 20 minutos en un lugar oscuro y silencioso.",
      "Take a short 20-minute nap in a dark, quiet place."],
    f4: ["Hoy haz solo ejercicio suave: baja al plan normal o un poco menos.",
      "Only do light exercise today: stay at or a little below the normal plan."],
    f5: ["Come e hidrátate según lo planeado.",
      "Eat and drink as planned."],
    f6: ["Esta noche acuéstate 1 hora antes y deja las pantallas fuera.",
      "Tonight go to bed 1 hour earlier and leave screens outside."],
    f7: ["Repite la prueba de reacción en 15 minutos para ver cómo sigues.",
      "Repeat the reaction test in 15 minutes to see how you are doing."],
  },
  aislamiento: {
    i1: ["Comparte hoy una comida con al menos un compañero.",
      "Share a meal with at least one crewmate today."],
    i2: ["Graba un mensaje para tu familia o amigos; se enviará en el próximo enlace.",
      "Record a message for your family or friends; it will go out on the next link."],
    i3: ["Proponle al equipo una actividad corta en común: una película, un juego o música.",
      "Suggest a short activity for the team: a movie, a game or music."],
    i4: ["Habla con tu comandante sobre cómo se siente el equipo.",
      "Talk to your commander about how the team is feeling."],
  },
  muscular_oseo: {
    m1: ["Reserva hoy tu bloque de ejercicio, aunque sea más corto que el plan.",
      "Block out your exercise time today, even if it is shorter than planned."],
    m2: ["Empieza con 10 minutos suaves y sube poco a poco.",
      "Start with 10 easy minutes and build up slowly."],
    m3: ["Incluye ejercicio de fuerza para piernas y espalda: son las zonas que más pierden.",
      "Include strength exercise for legs and back: those are the areas that lose the most."],
    m4: ["Si algo te impide entrenar (dolor, equipo averiado, falta de tiempo), avisa a tu comandante.",
      "If something keeps you from training (pain, broken equipment, no time), tell your commander."],
  },
  radiacion: {
    r1: ["Ve al refugio o a la zona más protegida de la estación.",
      "Go to the shelter or the most shielded area of the station."],
    r2: ["Avisa a toda la tripulación para que haga lo mismo.",
      "Tell the whole crew to do the same."],
    r3: ["Suspende cualquier salida al exterior.",
      "Cancel any spacewalk or trip outside."],
    r4: ["Quédate en el refugio y vuelve a medir la radiación en 15 minutos.",
      "Stay in the shelter and measure the radiation again in 15 minutes."],
    r5: ["Anota cómo te sientes (náusea, cansancio, dolor de cabeza) para el informe médico.",
      "Note how you feel (nausea, tiredness, headache) for the medical report."],
  },
  cardiovascular: {
    c1: ["Detén el esfuerzo físico y quédate en reposo.",
      "Stop physical effort and rest."],
    c2: ["Respira lento durante 5 minutos.",
      "Breathe slowly for 5 minutes."],
    c3: ["Bebe agua.",
      "Drink water."],
    c4: ["Vuelve a medir tu pulso en 15 minutos.",
      "Measure your pulse again in 15 minutes."],
    c5: ["Si sientes dolor en el pecho, falta de aire o mareo, avisa de inmediato a la tripulación.",
      "If you feel chest pain, shortness of breath or dizziness, tell the crew right away."],
  },
  energia: {
    e1: ["Come ahora algo de tu menú, aunque no tengas hambre.",
      "Eat something from your menu now, even if you are not hungry."],
    e2: ["Bebe agua con la comida.",
      "Drink water with your meal."],
    e3: ["Programa tus comidas de hoy con alarma para no saltarte ninguna.",
      "Schedule today's meals with an alarm so you do not skip any."],
    e4: ["Si tienes náusea o no toleras la comida, avisa a tu comandante.",
      "If you feel nauseous or cannot keep food down, tell your commander."],
  },
  oxigenacion: {
    o1: ["Recoloca el sensor en el dedo, quédate quieto y espera la nueva lectura.",
      "Put the sensor back on your finger, stay still and wait for the new reading."],
    o2: ["Respira profundo y lento durante 2 minutos.",
      "Breathe deeply and slowly for 2 minutes."],
    o3: ["Pide a un compañero que revise la calidad del aire del módulo.",
      "Ask a crewmate to check the air quality in the module."],
    o4: ["Vuelve a medir en 15 minutos.",
      "Measure again in 15 minutes."],
    o5: ["Si te falta el aire o te sientes confundido, avisa de inmediato a la tripulación.",
      "If you are short of breath or feel confused, tell the crew right away."],
  },
  temperatura: {
    t1: ["Descansa y bebe agua.",
      "Rest and drink water."],
    t2: ["Vuelve a medir tu temperatura en 15 minutos.",
      "Measure your temperature again in 15 minutes."],
    t3: ["Anota otros síntomas: escalofríos, dolor, tos.",
      "Note other symptoms: chills, pain, cough."],
    t4: ["Mantén distancia con tus compañeros hasta saber qué pasa y avisa a tu comandante.",
      "Keep your distance from crewmates until you know what is going on and tell your commander."],
  },
  general: {
    g1: ["Revisa tus indicadores de hoy en el tablero.",
      "Check today's indicators on the board."],
    g2: ["Cuida esta noche tu sueño, tu comida y tu hidratación.",
      "Look after your sleep, food and water tonight."],
    g3: ["Vuelve a registrar tus datos mañana para ver la tendencia.",
      "Log your data again tomorrow to see the trend."],
  },
};

export const PROTOCOLOS = Object.fromEntries(
  Object.entries(PASOS).map(([id, pasos]) => [id, {
    titulo: TITULOS_PROTOCOLO[id] || "Protocol",
    pasos: Object.fromEntries(Object.entries(pasos).map(([pid, [, en]]) => [pid, en])),
  }]),
);

const PASO_ES_A_EN = new Map(
  Object.values(PASOS).flatMap((pasos) => Object.values(pasos).map(([es, en]) => [es, en])),
);

// ---------------------------------------------------------------------------
// Why a specialist was consulted (routing table motives)
// ---------------------------------------------------------------------------
export const MOTIVOS = {
  "Dormiste menos de lo normal": "You slept less than usual",
  "Tu estrés está alto": "Your stress is high",
  "Tu ánimo está bajo": "Your mood is low",
  "Comiste menos de lo planeado": "You ate less than planned",
  "Hiciste poco ejercicio": "You did little exercise",
  "Tu pulso en reposo está alto": "Your resting pulse is high",
  "La variabilidad de tu pulso bajó": "Your heart-rate variability dropped",
  "Tu oxigenación está baja": "Your oxygen level is low",
  "Tu temperatura está elevada": "Your temperature is elevated",
  "La radiación que llega ahora es alta": "The radiation arriving now is high",
  "Hay una tormenta solar en curso": "A solar storm is underway",
  "La radiación acumulada es alta": "Accumulated radiation is high",
  "Las reglas ven riesgo de fatiga": "The rules see a fatigue risk",
  "Las reglas ven señales de aislamiento": "The rules see signs of isolation",
  "Las reglas ven sobrecarga del corazón": "The rules see heart strain",
  "Las reglas ven energía baja": "The rules see low energy",
  "Las reglas no vieron motivo para consultarlo.": "The rules saw no reason to consult it.",
  "Modo degradado: se consulta siempre al especialista local":
    "Degraded mode: the local specialist is always consulted",
  "Laptop 2 no disponible (orquestador no disponible)":
    "Laptop 2 unavailable (orchestrator unavailable)",
  "orquestador no disponible": "orchestrator unavailable",
};

// ---------------------------------------------------------------------------
// Escalation text by level, and notes
// ---------------------------------------------------------------------------
export const ESCALAMIENTO = {
  verde: "No action. Keep to your routine.",
  amarillo: "Self-care: follow the protocol on your own and check again tomorrow.",
  naranja: "Tell the crew or your commander and follow the protocol.",
  rojo: "Prepare contact with the flight surgeon. The report is ready for the next link with Earth.",
};

export const NOTAS = {
  "Tras seguir el protocolo": "After following the protocol",
};

export const MUSCULO = { verde: "Low", amarillo: "Medium", naranja: "High", rojo: "Very high" };

export const MODULOS =
  "Blood pressure and glucose are not reliable without dedicated equipment. " +
  "Simulated data from an optional external module.";

export const NOTA_INFORME =
  "Simulated-data prototype. Not a medical diagnostic tool. Models trained on synthetic data.";

// ---------------------------------------------------------------------------
// Factor labels used by the specialist models
// ---------------------------------------------------------------------------
export const ETIQUETAS = {
  sueno_h: "Hours of sleep last night",
  sueno_media_3d: "3-day average sleep",
  irregularidad_h: "Sleep irregularity this week",
  desfase_circadiano_h: "Body-clock offset",
  luz_brillante_min: "Bright light in your morning",
  ejercicio_min: "Exercise today",
  estres: "Perceived stress",
  animo: "Mood",
  hrv_desv_pct: "Heart-rate variability vs your normal",
  fc_desv_pct: "Resting pulse vs your normal",
  fc_reposo: "Resting pulse",
  hrv: "Heart-rate variability",
  ejercicio_pct_plan: "Exercise vs the plan",
  ingesta_pct: "Food vs what was planned",
  cohesion_equipo: "Team cohesion",
  tiempo_reaccion_ms: "Reaction time",
  dia_mision: "Mission day",
  tasa_dosis_usv_h: "Radiation arriving now",
  dosis_acumulada_msv: "Radiation accumulated this mission",
  evento_solar: "Solar storm underway",
  temperatura: "Body temperature",
  spo2: "Oxygen level",
  presion_sistolica: "Blood pressure (external module)",
};

export const RIESGO = {
  sueno: "sleep problems",
  "fatiga-bienestar": "fatigue and emotional strain",
  cardiovascular: "heart and circulation strain",
  "riesgo-solar": "radiation exposure",
};

const PALABRA_RIESGO = { verde: "low", amarillo: "moderate", naranja: "high", rojo: "very high" };

// ---------------------------------------------------------------------------
// Consequences and clause templates for "causa_en_lenguaje_simple"
// ---------------------------------------------------------------------------
const CONSECUENCIAS = [
  ["Esta combinación puede causar fatiga: menos atención, reflejos lentos y más errores.",
    CONSECUENCIA_ALERTA.FATIGA],
  ["Es una señal frecuente de aislamiento en misiones largas y conviene atenderla pronto.",
    CONSECUENCIA_ALERTA.AISLAMIENTO],
  ["En microgravedad eso acelera la pérdida de músculo y de hueso.",
    CONSECUENCIA_ALERTA.PERDIDA_MUSCULAR_OSEA],
  ["Juntas, estas señales indican que tu corazón está trabajando de más.",
    CONSECUENCIA_ALERTA.CARDIOVASCULAR],
  ["Sin suficiente comida te faltará energía para trabajar y entrenar.",
    CONSECUENCIA_ALERTA.ENERGIA_BAJA],
  ["Conviene limitar exposiciones adicionales y avisar al equipo médico.",
    CONSECUENCIA_ALERTA.DOSIS_ACUMULADA],
  ["Hay que reducir la exposición cuanto antes.", CONSECUENCIA_ALERTA.RADIACION],
  ["Con poco sueño baja la atención y es más fácil cometer errores.",
    CONSECUENCIA_ALERTA.SUENO_BAJO],
  ["Un ánimo bajo sostenido quita energía y afecta la convivencia con el equipo.",
    CONSECUENCIA_ALERTA.ANIMO_BAJO],
  ["El estrés alto sostenido cansa, quita sueño y dificulta concentrarse.",
    CONSECUENCIA_ALERTA.ESTRES_ALTO],
  ["Sin gravedad, los músculos y los huesos se debilitan si no se ejercitan.",
    CONSECUENCIA_ALERTA.EJERCICIO_BAJO],
  ["Un pulso en reposo alto indica que tu cuerpo está bajo carga.", CONSECUENCIA_ALERTA.FC_ALTA],
  ["Es señal de que tu cuerpo no se está recuperando bien.", CONSECUENCIA_ALERTA.HRV_BAJA],
  ["Con poco oxígeno en la sangre puedes sentir cansancio, mareo o confusión.",
    CONSECUENCIA_ALERTA.SPO2_BAJA],
  ["Una temperatura elevada indica que tu cuerpo está reaccionando a algo.",
    CONSECUENCIA_ALERTA.TEMPERATURA_ALTA],
  ["Comer poco te deja sin energía para trabajar y entrenar.", CONSECUENCIA_ALERTA.INGESTA_BAJA],
  ["Conviene reducir el tiempo de exposición.", CONSECUENCIA_ALERTA.TASA_DOSIS_ALTA],
  ["Las reglas no ven riesgo todavía, pero conviene vigilarlo.",
    "The rules do not see risk yet, but it is worth watching."],
];

const CLAUSULAS = [
  [/^dormiste ([\d.]+) h \(tu normal son ([\d.]+) h\)$/i,
    "You slept $1 h (your normal is $2 h)"],
  [/^llevas (\d+) d[ií]as durmiendo menos de lo normal \(anoche ([\d.]+) h\)$/i,
    "You have slept below normal for $1 days (last night $2 h)"],
  [/^tu estr[eé]s est[aá] alto \((\d+) de 100\)$/i, "Your stress is high ($1 of 100)"],
  [/^entrenaste m[aá]s de lo planeado \((\d+) min\)$/i,
    "You trained more than planned ($1 min)"],
  [/^adem[aá]s tu [aá]nimo baj[oó] a (\d+) de 5$/i, "your mood also dropped to $1 of 5"],
  [/^tu [aá]nimo lleva (\d+) d[ií]as bajando$/i, "Your mood has been dropping for $1 days"],
  [/^el equipo reporta poca uni[oó]n \(([\d.]+) de 5\)$/i,
    "The team reports low cohesion ($1 of 5)"],
  [/^llevas (\d+) d[ií]as con menos de la mitad del ejercicio planeado$/i,
    "You have done less than half the planned exercise for $1 days"],
  [/^hay una tormenta solar en curso$/i, "A solar storm is underway"],
  [/^la radiaci[oó]n que llega ahora es de (\d+) µSv\/h, m[aá]s alta de lo habitual$/i,
    "The radiation arriving now is $1 µSv/h, higher than usual"],
  [/^la radiaci[oó]n que llega ahora es de (\d+) µSv\/h$/i,
    "The radiation arriving now is $1 µSv/h"],
  [/^tu pulso en reposo est[aá] elevado \((\d+)\)$/i, "Your resting pulse is elevated ($1)"],
  [/^tu temperatura est[aá] elevada \(([\d.]+) °C\)$/i, "Your temperature is elevated ($1 °C)"],
  [/^tu temperatura est[aá] en ([\d.]+) °C$/i, "Your temperature is $1 °C"],
  [/^comiste el (\d+) % de lo planeado$/i, "You ate $1 % of what was planned"],
  [/^ya acumulas (\d+) mSv de radiaci[oó]n en esta misi[oó]n$/i,
    "You have accumulated $1 mSv of radiation this mission"],
  [/^tu [aá]nimo est[aá] bajo \((\d) de 5\)$/i, "Your mood is low ($1 of 5)"],
  [/^hiciste (\d+) min de ejercicio de los (\d+) planeados$/i,
    "You did $1 min of the $2 planned"],
  [/^tu pulso en reposo est[aá] en (\d+) \(tu normal es (\d+)\)$/i,
    "Your resting pulse is $1 (your normal is $2)"],
  [/^la variabilidad de tu pulso est[aá] baja \(([\d.]+), tu normal es ([\d.]+)\)$/i,
    "Your heart-rate variability is low ($1, your normal is $2)"],
  [/^tu oxigenaci[oó]n est[aá] en (\d+) %$/i, "Your oxygen level is $1 %"],
  [/^ya son (\d+) d[ií]as seguidos$/i, "for $1 days in a row"],
  // Early-warning phrases (specialist sees risk where the rules see none).
  [/^dormiste poco anoche$/i, "You slept little last night"],
  [/^tu estr[eé]s est[aá] alto$/i, "Your stress is high"],
  [/^la variabilidad de tu pulso baj[oó]$/i, "Your heart-rate variability dropped"],
  [/^llevas varios d[ií]as durmiendo poco$/i, "You have slept little for several days"],
  [/^tu reloj interno est[aá] desajustado \(16 amaneceres al d[ií]a en [oó]rbita\)$/i,
    "Your body clock is out of sync (16 sunrises a day in orbit)"],
  [/^tu pulso en reposo est[aá] m[aá]s alto que tu normal$/i,
    "Your resting pulse is higher than your normal"],
  [/^la radiaci[oó]n que llega ahora es m[aá]s alta de lo normal$/i,
    "The radiation arriving now is higher than usual"],
  [/^tu oxigenaci[oó]n est[aá] baja$/i, "Your oxygen level is low"],
  [/^tu [aá]nimo est[aá] bajo$/i, "Your mood is low"],
  [/^comiste menos de lo planeado$/i, "You ate less than planned"],
  [/^entrenaste menos de lo planeado$/i, "You trained less than planned"],
  [/^tus reflejos est[aá]n m[aá]s lentos$/i, "Your reflexes are slower"],
  [/^tu presi[oó]n est[aá] alta$/i, "Your blood pressure is high"],
  [/^tu cuerpo a[uú]n se adapta: en microgravedad los l[ií]quidos suben hacia el pecho y la cabeza$/i,
    "Your body is still adapting: in microgravity fluids shift toward your chest and head"],
  [/^tu radiaci[oó]n acumulada es baja$/i, "Your accumulated radiation is low"],
  [/^tu oxigenaci[oó]n es buena$/i, "Your oxygen level is good"],
  [/^tu pulso est[aá] m[aá]s alto que tu normal$/i, "Your pulse is higher than your normal"],
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
export function unir(frases) {
  const limpias = frases.filter(Boolean);
  if (!limpias.length) return "";
  if (limpias.length === 1) return limpias[0];
  return limpias.slice(0, -1).join(", ") + " and " + limpias[limpias.length - 1];
}

export function palabraRiesgo(nivel) {
  return PALABRA_RIESGO[nivel] || "unknown";
}

export function nombreIndicador(clave) {
  return (INDICADORES[clave] && INDICADORES[clave].nombre) || clave;
}

export function unidadIndicador(clave) {
  return (INDICADORES[clave] && INDICADORES[clave].unidad) || "";
}

export function tituloAlerta(alerta) {
  const id = typeof alerta === "string" ? alerta : alerta && alerta.id;
  if (ALERTAS[id]) return ALERTAS[id];
  if (id && id.startsWith("SENAL_")) {
    const clave = id.slice(6).toLowerCase().replace(/_/g, "-");
    const nombre = NOMBRES_ESPECIALISTA[clave];
    return nombre ? `Early signal: ${nombre.toLowerCase()}` : "Early signal";
  }
  return id || "Alert";
}

export function tituloProtocolo(id) {
  return (PROTOCOLOS[id] && PROTOCOLOS[id].titulo) || "Protocol";
}

export function traducirPaso(texto) {
  return PASO_ES_A_EN.get(texto) || null;
}

export function pasoProtocolo(idProtocolo, paso) {
  const protocolo = PROTOCOLOS[idProtocolo];
  return (protocolo && protocolo.pasos[paso.id]) || traducirPaso(paso.texto) || "Complete this step.";
}

export function traducirMotivo(texto) {
  if (!texto) return "";
  return String(texto).split("; ").map((parte) => MOTIVOS[parte] || "a rule signal").join("; ");
}

export function notaDia(texto) {
  return (texto && NOTAS[texto]) || "";
}

export function traducirNombre(nombre) {
  return String(nombre || "").replace(/^Cdte\.\s*/i, "Cmdr. ");
}

function dividirClausulas(texto) {
  const partes = [];
  let actual = "";
  let profundidad = 0;
  for (let i = 0; i < texto.length; i += 1) {
    const caracter = texto[i];
    if (caracter === "(") profundidad += 1;
    if (caracter === ")") profundidad = Math.max(0, profundidad - 1);
    if (profundidad === 0 && caracter === ",") {
      partes.push(actual);
      actual = "";
      continue;
    }
    if (profundidad === 0 && texto.slice(i, i + 3) === " y ") {
      partes.push(actual);
      actual = "";
      i += 2;
      continue;
    }
    actual += caracter;
  }
  partes.push(actual);
  return partes.map((parte) => parte.trim().replace(/\.$/, "")).filter(Boolean);
}

function traducirClausula(clausula) {
  for (const [patron, ingles] of CLAUSULAS) {
    if (patron.test(clausula)) return clausula.replace(patron, ingles);
  }
  return null;
}

/** Translates a Spanish "causa_en_lenguaje_simple" into English. */
export function traducirCausa(texto, idAlerta) {
  if (!texto) return "";
  let resto = String(texto).trim();
  const cierre = "Sigue este protocolo.";
  if (resto.endsWith(cierre)) resto = resto.slice(0, -cierre.length).trim();

  let consecuencia = "";
  for (const [espanol, ingles] of CONSECUENCIAS) {
    if (resto.endsWith(espanol)) {
      consecuencia = ingles;
      resto = resto.slice(0, -espanol.length).trim();
      break;
    }
  }
  resto = resto.replace(/\.\s*$/, "").trim();

  const partes = dividirClausulas(resto);
  const traducidas = partes.map(traducirClausula);
  if (!traducidas.length || traducidas.some((parte) => !parte)) {
    const generica = CONSECUENCIA_ALERTA[idAlerta] || "Follow this protocol.";
    return traducirCausaGenerica(generica);
  }

  const frases = traducidas.map((parte, i) =>
    (i === 0 ? parte : parte.charAt(0).toLowerCase() + parte.slice(1)));
  let salida = unir(frases) + ".";
  if (!consecuencia) consecuencia = CONSECUENCIA_ALERTA[idAlerta] || "";
  if (consecuencia) salida += " " + consecuencia;
  salida += " Follow this protocol.";
  return salida.charAt(0).toUpperCase() + salida.slice(1);
}

function traducirCausaGenerica(consecuencia) {
  const texto = consecuencia.endsWith(".") ? consecuencia : consecuencia + ".";
  return `${texto} Follow this protocol.`;
}

/** Rebuilds the global one-line summary in English from structured data. */
export function explicacionGlobal(resultado) {
  const alertas = resultado.alertas || [];
  let texto;
  if (!alertas.length) {
    texto = "All clear. Your indicators are within your normal range.";
    if (resultado.ventana_adaptacion) {
      texto += " You are in the first days of adaptation: it is normal for some values to move.";
    }
  } else {
    texto = `${tituloAlerta(alertas[0])}.`;
    const otras = alertas.length - 1;
    if (otras === 1) texto += " There is 1 more alert.";
    else if (otras > 1) texto += ` There are ${otras} more alerts.`;
  }
  if (resultado.modo === "degradado") {
    texto += " Part of the board is unavailable; I keep watching with the rules.";
  }
  return texto;
}

/** Rebuilds "the board says ..." from the specialists' answers. */
export function opinionJunta(alerta, resultado) {
  const junta = resultado.junta || [];
  const partes = (alerta.especialistas_consultados || []).map((nombre) => {
    const miembro = junta.find((m) => m.especialista === nombre && m.respuesta);
    if (!miembro) return null;
    const titulo = (NOMBRES_ESPECIALISTA[nombre] || nombre).toLowerCase();
    return `${titulo} sees ${palabraRiesgo(miembro.respuesta.nivel)} risk`;
  }).filter(Boolean);
  if (!partes.length) return "";
  return `The board says: ${unir(partes)}.`;
}

/** Rebuilds a specialist's short explanation in English. */
export function explicacionCorta(respuesta) {
  const riesgo = palabraRiesgo(respuesta.nivel);
  let texto = `${riesgo.charAt(0).toUpperCase()}${riesgo.slice(1)} risk of ${RIESGO[respuesta.especialista] || "a health problem"}.`;
  const suben = (respuesta.factores || [])
    .filter((f) => f.aporte > 0.05)
    .slice(0, 2)
    .map((f) => ETIQUETAS[f.indicador] || "a personal factor");
  if (suben.length && respuesta.nivel !== "verde") {
    texto += ` Main drivers: ${unir(suben)}.`;
  }
  if ((respuesta.datos_faltantes || []).length) {
    texto += " Some data is missing, so the estimate is less certain.";
  }
  return texto;
}

// ---------------------------------------------------------------------------
// Backend validation errors (they arrive as plain Spanish sentences)
// ---------------------------------------------------------------------------
const ERRORES_EXACTOS = {
  "El ánimo va de 1 a 5.": "Mood goes from 1 to 5.",
  "La prueba necesita al menos 3 reacciones válidas.":
    "The test needs at least 3 valid reactions.",
  "Responde las 3 preguntas con un valor de 1 a 5.":
    "Answer all 3 questions with a value from 1 to 5.",
  "No se recibió ningún indicador.": "No indicator was received.",
  "No se pudo avisar al orquestador (Laptop 3): no responde.":
    "Could not reach the orchestrator (Laptop 3): it is not responding.",
  "Faltan alerta_id o paso_id.": "Missing alerta_id or paso_id.",
};

// Spanish indicator names that the backend embeds in validation messages.
const NOMBRES_BACKEND = {
  "Sueño": "Sleep",
  "Ánimo": "Mood",
  "Estrés": "Stress",
  "Ejercicio": "Exercise",
  "Pulso en reposo": "Resting pulse",
  "Variabilidad del pulso": "Heart-rate variability",
  "Oxigenación": "Oxygen level",
  "Temperatura": "Temperature",
  "Comida": "Food",
  "Radiación ahora": "Radiation now",
  "Radiación acumulada": "Radiation accumulated",
  "Cohesión del equipo": "Team cohesion",
  "Tiempo de reacción": "Reaction time",
  "Desfase del reloj interno": "Body-clock offset",
  "Luz brillante": "Bright light",
  "Presión sistólica": "Systolic pressure",
  "Presión diastólica": "Diastolic pressure",
  "Glucosa": "Glucose",
};

function nombreBackend(nombre) {
  return NOMBRES_BACKEND[nombre] || "This indicator";
}

const ERRORES_REGEX = [
  [/^'(.+)' no es un indicador conocido\.$/, (_, clave) => `'${clave}' is not a known indicator.`],
  [/^(.+) no se ingresa a mano\.$/, (_, nombre) => `${nombreBackend(nombre)} cannot be entered by hand.`],
  [/^(.+): el valor debe ser un número\.$/, (_, nombre) => `${nombreBackend(nombre)}: the value must be a number.`],
  [/^(.+): debe estar entre ([\d.]+) y ([\d.]+) (.+)\.$/,
    (_, nombre, minimo, maximo, unidad) =>
      `${nombreBackend(nombre)}: must be between ${minimo} and ${maximo} ${unidad}.`],
  [/^El día de misión va de 1 a (\d+)\.$/, (_, dias) => `Mission day goes from 1 to ${dias}.`],
];

export function traducirError(texto) {
  if (!texto) return "The server rejected the data. Please check the values.";
  const limpio = String(texto).trim();
  if (ERRORES_EXACTOS[limpio]) return ERRORES_EXACTOS[limpio];
  for (const [patron, reemplazo] of ERRORES_REGEX) {
    if (patron.test(limpio)) return limpio.replace(patron, reemplazo);
  }
  return "The server rejected the data. Please check the values.";
}
