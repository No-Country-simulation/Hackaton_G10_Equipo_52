export function validarPreguntas(lista) {
  if (!Array.isArray(lista)) return [];
  return lista
    .filter(
      (q) =>
        q &&
        typeof q.pregunta === 'string' &&
        q.pregunta.trim() &&
        Array.isArray(q.opciones) &&
        q.opciones.length >= 2 &&
        q.opciones.every((o) => typeof o === 'string' && o.trim()) &&
        Number.isInteger(q.correcta) &&
        q.correcta >= 0 &&
        q.correcta < q.opciones.length,
    )
    .map((q) => ({
      pregunta: q.pregunta.trim(),
      opciones: q.opciones.map((o) => o.trim()),
      correcta: q.correcta,
    }));
}

/** Nivel de conocimiento según el porcentaje de aciertos. */
export function calcularNivel(respuestas, preguntas) {
  if (!preguntas.length) return 'Principiante';
  const aciertos = preguntas.filter((q, i) => respuestas[i] === q.correcta).length;
  const proporcion = aciertos / preguntas.length;
  return proporcion < 0.4 ? 'Principiante' : proporcion < 0.75 ? 'Intermedio' : 'Avanzado';
}

/** { aciertos, total, nivel } para mostrar en la pantalla de estudio. */
export function resumenDiagnostico(respuestas, preguntas) {
  const aciertos = preguntas.filter((q, i) => respuestas[i] === q.correcta).length;
  return { aciertos, total: preguntas.length, nivel: calcularNivel(respuestas, preguntas) };
}