// Textos del mapa corporal: qué afecta a cada zona en el espacio y qué hacer.
// Lenguaje sencillo, sin jerga y sin dosis de medicamentos.

export const ZONAS = [
  {
    id: "cabeza",
    nombre: "Cabeza: sueño, ánimo y estrés",
    corto: "Cabeza",
    indicadores: ["sueno_h", "animo", "estres"],
    alertas: ["FATIGA", "AISLAMIENTO", "SUENO_BAJO", "ESTRES_ALTO", "ANIMO_BAJO"],
    causa: "En órbita ves unos 16 amaneceres al día y eso confunde a tu reloj interno. " +
      "El encierro, la carga de trabajo y estar lejos de casa suben el estrés y bajan el ánimo.",
    hacer: "Mantén un horario fijo de sueño, busca luz brillante al empezar tu día y habla con tu equipo de cómo te sientes.",
  },
  {
    id: "corazon",
    nombre: "Corazón",
    corto: "Corazón",
    indicadores: ["fc_reposo", "hrv"],
    alertas: ["CARDIOVASCULAR", "FC_ALTA", "HRV_BAJA"],
    causa: "Sin gravedad, los líquidos del cuerpo suben hacia el pecho y la cabeza, y el corazón trabaja de otra forma. " +
      "El cansancio y el estrés también aceleran el pulso en reposo.",
    hacer: "Descansa, bebe agua y vuelve a medir. Cumple tu plan de ejercicio: mantiene al corazón en forma.",
  },
  {
    id: "pulmones",
    nombre: "Pulmones: oxigenación",
    corto: "Pulmones",
    indicadores: ["spo2"],
    alertas: ["SPO2_BAJA"],
    causa: "El aire de la estación se recicla. Si la ventilación falla en un rincón del módulo, " +
      "el aire usado se queda alrededor de ti y tu oxigenación puede bajar.",
    hacer: "Si baja, recoloca el sensor, respira profundo, cambia de lugar y pide revisar el aire del módulo.",
  },
  {
    id: "musculo",
    nombre: "Músculos y huesos: piernas y columna",
    corto: "Músculos y huesos",
    indicadores: ["ejercicio_min"],
    alertas: ["PERDIDA_MUSCULAR_OSEA", "EJERCICIO_BAJO"],
    estimado: true,
    causa: "Sin gravedad, las piernas y la columna dejan de cargar tu peso. " +
      "Los músculos se achican y los huesos pierden minerales si no se ejercitan.",
    hacer: "Cumple tu ejercicio diario, sobre todo el de fuerza para piernas y espalda.",
  },
  {
    id: "radiacion",
    nombre: "Cuerpo completo: radiación",
    corto: "Radiación",
    indicadores: ["tasa_dosis_usv_h"],
    alertas: ["RADIACION", "TASA_DOSIS_ALTA", "DOSIS_ACUMULADA"],
    causa: "Fuera de la atmósfera y del campo magnético de la Tierra llega más radiación. " +
      "Durante una tormenta solar puede subir mucho en pocas horas.",
    hacer: "Si hay tormenta solar, ve al refugio de la estación y suspende las salidas al exterior.",
  },
];

export const INMUNE = {
  titulo: "Sistema inmune: línea futura",
  texto: "Vigilar las defensas requiere muestras de sangre, saliva y orina. Este prototipo no lo mide ni lo simula.",
};

export const PREGUNTAS_EQUIPO = [
  { clave: "comunicacion", texto: "¿Qué tan bien se comunicó el equipo esta semana?" },
  { clave: "conflictos", texto: "¿Qué tan bien se resolvieron los desacuerdos?" },
  { clave: "carga", texto: "¿Qué tan manejable fue la carga de trabajo?" },
];

export const ANIMOS = ["Muy bajo", "Bajo", "Regular", "Bien", "Muy bien"];
