<img width="896" height="1200" alt="logo krystal ok" src="https://github.com/user-attachments/assets/7a718a0a-4cec-48b5-acc6-9b2a355af1f9" />
﻿<p align="center"> <strong>Sistema Inteligente de Adaptación y Generación de Contenido Educativo</strong>
<br>  </p>
<p align="center"> <strong> Hackaton_G10_Equipo_52  </p>


<h1 align="center">Krystal <img src="https://media.giphy.com/media/hvRJCLFzcasrR4ia7z/giphy.gif" width="35"></h1>
<picture> <img align="right" src="https://github.com/7oSkaaa/7oSkaaa/blob/main/Images/Right_Side.gif?raw=true" width = 250px></picture>

## :triangular_ruler:
🛠 Funcionalidades del proyecto

Ingesta de documentos

Chunking con chunk_id

Embeddings

Vector Store ChromaDB

Grafo en LangGraph Investigador, Redactor, Revisor

Structured Outputs



### :clapper:


## :pencil2:
📌

# Krystal · Aprende a tu manera

> Sistema inteligente de adaptación y generación de contenido educativo a partir de documentación técnica.
> **Proyecto 1 · NuevaMente** — Hackathon ONE G10 (Oracle Next Education + Alura) · Simulación No Country

## 1. Resumen

Krystal toma documentación técnica densa (manuales, artículos, bases de conocimiento) y la convierte, en minutos, en material de estudio personalizado. La persona sube sus documentos y define **para quién** es el material (perfil), **en qué formato** lo quiere (resumen, flashcards, quiz o tutorial) y **en qué contexto** lo va a aplicar (sector).

Un sistema de agentes con RAG reescribe el contenido **anclado en las fuentes originales**, verifica su fidelidad y entrega un paquete en **JSON estructurado**. El resultado se guarda en **OCI Object Storage** y se muestra en una interfaz web interactiva.

## 2. Problema y propuesta de valor

Las empresas y escuelas de tecnología producen documentación muy rica, pero difícil de leer para quien no domina la jerga. Un mismo manual debe enseñarse de manera muy distinta a una persona que da sus primeros pasos y a otra que tomará decisiones de inversión, y adaptarlo a mano consume semanas de trabajo de especialistas.

Krystal propone:

- **Ingerir documentos densos** sin preprocesamiento manual.
- **Personalizar el lenguaje y la didáctica** al perfil de cada persona.
- **Generar formatos de estudio** (resumen, flashcards, quiz, tutorial) con pocos clics.
- **Garantizar fidelidad:** cada elemento generado cita los fragmentos del documento que lo respaldan, y un revisor verifica que no se hayan inventado datos.
- **Reducir el tiempo de producción** de semanas a minutos.

## 3. Funcionalidades

- **Ingesta de PDF, Markdown y texto plano:** hasta 5 archivos por proceso, de hasta 20 MB cada uno.
- **4 perfiles de destinatario:** Principiante, Intermedio, Avanzado y Ejecutivo (no técnico).
- **4 formatos de salida:** resumen ejecutivo, flashcards, quiz con justificaciones y tutorial paso a paso.
- **Contexto de aplicación:** más de una docena de sectores (educación, salud, finanzas, comercio, logística, tecnología, entre otros) y la opción "General".
- **Nivel de detalle** configurable.
- **Diagnóstico opcional:** preguntas de opción múltiple generadas a partir del propio documento para estimar el punto de partida de la persona.
- **Material interactivo:** flashcards que se voltean y quiz con retroalimentación inmediata y explicación de cada respuesta.
- **Metadatos de aprendizaje:** conceptos clave, prerrequisitos y tiempo estimado de estudio.
- **Evaluación de calidad:** puntaje de fidelidad a la fuente (de 0 a 1), claridad pedagógica y observaciones del revisor.
- **Salida en JSON** descargable y accesible por API para integrarse con otros sistemas.
- **Persistencia en OCI Object Storage** de los documentos originales y de los paquetes generados.
- **Manejo de errores** con mensajes claros en español, y botones para reintentar o volver a empezar.

