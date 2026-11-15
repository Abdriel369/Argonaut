// Body-map texts: what affects each zone in space and what to do about it.
// Plain language, no jargon and no medication doses.

export const ZONAS = [
  {
    id: "cabeza",
    nombre: "Head: sleep, mood and stress",
    corto: "Head",
    indicadores: ["sueno_h", "animo", "estres"],
    alertas: ["FATIGA", "AISLAMIENTO", "SUENO_BAJO", "ESTRES_ALTO", "ANIMO_BAJO"],
    causa: "In orbit you see about 16 sunrises a day, and that confuses your body clock. " +
      "Being confined, the workload and being far from home raise stress and lower mood.",
    hacer: "Keep a fixed sleep schedule, get bright light at the start of your day and talk to your crew about how you feel.",
  },
  {
    id: "corazon",
    nombre: "Heart",
    corto: "Heart",
    indicadores: ["fc_reposo", "hrv"],
    alertas: ["CARDIOVASCULAR", "FC_ALTA", "HRV_BAJA"],
    causa: "Without gravity, body fluids shift toward your chest and head, and your heart works differently. " +
      "Tiredness and stress also speed up your resting pulse.",
    hacer: "Rest, drink water and measure again. Stick to your exercise plan: it keeps your heart fit.",
  },
  {
    id: "pulmones",
    nombre: "Lungs: oxygenation",
    corto: "Lungs",
    indicadores: ["spo2"],
    alertas: ["SPO2_BAJA"],
    causa: "The station's air is recycled. If ventilation fails in a corner of the module, " +
      "used air stays around you and your oxygen level can drop.",
    hacer: "If it drops, reposition the sensor, breathe deeply, move somewhere else and ask for the module's air to be checked.",
  },
  {
    id: "musculo",
    nombre: "Muscles and bones: legs and spine",
    corto: "Muscles and bones",
    indicadores: ["ejercicio_min"],
    alertas: ["PERDIDA_MUSCULAR_OSEA", "EJERCICIO_BAJO"],
    estimado: true,
    causa: "Without gravity, your legs and spine stop carrying your weight. " +
      "Muscles shrink and bones lose minerals if they are not exercised.",
    hacer: "Keep up your daily exercise, especially strength work for legs and back.",
  },
  {
    id: "radiacion",
    nombre: "Whole body: radiation",
    corto: "Radiation",
    indicadores: ["tasa_dosis_usv_h"],
    alertas: ["RADIACION", "TASA_DOSIS_ALTA", "DOSIS_ACUMULADA"],
    causa: "Outside the atmosphere and Earth's magnetic field, more radiation reaches you. " +
      "During a solar storm it can rise a lot in a few hours.",
    hacer: "If there is a solar storm, go to the station shelter and cancel any trips outside.",
  },
];

export const INMUNE = {
  titulo: "Immune system: future work",
  texto: "Monitoring the immune system needs blood, saliva and urine samples. This prototype does not measure or simulate it.",
};

export const PREGUNTAS_EQUIPO = [
  { clave: "comunicacion", texto: "How well did the team communicate this week?" },
  { clave: "conflictos", texto: "How well were disagreements resolved?" },
  { clave: "carga", texto: "How manageable was the workload?" },
];

export const ANIMOS = ["Very low", "Low", "Okay", "Good", "Very good"];
