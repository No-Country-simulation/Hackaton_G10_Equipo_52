// ============================================================
// SERVICIO DE API
//
// CONTRATO CON EL BACKEND
//   1) POST /adaptar  (multipart/form-data)
//        archivos[]            uno o varios PDF / Markdown / texto (misma clave repetida)
//        perfil_destinatario   Principiante | Intermedio | Avanzado | Ejecutivo
//        formato_salida        Resumen | Flashcards | Quiz | Tutorial
//        nicho_sector          Educacion | Salud | Finanzas | ... | General (sin tildes)
//        nivel_detalle         Didactico | Profundo
//        session_id            id anónimo de la sesión
//      → 202 { "job_id": "..." }
//   2) GET /adaptar/{job_id}   (se consulta cada 2 s)
//      → { "estado": "procesando" | "listo" | "error",
//          "etapa": 1 | 2 | 3,            // etapa real de los agentes
//          "mensaje": "...",              // si estado = error
//          "resultado": { ... } }         // si estado = listo (ver resultadoDemo.js)
//   Errores HTTP: se muestra "detail" o "mensaje" del cuerpo JSON si existe.
//
// MODO DEMO: se controla con VITE_USE_DEMO=true | false. Si no se define,
//   está activado en desarrollo (npm run dev) y desactivado en el build.
// URL DEL BACKEND: VITE_API_URL (en desarrollo, por defecto http://localhost:8000;
//   en producción es obligatoria, puede ir vacía = mismo origen).
// ============================================================
import { resultadoDemo } from '../data/resultadoDemo';

const DEMO_FORZADO = import.meta.env.VITE_USE_DEMO;
const USAR_DEMO = DEMO_FORZADO ? DEMO_FORZADO === 'true' : import.meta.env.DEV;

const URL_CONFIGURADA = import.meta.env.VITE_API_URL; // undefined si no se definió
const URL_API = (URL_CONFIGURADA ?? (import.meta.env.DEV ? 'http://localhost:8000' : '')).replace(/\/$/, '');

const PAUSA_MS = 2000; // cada cuánto se consulta el estado de la tarea
const LIMITE_MS = 10 * 60 * 1000; // tiempo máximo total de procesamiento

const MENSAJES = {
  413: 'El archivo es demasiado grande.',
  415: 'Ese formato de archivo no está soportado.',
  422: 'No pudimos leer el contenido de tu documento.',
  429: 'Hay muchas solicitudes en este momento. Espera unos segundos e intenta de nuevo.',
};

class ErrorApi extends Error {}

const sinTildes = (texto) => String(texto).normalize('NFD').replace(/[\u0300-\u036f]/g, '');

// Id anónimo de la sesión (dura mientras la pestaña esté abierta)
function idSesion() {
  try {
    let id = sessionStorage.getItem('krystal_sesion');
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem('krystal_sesion', id);
    }
    return id;
  } catch {
    return 'anonima';
  }
}

// Espera cancelable: si se aborta la señal, termina con AbortError
function esperar(ms, senal) {
  return new Promise((resolver, rechazar) => {
    const cancelado = () => new DOMException('Cancelado', 'AbortError');
    if (senal?.aborted) return rechazar(cancelado());
    const timer = setTimeout(resolver, ms);
    senal?.addEventListener(
      'abort',
      () => {
        clearTimeout(timer);
        rechazar(cancelado());
      },
      { once: true },
    );
  });
}