## 4. Flujo de la persona usuaria

La interfaz es un asistente (wizard) de 5 pasos:

1. **Tu perfil:** 4 preguntas rápidas definen el perfil, el formato, el sector y el nivel de detalle.
2. **Carga:** se suben uno o varios documentos (PDF, Markdown o TXT).
3. **Procesamiento:** se muestra el avance real de los agentes mientras trabajan.
4. **Diagnóstico (opcional):** preguntas sobre el documento para afinar el nivel; se puede saltear.
5. **Estudio:** se presenta el material, la evaluación de fidelidad y la descarga del JSON.

## 5. Arquitectura

```
   Usuario (navegador)
          │  sube documentos y elige perfil, formato y sector
          ▼
┌────────────────────────────────────────────────┐
│ FRONTEND · React + Vite                        │
│ Wizard: Perfil → Carga → Procesamiento →       │
│         Diagnóstico → Estudio                  │
└────────────────────────────────────────────────┘
          │  POST /adaptar (multipart)      → job_id
          │  GET  /adaptar/{id} cada 2 s    → etapa y resultado
          ▼
┌────────────────────────────────────────────────┐
│ BACKEND · FastAPI (Python)                     │
│ Validación Pydantic · tareas en segundo plano  │
│ Errores con mensajes amigables                 │
└────────────────────────────────────────────────┘
      │                                │
      ▼                                ▼
┌─────────────────────────────┐   ┌────────────────────────┐
│ PIPELINE RAG                │   │ OCI OBJECT STORAGE     │
│ 1 Ingesta (PyPDF, MD, TXT)  │   │ originales/            │
│ 2 Chunking (LangChain)      │   │ resultados/            │
│ 3 Embeddings (Gemini)       │   │ cache/                 │
│ 4 Vector store (ChromaDB)   │   └────────────────────────┘
└─────────────────────────────┘
      │
      ▼
┌────────────────────────────────────────────────┐
│ GRAFO DE AGENTES · LangGraph                   │
│ LLM: Groq (Gemini como alternativa)            │
└────────────────────────────────────────────────┘
```

**Cómo se comunican:** el procesamiento puede tardar, así que la API es asíncrona. `POST /adaptar` recibe los documentos y responde de inmediato con un `job_id`; el frontend consulta `GET /adaptar/{job_id}` cada 2 segundos y muestra la etapa real hasta que el resultado está listo.

**Módulos del backend (`backend/app/`):**

- `main.py`: endpoints, validación de entrada y manejo de errores.
- `pipeline.py`: orquesta la ingesta, el RAG, los agentes y el guardado en OCI.
- `ingesta.py`, `chunking.py`, `embeddings.py`, `vectorstore.py`: pipeline RAG.
- `agents.py`: grafo de LangGraph.
- `prompts.py`: prompts con role prompting y few-shot.
- `fidelidad.py`: verificación de citas y puntaje de anclaje.
- `storage.py`: integración con OCI Object Storage.
- `schemas.py`: esquemas Pydantic de entrada y salida.
- `jobs.py`, `config.py`: tareas en curso y configuración.

## 6. Pipeline RAG

1. **Ingesta:** los PDF se leen página por página con PyPDF (se conserva el número de página para citar la fuente); Markdown y TXT se leen como texto. Se limpia el texto (palabras cortadas, espacios y saltos repetidos).
2. **Chunking:** `RecursiveCharacterTextSplitter` de LangChain (fragmentos de 1000 caracteres con 150 de solapamiento). En los archivos Markdown se divide primero por títulos, de modo que cada fragmento conserve su sección. Cada fragmento recibe un identificador estable (`chunk_000`, `chunk_001`, …).
3. **Embeddings:** modelo de embeddings de Gemini (configurable). El proveedor está aislado en una única función para poder cambiarlo.
4. **Vector store:** ChromaDB persistente, con una colección por documento identificada por un hash de su contenido; el mismo documento no se vuelve a indexar.
5. **Recuperación:** búsqueda semántica con varias consultas (título, conceptos clave, procesos y ejemplos, sector). Se envían al modelo los fragmentos más relevantes, sin  repetir y en el orden original; en documentos cortos se envía todo.

