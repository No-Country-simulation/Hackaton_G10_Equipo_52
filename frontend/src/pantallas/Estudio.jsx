import { useState } from 'react';
import { useSesion } from '../context/SesionContext';
import { PREGUNTAS, opcionElegida } from '../data/preguntas';
import MigaDePan from '../components/layout/MigaDePan';
import Boton from '../components/ui/Boton';
import Dialogo from '../components/ui/Dialogo';
import Icono from '../components/ui/Icono';
import Insignia from '../components/ui/Insignia';

const FORMATOS = {
  Resumen: { texto: 'Resumen ejecutivo', icono: 'FileText' },
  Tutorial: { texto: 'Guía paso a paso', icono: 'Wrench' },
  Flashcards: { texto: 'Flashcards', icono: 'Layers' },
  Quiz: { texto: 'Quiz', icono: 'CircleHelp' },
};

// Descarta los items que no tengan los campos que necesita cada formato
function itemsValidos(formato, items) {
  if (!Array.isArray(items)) return [];
  if (formato === 'Flashcards') return items.filter((i) => i?.frente && i?.dorso);
  if (formato === 'Quiz') return items.filter((i) => i?.pregunta && Array.isArray(i.opciones) && i.opciones.length > 1);
  return items.filter((i) => i?.titulo_paso || i?.texto);
}

// ---------- Contenido según el formato ----------
function Pasos({ contenido, metadatos, items }) {
  return (
    <section className="tarjeta resumen-ejecutivo">
      <div className="resumen-ejecutivo__encabezado">
        <span className="circulo-icono">
          <Icono nombre="FileText" />
        </span>
        <div>
          <h3>{contenido.titulo}</h3>
          {metadatos?.conceptos_clave?.length > 0 && <p>{metadatos.conceptos_clave.join(' · ')}</p>}
        </div>
        {metadatos?.tiempo_estimado_estudio_minutos && (
          <Insignia>{metadatos.tiempo_estimado_estudio_minutos} min de lectura</Insignia>
        )}
      </div>
      {contenido.introduccion_contextualizada && (
        <p className="recuerda">
          <Icono nombre="Lightbulb" />
          <span>{contenido.introduccion_contextualizada}</span>
        </p>
      )}
      {items.map((s, i) => (
        <div key={i} className="seccion-resumen">
          <span className="numero">{i + 1}</span>
          <div>
            <strong>{s.titulo_paso}</strong>
            <p>{s.texto}</p>
          </div>
        </div>
      ))}
    </section>
  );
}

function Flashcards({ tarjetas }) {
  const [i, setI] = useState(0);
  const [volteada, setVolteada] = useState(false);
  const t = tarjetas[i];
  const mover = (d) => {
    setVolteada(false);
    setI((i + d + tarjetas.length) % tarjetas.length);
  };
  return (
    <section className="pregunta">
      <button
        className={`flashcard ${volteada ? 'flashcard--dorso' : ''}`}
        onClick={() => setVolteada(!volteada)}
        aria-label={volteada ? 'Ver la pregunta' : 'Ver la respuesta'}
      >
        <small>
          {volteada ? 'Respuesta' : 'Pregunta'} {i + 1} de {tarjetas.length}
        </small>
        <h2>{volteada ? t.dorso : t.frente}</h2>
        {volteada ? (
          t.pista_didactica && <span className="flashcard__pista">💡 {t.pista_didactica}</span>
        ) : (
          <span className="ayuda-tecla" style={{ marginTop: 'auto' }}>
            Toca la tarjeta para ver la respuesta
          </span>
        )}
      </button>
      <div className="controles-flashcards">
        <Boton tipo="fantasma" iconoIzq="ArrowLeft" onClick={() => mover(-1)}>
          Anterior
        </Boton>
        <Boton iconoDer="ArrowRight" onClick={() => mover(1)}>
          Siguiente
        </Boton>
      </div>
    </section>
  );
}