// Petición con timeout, cancelación y mensajes de error en español
async function pedir(ruta, opciones = {}, { senal, timeoutMs = 30000 } = {}) {
  const control = new AbortController();
  const cancelar = () => control.abort();
  senal?.addEventListener('abort', cancelar);
  const timer = setTimeout(cancelar, timeoutMs);
  try {
    const res = await fetch(`${URL_API}${ruta}`, { ...opciones, signal: control.signal });
    if (!res.ok) {
      const cuerpo = await res.json().catch(() => ({}));
      const detalle = typeof cuerpo.detail === 'string' ? cuerpo.detail : cuerpo.mensaje;
      throw new ErrorApi(detalle || MENSAJES[res.status] || 'Ocurrió un error inesperado. Intenta de nuevo.');
    }
    return await res.json();
  } catch (e) {
    if (e instanceof ErrorApi || senal?.aborted) throw e;
    if (e.name === 'AbortError') throw new ErrorApi('El servidor tardó demasiado en responder. Intenta de nuevo.');
    throw new ErrorApi('No pudimos conectar con el servidor. Revisa tu conexión e intenta de nuevo.');
  } finally {
    clearTimeout(timer);
    senal?.removeEventListener('abort', cancelar);
  }
}

// Evita que un material mal formado rompa la pantalla de estudio
function validarResultado(resultado) {
  const items = resultado?.contenido_adaptado?.items;
  if (!Array.isArray(items) || !items.length) {
    throw new ErrorApi('El servidor devolvió un material incompleto. Intenta de nuevo.');
  }
  return resultado;
}

async function simularProceso(archivos, perfil, { senal, alCambiarEtapa }) {
  for (const etapa of [1, 2, 3]) {
    alCambiarEtapa?.(etapa);
    await esperar(1200, senal);
  }
  // Para probar el manejo de errores: sube un archivo con "error" en el nombre
  if (archivos.some((a) => a.name.toLowerCase().includes('error'))) {
    throw new ErrorApi('Error simulado: el nombre del archivo contiene "error".');
  }
  return resultadoDemo(perfil.formato_salida);
}

/**
 * Envía los documentos y el perfil al backend y espera el material.
 * @param {File[]} archivos
 * @param {object} perfil  { perfil_destinatario, formato_salida, nicho_sector, nivel_detalle }
 * @param {object} opciones  { senal: AbortSignal, alCambiarEtapa: (1|2|3) => void }
 */
export async function procesarDocumento(archivos, perfil, { senal, alCambiarEtapa } = {}) {
  if (USAR_DEMO) return simularProceso(archivos, perfil, { senal, alCambiarEtapa });

  // En producción no se adivina la URL: si falta, se avisa en vez de llamar a localhost
  if (URL_CONFIGURADA === undefined && !import.meta.env.DEV) {
    console.error('Falta definir VITE_API_URL (ver .env.example).');
    throw new ErrorApi('La aplicación no está conectada a un servidor. Avisa al equipo.');
  }

  const datos = new FormData();
  archivos.forEach((archivo) => datos.append('archivos', archivo));
  Object.entries(perfil).forEach(([clave, valor]) => datos.append(clave, sinTildes(valor)));
  datos.append('session_id', idSesion());

  // 1) Crear la tarea (la subida puede tardar más que una consulta normal)
  const { job_id: idTarea } = await pedir('/adaptar', { method: 'POST', body: datos }, { senal, timeoutMs: 180000 });
  if (!idTarea) throw new ErrorApi('El servidor respondió algo inesperado. Intenta de nuevo.');

  // 2) Consultar el estado hasta que termine
  const inicio = Date.now();
  while (true) {
    await esperar(PAUSA_MS, senal);
    if (Date.now() - inicio > LIMITE_MS) throw new ErrorApi('El procesamiento está tardando demasiado. Intenta de nuevo.');
    const tarea = await pedir(`/adaptar/${encodeURIComponent(idTarea)}`, {}, { senal });
    if (Number.isFinite(tarea.etapa)) alCambiarEtapa?.(Math.min(Math.max(tarea.etapa, 1), 3));
    if (tarea.estado === 'listo') return validarResultado(tarea.resultado);
    if (tarea.estado === 'error') throw new ErrorApi(tarea.mensaje || 'No pudimos procesar tu documento. Intenta de nuevo.');
  }
}