## 7. Orquestación con agentes (LangGraph)

```
             solicitud (tarea = adaptar)
                          │
                          ▼
 ┌─────────────────────────────────────────────────┐
 │ INVESTIGADOR · recupera, sin LLM                │
 │ busca los fragmentos más relevantes en ChromaDB │
 └─────────────────────────────────────────────────┘
                          │
                          ▼
 ┌─────────────────────────────────────────────────┐
 │ REDACTOR · LLM                                  │ ◀──────┐
 │ adapta al perfil y sector; genera el formato    │        │
 └─────────────────────────────────────────────────┘        │ reintento: el redactor recibe
                          │                                 │ las observaciones del revisor
                          ▼                                 │
 ┌─────────────────────────────────────────────────┐        │
 │ REVISOR · verificación de fidelidad             │        │
 │ 1) las citas existen en el documento            │ ───────┘ si la fidelidad es < 0,85
 │ 2) un LLM juez revisa cada afirmación           │          (máx. 2 reintentos; si se agotan,
 └─────────────────────────────────────────────────┘          se entrega con una advertencia)
                          │
                          ▼
      RESULTADO JSON validado con Pydantic
```

Un **router** al inicio del grafo decide el camino según la tarea. Si la tarea es `diagnostico`, el grafo va directo al **evaluador**, que genera 5 preguntas de opción múltiple basadas solo en los fragmentos del documento. La adaptación y el diagnóstico se ejecutan en paralelo.

**Agentes:**

- **Investigador (sin LLM):** recupera el contexto relevante desde ChromaDB.
- **Redactor (LLM):** reescribe el contenido según el perfil, el sector y el nivel de detalle, y lo entrega directamente en el formato pedido, con salida estructurada validada por Pydantic. Cada elemento incluye las fuentes (`chunk_id`) que lo respaldan.
- **Revisor:** verifica la fidelidad en dos capas. La primera es determinista: descarta las citas a fragmentos que no existen y penaliza los elementos sin cita válida. La segunda es un LLM juez que estima qué proporción de las afirmaciones está respaldada por el documento. El puntaje final de anclaje combina ambas capas.
- **Evaluador (LLM):** genera el diagnóstico de nivel.

**Prompts:** se usan *role prompting* (diseñador instruccional senior) y *few-shot*: un mismo fragmento reescrito para cada uno de los cuatro perfiles, más un ejemplo de elemento por formato. Los prompts incluyen una regla contra la inyección de instrucciones: el texto del documento se trata como datos.

**Robustez:** si el modelo devuelve un JSON inválido o el proveedor limita la velocidad, se reintenta con esperas progresivas, y si no se resuelve se informa un mensaje claro.

## 8. API REST

La documentación interactiva (Swagger) está disponible en `/docs` cuando el backend está en ejecución.

- `POST /adaptar` (multipart): recibe `archivos` (1 a 5), `perfil_destinatario`, `formato_salida`, `nicho_sector`, `nivel_detalle` y `session_id`. Responde `202` con `{ "job_id": "..." }`.
- `GET /adaptar/{job_id}`: devuelve `estado` (`procesando`, `listo` o `error`), `etapa` (1 a 3), `mensaje` y, si terminó, el `resultado`.
- `POST /adaptar/sincrono` (JSON): variante del ejemplo de la consigna. Recibe el texto del documento en el cuerpo y devuelve el paquete completo en una sola respuesta.
- `GET /salud`: estado del servicio, proveedor de almacenamiento y modelo configurado.

**Valores aceptados:**

- `perfil_destinatario`: Principiante, Intermedio, Avanzado, Ejecutivo.
- `formato_salida`: Resumen, Flashcards, Quiz, Tutorial.
- `nivel_detalle`: Conciso, Didactico, Profundo.
- `nicho_sector`: General y los sectores disponibles (los valores se aceptan con o sin tildes y sin distinguir mayúsculas).

**Ejemplo de solicitud (JSON de la consigna):**

