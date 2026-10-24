// ============================================================
// RESULTADO DE DEMOSTRACIÓN (modo demo)
// Tiene la misma forma que el JSON que debe devolver el backend:
//   metadatos, contenido_adaptado.items, evaluacion_calidad, almacenamiento_oci, diagnostico.
// Según el formato, cada item tiene estos campos:
//   Resumen y Tutorial → { titulo_paso, texto, fuentes }
//   Flashcards         → { frente, dorso, pista_didactica, fuentes }
//   Quiz               → { pregunta, opciones, respuesta_correcta (índice), justificacion, fuentes }
// ============================================================
import { DIAGNOSTICO } from './contenidoDemo';

const ITEMS = {
  Resumen: [
    { titulo_paso: 'Qué es XML', texto: 'Es un estándar para intercambiar datos entre sistemas.', fuentes: ['chunk_000'] },
    { titulo_paso: 'Cómo se organiza', texto: 'Con una estructura jerárquica de elementos y un elemento raíz.', fuentes: ['chunk_001'] },
    { titulo_paso: 'Cómo se valida', texto: 'Mediante esquemas (XSD) que definen qué estructura es válida.', fuentes: ['chunk_002'] },
  ],
  Tutorial: [
    { titulo_paso: 'Declara la versión', texto: 'Empieza el archivo con la declaración de versión y codificación.', fuentes: ['chunk_000'] },
    { titulo_paso: 'Crea el elemento raíz', texto: 'Todos los demás elementos van dentro de un único elemento raíz.', fuentes: ['chunk_001'] },
    { titulo_paso: 'Valida tu documento', texto: 'Compáralo con un esquema XSD antes de usarlo en producción.', fuentes: ['chunk_002'] },
  ],
  Flashcards: [
    { frente: '¿Qué es XML?', dorso: 'Un estándar para intercambiar datos entre sistemas.', pista_didactica: 'Piensa en un idioma común entre programas.', fuentes: ['chunk_000'] },
    { frente: '¿Qué es el elemento raíz?', dorso: 'El elemento que contiene a todos los demás.', pista_didactica: 'Es el tronco del árbol.', fuentes: ['chunk_001'] },
    { frente: '¿Para qué sirve un XSD?', dorso: 'Para validar que el documento tenga la estructura correcta.', pista_didactica: 'Es el molde del documento.', fuentes: ['chunk_002'] },
  ],
  Quiz: [
    { pregunta: '¿Qué contiene a todos los demás elementos?', opciones: ['El elemento raíz', 'Un atributo', 'Un comentario', 'La declaración'], respuesta_correcta: 0, justificacion: 'El elemento raíz es el único de primer nivel y contiene al resto.', fuentes: ['chunk_001'] },
    { pregunta: '¿Para qué sirve un esquema XSD?', opciones: ['Comprimir archivos', 'Validar la estructura', 'Crear bases de datos', 'Programar páginas'], respuesta_correcta: 1, justificacion: 'Un XSD define qué estructura es válida y permite comprobarla.', fuentes: ['chunk_002'] },
    { pregunta: '¿Cómo se organizan los datos en XML?', opciones: ['En tablas', 'De forma jerárquica', 'Sin orden', 'En binario'], respuesta_correcta: 1, justificacion: 'Los elementos se anidan formando una jerarquía.', fuentes: ['chunk_001'] },
  ],
};

export function resultadoDemo(formato = 'Resumen') {
  const f = ITEMS[formato] ? formato : 'Resumen';
  return {
    status: 'exito',
    doc_id: 'demo',
    metadatos: {
      perfil_aplicado: 'Principiante',
      formato_generado: f,
      nicho_sector: 'General',
      tiempo_estimado_estudio_minutos: 5,
      conceptos_clave: ['XML', 'Elemento raíz', 'XSD'],
      prerrequisitos: ['Nociones básicas de datos'],
    },
    contenido_adaptado: {
      titulo: 'XML desde cero',
      introduccion_contextualizada: 'Imagina XML como un formulario con campos bien ordenados que cualquier programa puede leer.',
      items: ITEMS[f],
    },
    evaluacion_calidad: { anclaje_fuente_score: 0.96, claridad_pedagogica: 'Alta', observaciones: 'Datos de demostración.' },
    almacenamiento_oci: { bucket: 'krystal-contenidos-educativos', objeto_id: `demo-${f.toLowerCase()}.json`, status_upload: 'simulado' },
    diagnostico: { preguntas: DIAGNOSTICO },
  };
}