function Quiz({ preguntas }) {
  const [n, setN] = useState(0);
  const [elegida, setElegida] = useState(null);
  const [aciertos, setAciertos] = useState(0);
  const [fin, setFin] = useState(false);
  const q = preguntas[n];

  const reiniciar = () => {
    setN(0);
    setElegida(null);
    setAciertos(0);
    setFin(false);
  };

  if (fin) {
    return (
      <section className="tarjeta pregunta">
        <h3>¡Terminaste el quiz!</h3>
        <p>
          Acertaste {aciertos} de {preguntas.length} preguntas.
        </p>
        <div className="pregunta__pie">
          <span style={{ flex: 1 }} />
          <Boton iconoIzq="RotateCcw" onClick={reiniciar}>
            Repetir quiz
          </Boton>
        </div>
      </section>
    );
  }

  const elegir = (i) => {
    setElegida(i);
    if (i === q.respuesta_correcta) setAciertos((a) => a + 1);
  };
  const siguiente = () => {
    if (n + 1 >= preguntas.length) return setFin(true);
    setN(n + 1);
    setElegida(null);
  };
  const claseDe = (i) => {
    if (elegida === null) return '';
    if (i === q.respuesta_correcta) return 'opcion-quiz--correcta';
    if (i === elegida) return 'opcion-quiz--incorrecta';
    return '';
  };

  return (
    <section className="tarjeta pregunta">
      <strong>
        Pregunta {n + 1} de {preguntas.length}
      </strong>
      <h3>{q.pregunta}</h3>
      {q.opciones.map((op, i) => (
        <button key={i} className={`opcion-quiz ${claseDe(i)}`} disabled={elegida !== null} onClick={() => elegir(i)}>
          <span className="opcion-quiz__radio" aria-hidden="true" />
          {op}
          {elegida !== null && i === q.respuesta_correcta && <span className="opcion-quiz__resultado">✓ Correcta</span>}
          {elegida === i && i !== q.respuesta_correcta && <span className="opcion-quiz__resultado">✕ Incorrecta</span>}
        </button>
      ))}
      {elegida !== null && q.justificacion && (
        <p className="recuerda">
          <Icono nombre="Lightbulb" />
          <span>{q.justificacion}</span>
        </p>
      )}
      <div className="pregunta__pie">
        <span style={{ flex: 1 }} />
        <Boton iconoDer="ArrowRight" disabled={elegida === null} onClick={siguiente}>
          {n + 1 >= preguntas.length ? 'Ver resultado' : 'Siguiente pregunta'}
        </Boton>
      </div>
    </section>
  );
}