```json
{
  "documento_titulo": "Introduccion a la Arquitectura de Redes VCN en OCI",
  "documento_contenido": "La Virtual Cloud Network (VCN) es una red privada y personalizable configurada en Oracle Cloud Infrastructure...",
  "perfil_destinatario": "Principiante",
  "formato_salida": "Flashcards",
  "nicho_sector": "General",
  "nivel_detalle": "Didactico"
}
```

**Estructura de la respuesta (ejemplo ilustrativo, abreviado):**

```json
{
  "status": "exito",
  "doc_id": "a1b2c3d4e5f60718",
  "metadatos": {
    "perfil_aplicado": "Principiante",
    "formato_generado": "Flashcards",
    "nicho_sector": "General",
    "nivel_detalle": "Didactico",
    "tiempo_estimado_estudio_minutos": 5,
    "conceptos_clave": ["VCN", "Subredes", "Internet Gateway", "Security Lists"],
    "prerrequisitos": ["Nociones básicas de redes"]
  },
  "contenido_adaptado": {
    "titulo": "Dominando Redes en la Nube (VCN) desde Cero",
    "introduccion_contextualizada": "Imagina la VCN como tu propio barrio privado dentro de la nube de Oracle...",
    "items": [
      {
        "frente": "¿Qué es una VCN en Oracle Cloud?",
        "dorso": "Es tu red virtual privada y personalizada dentro de la nube de Oracle.",
        "pista_didactica": "Piensa en ella como el terreno cercado donde residen tus servidores.",
        "fuentes": ["chunk_000"]
      }
    ]
  },
  "evaluacion_calidad": {
    "anclaje_fuente_score": 0.96,
    "claridad_pedagogica": "Alta",
    "observaciones": "Sin observaciones."
  },
  "almacenamiento_oci": {
    "bucket": "krystal-contenidos-educativos",
    "objeto_id": "resultados/sesion-1/a1b2c3d4e5f60718-principiante-flashcards.json",
    "status_upload": "completado"
  },
  "diagnostico": { "preguntas": [] },
  "fuentes_detalle": {
    "chunk_000": { "archivo": "manual.pdf", "pagina": 1, "fragmento": "La Virtual Cloud Network (VCN) es..." }
  }
}
```

Según el formato, cada elemento de `items` tiene: `frente`, `dorso` y `pista_didactica` (flashcards); `pregunta`, `opciones`, `respuesta_correcta` y `justificacion` (quiz); o `titulo_paso` y `texto` (resumen y tutorial). Todos incluyen `fuentes`.

## 9. Tecnologías

- **Frontend:** React, Vite, CSS propio y iconos de Lucide.
- **Backend:** Python, FastAPI, Uvicorn y Pydantic v2.
- **RAG:** PyPDF, LangChain (divisores de texto) y ChromaDB.
- **Agentes:** LangGraph.
- **Modelo de lenguaje:** Gemini.
- **Embeddings:** Gemini.
- **Nube:** OCI Object Storage (capa Always Free) mediante el SDK oficial de Python.
- **Pruebas:** pytest.

## 10. Escenarios de demostración

Todos los escenarios usan **el mismo documento técnico**: nombre del documento "Introducción a la arquitectura de redes VCN en OCI"]. El objetivo es mostrar cómo cambian el lenguaje, la profundidad y el formato según los parámetros.

**Escenario A · Principiante + Flashcards + General**
- Parámetros: perfil Principiante, formato Flashcards, sector General, detalle Didáctico.
- Qué se observa: analogías cotidianas, términos técnicos definidos y pistas para recordar.

**Escenario B · Ejecutivo + Resumen + Finanzas**
- Parámetros: perfil Ejecutivo, formato Resumen, sector Finanzas, detalle Didáctico.
- Qué se observa: foco en impacto, riesgo y decisiones, sin jerga, con ejemplos del sector.

**Escenario C · Avanzado + Quiz + Comercio**
- Parámetros: perfil Avanzado, formato Quiz, sector Comercio, detalle Profundo.
- Qué se observa: preguntas técnicas con opciones plausibles y justificación inmediata de cada respuesta, anclada al documento.

