// ============================================================
// CONTENIDO DE DEMOSTRACIÓN
// Mientras el backend (RAG + agentes) no esté listo, la app usa
// estos datos. Tienen la misma forma que el JSON de salida del reto.
// ============================================================

export const DIAGNOSTICO = [
  {
    pregunta: '¿Qué describe mejor la "estructura" de un documento XML?',
    opciones: [
      'La forma en que se organizan y jerarquizan los datos dentro del archivo.',
      'El lenguaje de programación usado para crear aplicaciones web.',
      'Un tipo de base de datos relacional.',
      'Un formato de compresión de archivos.',
    ],
    correcta: 0,
  },
  {
    pregunta: '¿Qué elemento contiene a todos los demás en un XML?',
    opciones: ['El elemento raíz', 'Un atributo', 'La declaración de versión', 'Un comentario'],
    correcta: 0,
  },
  {
    pregunta: '¿Para qué sirve un esquema XSD?',
    opciones: ['Para dar estilo visual', 'Para validar la estructura del documento', 'Para comprimir el archivo', 'Para traducirlo'],
    correcta: 1,
  },
  {
    pregunta: '¿Qué es un atributo en XML?',
    opciones: ['Un dato extra dentro de la etiqueta de apertura', 'Un archivo adjunto', 'Una base de datos', 'Un error de sintaxis'],
    correcta: 0,
  },
  {
    pregunta: '¿Cuál es una buena práctica al nombrar elementos?',
    opciones: ['Usar nombres aleatorios', 'Usar nombres descriptivos', 'Usar solo números', 'Repetir el mismo nombre siempre'],
    correcta: 1,
  },
];



export const AGENTES = [
  { nombre: 'Agente de análisis', descripcion: 'Lee y comprende la estructura del documento.', icono: 'FileSearch' },
  { nombre: 'Agente de adaptación', descripcion: 'Ajusta el contenido a tu nivel y a tu mundo.', icono: 'Brain' },
    { nombre: 'Agente de generación', descripcion: 'Crea tu material en el formato que elegiste.', icono: 'Layers' },
];
