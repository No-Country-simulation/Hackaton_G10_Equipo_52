import { Fragment, useEffect, useState } from 'react';
import { useSesion } from '../context/SesionContext';
import { AGENTES } from '../data/contenidoDemo';
import { procesarDocumento } from '../services/api';
import { PREGUNTAS } from '../data/preguntas';
import { validarPreguntas } from '../lib/diagnostico';
import Plantilla from '../components/layout/Plantilla';
import Boton from '../components/ui/Boton';
import NodoAgente from '../components/procesamiento/NodoAgente';
import Icono from '../components/ui/Icono';
import Insignia from '../components/ui/Insignia';
import TituloDegradado from '../components/ui/TituloDegradado';

const QUE_HACE = [
  'Lee tu documento y entiende cómo está organizado.',
  'Adapta el contenido a tu nivel: simplifica conceptos complejos y conserva la información clave, con ejemplos de tu mundo.',
  'Crea tu material en el formato que elegiste y revisa que todo sea fiel al original.',
];

const TOPE = [30, 65, 95]; // hasta dónde avanza la barra en cada etapa real

export default function Procesamiento() {
  const { archivos, respuestas, setResultado, setPreguntasDiagnostico, setDiagnostico, irA } = useSesion();
  const [progreso, setProgreso] = useState(0);
  const [etapa, setEtapa] = useState(1); // etapa real que informa el backend (1 a 3)
  const [error, setError] = useState('');
  const [intento, setIntento] = useState(0); // al aumentar, se vuelve a procesar (botón Reintentar)
  const terminado = progreso === 100;

  // Procesa el documento; el servicio informa la etapa real mientras trabaja
  useEffect(() => {
    const control = new AbortController();
    const perfil = Object.fromEntries(PREGUNTAS.map((p) => [p.campo, respuestas[p.id]]));
    // El setTimeout evita que el doble montaje de StrictMode (desarrollo) envíe la petición dos veces
    const arranque = setTimeout(() => {
      procesarDocumento(archivos.map((a) => a.file), perfil, { senal: control.signal, alCambiarEtapa: setEtapa })
        .then((res) => {
          if (control.signal.aborted) return;
          setResultado(res);
          // Las preguntas del diagnóstico vienen en la respuesta (res.diagnostico.preguntas)
          const preguntas = validarPreguntas(res.diagnostico?.preguntas);
          setPreguntasDiagnostico(preguntas);
          if (!preguntas.length) setDiagnostico({ actual: 0, respuestas: [], saltado: true }); // paso opcional: se omite
          setProgreso(100);
          setTimeout(() => !control.signal.aborted && irA(preguntas.length ? 'diagnostico' : 'estudio'), 700);
        })
        .catch((e) => {
          if (!control.signal.aborted) setError(e.message);
        });
    }, 0);
    return () => {
      clearTimeout(arranque);
      control.abort(); // cancela la petición si se sale de la pantalla
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intento]);

  // La barra avanza despacio dentro de cada etapa real y se detiene si hay error
  useEffect(() => {
    if (error || terminado) return;
    const timer = setInterval(() => setProgreso((p) => Math.min(p + 1, TOPE[etapa - 1] ?? 95)), 250);
    return () => clearInterval(timer);
  }, [etapa, error, terminado]);

  const reintentar = () => {
    setError('');
    setProgreso(0);
    setEtapa(1);
    setIntento((n) => n + 1);
  };

  const agenteActual = terminado ? 3 : etapa - 1;
  const estadoDe = (i) => (i < agenteActual ? 'completado' : i === agenteActual ? 'en-proceso' : 'pendiente');

  return (
    <Plantilla
      consejo="Cuando termine, pasarás a un diagnóstico corto (puedes saltarlo)."
      extraPanel={
        agenteActual < 3 && (
          <div className="caja-agente">
            <strong>
              <Icono nombre="Sparkles" tamano={18} /> ¿Qué hace ahora el Agente {agenteActual + 1}?
            </strong>
            {QUE_HACE[agenteActual]}
          </div>
        )
      }
    >
      <TituloDegradado antes="Estamos procesando tu contenido con la ayuda de nuestros" destacado="agentes de IA" />
      <p className="subtitulo">
        Cada agente trabaja en una etapa clave para transformar tu documento en material de estudio hecho a tu medida.
      </p>

      <section className="tarjeta pipeline" aria-label="Pipeline de agentes">
        <div className="pipeline__encabezado">
          <div>
            <h3>Pipeline de agentes</h3>
            <p>
              Procesando{' '}
              {archivos.length > 1 ? `${archivos.length} documentos` : archivos[0]?.nombre || 'tu documento'}…
            </p>
          </div>
          <Insignia color={progreso === 100 ? 'turquesa' : 'indigo'}>
            {progreso === 100 ? 'Completado' : 'En progreso'}
          </Insignia>
        </div>

        <div className="agentes">
          {AGENTES.map((a, i) => (
            <Fragment key={a.nombre}>
              <NodoAgente numero={i + 1} {...a} estado={estadoDe(i)} />
              {i < AGENTES.length - 1 && (
                <div className={`agente__conector ${i < agenteActual ? 'agente__conector--hecho' : ''}`} aria-hidden="true">
                  <span />
                  {i < agenteActual ? <Icono nombre="Check" tamano={16} /> : '•'}
                  <span />
                </div>
              )}
            </Fragment>
          ))}
        </div>

        <div>
          <div className="progreso-fila">
            <div
              className="barra"
              role="progressbar"
              aria-valuenow={progreso}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Progreso del procesamiento"
            >
              <span style={{ width: `${progreso}%` }} />
            </div>
            {progreso}%
          </div>
          <p className="texto-tiempo" aria-live="polite">
            <Icono nombre="Clock" tamano={16} />
            {progreso === 100
              ? '¡Listo! Pasando al diagnóstico…'
              : `Etapa ${agenteActual + 1} de 3 · Puede tardar un par de minutos`}
          </p>
          {error && (
            <>
              <p className="mensaje-error" role="alert">
                {error}
              </p>
              <div style={{ display: 'flex', gap: 12, marginTop: 12, flexWrap: 'wrap' }}>
                <Boton iconoIzq="RotateCcw" onClick={reintentar}>
                  Reintentar
                </Boton>
                <Boton tipo="fantasma" onClick={() => irA('carga')}>
                  Volver a la carga
                </Boton>
              </div>
            </>
          )}
        </div>
      </section>
    </Plantilla>
  );
}