**Escenario D · Intermedio + Tutorial + Educación**
- Parámetros: perfil Intermedio, formato Tutorial, sector Educación, detalle Didáctico.
- Qué se observa: pasos ordenados y accionables, con terminología técnica y ejemplos concretos.

**Cómo reproducirlos:** abrir la aplicación, responder las 4 preguntas de perfil con los valores del escenario, subir el documento, esperar el procesamiento, omitir o responder el diagnóstico y revisar el material y la evaluación de calidad. También pueden probarse desde `/docs` con `POST /adaptar/sincrono`.

## 11. Cumplimiento de la consigna

**Requisitos mínimos**

- ✅ Ingesta de documentos técnicos en PDF, Markdown y texto.
- ✅ RAG con segmentación (chunking), embeddings y búsqueda vectorial en un vector store (ChromaDB).
- ✅ Orquestación con LLM (Groq, con Gemini como alternativa) mediante LangGraph.
- ✅ Adaptación del mismo contenido para 4 perfiles y 4 formatos distintos.
- ✅ Salida estructurada en JSON, interfaz interactiva (React) y API REST (FastAPI).
- ✅ Integración con OCI Object Storage (capa Always Free): documentos originales, resultados y caché.
- ✅ Mecanismo de verificación de fidelidad contra las fuentes para mitigar alucinaciones.
- ✅ Prompts estructurados con role prompting y few-shot.
- ✅ Validación de entrada y salida con tipado estricto (Pydantic) y manejo de errores con mensajes amigables.
- ✅ Al menos 3 escenarios de demostración (sección 10).
- ✅ Documentación con arquitectura y diagrama del flujo RAG y de agentes (secciones 5 a 7).

**Diferenciales**

- ✅ Sistema multi-agente con LangGraph: router, investigador RAG, redactor y revisor.
- ✅ Quiz con evaluación inmediata y retroalimentación explicativa.
- 🔶 Exportación: descarga en JSON. Markdown, PDF y CSV para Anki quedan como mejora futura.
- ⏳ Despliegue completo en la nube: https://krystal-g4vt.onrender.com/
- ➖ Soporte multimodal: no incluido en esta versión.

## 12. Guía de instalación

### Requisitos

- Python 3.11 o superior (probado con 3.12).
- Node.js 20.19 o superior (o 22.12 o superior) y npm.
- Git.
- Una clave de **Gemini** (modelo de lenguaje) y una de **Google AI Studio / Gemini** (embeddings), ambas gratuitas.
- Una cuenta de **OCI** con un bucket de Object Storage en la capa Always Free (para la persistencia).

### 1. Clonar el repositorio

```bash
git clone https://github.com//No-Country-simulation/Hackaton_G10_Equipo_52
cd Hackaton_G10_Equipo_52
```

### 2. Backend

En **Windows (PowerShell)**:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

En **Linux / macOS**:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Completar `backend/.env` (las variables principales):

- `LLM_PROVIDER`: `gemini`.
- `LLM_MODEL`: modelo de lenguaje a usar `gemini-3.8-flash`.
- `GOOGLE_API_KEY`: clave de Gemini, usada para los embeddings y LLM.
- `EMBEDDING_PROVIDER` y `EMBEDDING_MODEL`: proveedor y modelo de embeddings.
- `OCI_ENABLED`: `true` para guardar en OCI Object Storage; `false` guarda en disco (solo desarrollo).
- `OCI_BUCKET`: krystal-contenidos-educativos.
- `OCI_NAMESPACE` (opcional), `OCI_CONFIG_FILE` y `OCI_PROFILE`: ubicación del archivo de configuración de OCI.
- `UMBRAL_FIDELIDAD` y `MAX_REINTENTOS`: umbral de fidelidad (0,85 por defecto) y reintentos del revisor (2 por defecto).
- `MAX_ARCHIVOS`, `MAX_MB`, `MAX_PAGINAS`, `MAX_CHUNKS`, `MAX_CONTEXTO` y `MAX_TAREAS`: límites del servicio.
- `CORS_ORIGINS`: origen permitido para el frontend (por defecto `http://localhost:5173`).