// ---------- Pantalla ----------
function EstudioContenido({ datos }) {
  const { archivos, respuestas, diagnostico, reiniciar } = useSesion();
  const [nivel, estilo, mundo, prof] = PREGUNTAS.map((p) => opcionElegida(p, respuestas));
  const [confirmar, setConfirmar] = useState(false);

  const formato = datos.metadatos?.formato_generado ?? estilo?.valor ?? 'Resumen';
  const info = FORMATOS[formato] ?? FORMATOS.Resumen;
  const contenido = datos.contenido_adaptado ?? {};
  const items = itemsValidos(formato, contenido.items);
  const puntaje = Number(datos.evaluacion_calidad?.anclaje_fuente_score);
  const fidelidad = Number.isFinite(puntaje) ? Math.round(Math.min(Math.max(puntaje, 0), 1) * 100) : null;
  const claridad = datos.evaluacion_calidad?.claridad_pedagogica;
  const resumenDiag = diagnostico.resumen;

  const descargar = () => {
    const blob = new Blob([JSON.stringify(datos, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'krystal-material.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="contenedor contenedor--estudio">
      <div>
        <button className="enlace-volver" style={{ marginBottom: 28 }} onClick={() => setConfirmar(true)}>
          <Icono nombre="RotateCcw" tamano={16} /> Empezar de nuevo
        </button>
        <MigaDePan vertical />
      </div>

      <main id="contenido" className="principal" tabIndex={-1}>
        <Insignia color="turquesa">Listo para estudiar</Insignia>
        <h1>
          ¡Aquí tienes tu material de estudio <span className="titulo-degradado">personalizado!</span>
        </h1>
        <p className="subtitulo">
          Adaptamos el contenido a tu nivel y lo convertimos en material de estudio para que aprendas de forma clara,
          práctica y efectiva.
        </p>

        <div className="pestanas" role="tablist" aria-label="Formato de estudio">
          <button role="tab" aria-selected="true" className="pestana">
            <Icono nombre={info.icono} tamano={20} /> {info.texto}
          </button>
        </div>

        <div role="tabpanel">
          {!items.length && (
            <p className="tarjeta">El material llegó vacío. Reinicia el proceso para intentarlo de nuevo.</p>
          )}
          {items.length > 0 && formato === 'Flashcards' && <Flashcards tarjetas={items} />}
          {items.length > 0 && formato === 'Quiz' && <Quiz preguntas={items} />}
          {items.length > 0 && formato !== 'Flashcards' && formato !== 'Quiz' && (
            <Pasos contenido={contenido} metadatos={datos.metadatos} items={items} />
          )}
        </div>

        {/* Al terminar, la única forma de cambiar respuestas o archivos es reiniciar */}
        <section className="tarjeta tarjeta-reinicio">
          <span className="circulo-icono">
            <Icono nombre="RotateCcw" />
          </span>
          <div>
            <h3>¿Quieres estudiar otro tema o cambiar tu perfil?</h3>
            <p>Tus respuestas y archivos quedaron fijos para este material. Reinicia para empezar un proceso nuevo.</p>
          </div>
          <Boton iconoIzq="RotateCcw" onClick={() => setConfirmar(true)}>
            Reiniciar proceso
          </Boton>
        </section>
      </main>

      <aside className="columna-derecha" aria-label="Tu sesión y acciones">
        <section className="tarjeta" style={{ padding: 16 }}>
          <ul style={{ margin: 0, padding: 0 }}>
            <li className="fila-sesion" style={{ listStyle: 'none' }}>
              <span className="circulo-icono">
                <Icono nombre="FileText" />
              </span>
              <div>
                <div className="fila-sesion__titulo">
                  {archivos.length > 1 ? `${archivos.length} documentos` : 'Documento'}
                </div>
                {archivos.map((a) => (
                  <div key={a.id} className="fila-sesion__detalle" style={{ color: 'var(--texto)', fontSize: 14 }}>
                    {a.nombre} <span style={{ color: 'var(--texto-2)' }}>· {a.tamano}</span>
                  </div>
                ))}
              </div>
            </li>
            <li className="fila-sesion" style={{ listStyle: 'none' }}>
              <span className="circulo-icono">
                <Icono nombre="User" />
              </span>
              <div>
                <div className="fila-sesion__titulo">Tu perfil</div>
                <div>{nivel?.corto}</div>
                <div className="fila-sesion__detalle">
                  {[estilo?.corto, mundo?.texto, prof?.corto].filter(Boolean).join(' · ')}
                </div>
                {resumenDiag && (
                  <div className="fila-sesion__detalle">
                    Diagnóstico: {resumenDiag.aciertos} de {resumenDiag.total} · nivel sugerido: {resumenDiag.nivel}
                  </div>
                )}
              </div>
            </li>
          </ul>
        </section>

        {fidelidad !== null && (
          <section className="tarjeta" style={{ padding: 22 }}>
            <div className="anillo">
              <svg width="76" height="76" viewBox="0 0 76 76" aria-hidden="true">
                <circle cx="38" cy="38" r="33" fill="none" stroke="var(--turquesa-suave)" strokeWidth="7" />
                <circle
                  cx="38" cy="38" r="33" fill="none" stroke="var(--turquesa)" strokeWidth="7" strokeLinecap="round"
                  strokeDasharray={`${(2 * Math.PI * 33 * fidelidad) / 100} 999`} transform="rotate(-90 38 38)"
                />
              </svg>
              <div>
                <strong>Fidelidad a la fuente</strong>
                <div className="anillo__valor">{fidelidad}%</div>
                {claridad && <div className="fila-sesion__detalle">Claridad pedagógica: {claridad.toLowerCase()}</div>}
              </div>
            </div>
          </section>
        )}

        <section className="tarjeta" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Icono nombre="Zap" tamano={20} color="var(--indigo)" /> Acciones rápidas
          </h3>
          {[
            { icono: 'Download', titulo: 'Descargar todo el material', detalle: 'Archivo JSON (PDF y Anki próximamente)', accion: descargar },
            { icono: 'RotateCcw', titulo: 'Reiniciar proceso', detalle: 'Nuevo perfil y nuevos documentos, desde cero', accion: () => setConfirmar(true) },
          ].map((a) => (
            <button key={a.titulo} className="accion" onClick={a.accion}>
              <Icono nombre={a.icono} />
              <div>
                <strong>{a.titulo}</strong>
                <span>{a.detalle}</span>
              </div>
              <Icono nombre="ChevronRight" tamano={18} />
            </button>
          ))}
        </section>
      </aside>

      {confirmar && (
        <Dialogo
          titulo="¿Seguro que quieres reiniciar el proceso?"
          texto="Se borrarán tus respuestas, tus archivos y el material generado en esta sesión. Volverás a la bienvenida para empezar de cero."
          textoConfirmar="Sí, reiniciar"
          onCancelar={() => setConfirmar(false)}
          onConfirmar={reiniciar}
        />
      )}
    </div>
  );
}

// Sin resultado no se inventa contenido: se avisa y se permite empezar de nuevo
export default function Estudio() {
  const { resultado, reiniciar } = useSesion();
  if (!resultado) {
    return (
      <main id="contenido" tabIndex={-1} style={{ maxWidth: 520, margin: '120px auto', padding: 24, textAlign: 'center' }}>
        <h1>No hay material para mostrar</h1>
        <p style={{ margin: '12px 0 24px' }}>Algo salió mal al generar tu material. Empieza de nuevo para intentarlo otra vez.</p>
        <Boton iconoIzq="RotateCcw" onClick={reiniciar}>
          Empezar de nuevo
        </Boton>
      </main>
    );
  }
  return <EstudioContenido datos={resultado} />;
}