Levantar el servidor **desde la carpeta `backend`**:

```bash
uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000` y su documentación en `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install
```

Crear `frontend/.env.local` para conectarlo al backend real:

```
VITE_USE_DEMO=false
VITE_API_URL=http://localhost:8000
```

```bash
npm run dev
```

La aplicación queda en `http://localhost:5173`. Si no se define `VITE_USE_DEMO`, `npm run dev` usa datos simulados y permite trabajar la interfaz sin backend.

### 4. Conectar OCI Object Storage

1. En la consola de OCI, crear un bucket en la capa **Always Free** (`krystal-contenidos-educativos`).
2. Generar una clave de API para el usuario y guardar la configuración (`~/.oci/config`) junto con la clave privada. Estos archivos no se suben al repositorio.
3. En `backend/.env`: `OCI_ENABLED=true` y `OCI_BUCKET` con el nombre del bucket.
4. Reiniciar el backend, procesar un documento y comprobar en la consola que aparecen los objetos `originales/…`, `resultados/…` y `cache/…`. La respuesta debe indicar `"status_upload": "completado"`.

### 5. Pruebas

Desde la carpeta `backend`:

```bash
pytest
```

La suite cubre la ingesta, el chunking, la verificación de fidelidad, los agentes (incluyendo el bucle de reintentos y el enrutamiento) y la API. Usa un modelo de lenguaje simulado y embeddings de prueba, por lo que no consume cuota ni requiere claves.

## 13. Despliegue

Render, https://krystal-g4vt.onrender.com/.

## 14. Seguridad y privacidad

- No hay inicio de sesión: cada visita es una sesión anónima identificada por un identificador aleatorio.
- Las claves se leen de variables de entorno; el archivo `.env` y las credenciales de OCI están excluidos del repositorio.
- Los nombres de archivo y los identificadores de sesión se sanean antes de usarse como nombres de objeto en OCI.
- Se validan la cantidad, el tamaño y el tipo de los archivos, tanto en el frontend como en el backend.
- El texto de los documentos se trata como datos, no como instrucciones, para mitigar la inyección de prompts.

## 15. Limitaciones conocidas y mejoras futuras

- No hay OCR: los PDF escaneados (sin texto seleccionable) se detectan y se informa que no se pueden procesar.
- Las tareas en curso se guardan en memoria y se pierden si el servidor se reinicia.
- La velocidad y la cuota dependen de los planes gratuitos de los proveedores de IA.
- Mejoras previstas: exportación a Markdown, PDF y Anki, panel de fuentes con el fragmento original de cada cita, comparador de perfiles, soporte multimodal y despliegue en una VM de OCI.

## 16. Estructura del repositorio

```
├── backend/
│   ├── app/            # API, pipeline RAG, agentes, prompts, fidelidad y almacenamiento
│   ├── tests/          # pruebas automáticas (pytest)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/            # pantallas, componentes, contexto, servicios, datos y estilos
│   └── .env.example
├── LICENSE
└── README.md
```

## 17. Equipo y enlaces

**Equipo:** Hackaton_G10_Equipo_52

- Kiara Antonella Kuznicki — AI Engineer
- Andrés Felipe Guzmán Romero — Database Administrator
- Carlos Arturo Torres Jara — Backend Developer
- Fernando Méndez García — Project Manager
- Francisco León — Vibe Coder
- Carlos Gernhofer — Backend Developer

**Enlaces:**

- Repositorio: https://github.com//No-Country-simulation/Hackaton_G10_Equipo_52
- Aplicación desplegada: https://krystal-g4vt.onrender.com/
- Video demo: mp4

## 18. Licencia

Ver el archivo `LICENSE` del repositorio.


## :rocket:

🚀  :rocket:

## :flashlight:
- Despliegue del proyecto a través de Render: https://krystal-g4vt.onrender.com/
- Acceso al proyecto: a través de GitHub: https://github.com//No-Country-simulation/Hackaton_G10_Equipo_52
- Estado del proyecto: funcional 100%
