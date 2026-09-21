# Repo Expert

> 🇬🇧 English? Read [`README.md`](README.md).

**RAG agéntico que responde preguntas sobre cualquier repositorio de GitHub al que se le
apunte, con citas en línea.** Una sola base de código, dos instancias seleccionadas por
configuración — sin cambios de código para alternar:

- **public** — entregable de clase apuntado a un repositorio público serio
  (`fastapi/fastapi`).
- **portfolio** — demo para reclutadores apuntada a los repositorios de portafolio de
  Jorge Pulgar + una Base de Conocimiento de Carrera (Career KB).

Stack: Qdrant Cloud (búsqueda vectorial + inferencia gratuita del lado del servidor) ·
fusión RRF · LangGraph (RAG correctivo/agéntico) · FastAPI · Azure OpenAI `gpt-5-mini`.
Desplegado en Azure Container Apps (escala a cero). Python 3.12, gestionado con
[uv](https://docs.astral.sh/uv/). Costo recurrente ~$0–1/mes.

**En vivo (instancia portfolio):**
`https://ca-repo-expert.delightfulgrass-0e92a824.swedencentral.azurecontainerapps.io`
— [`/health`](https://ca-repo-expert.delightfulgrass-0e92a824.swedencentral.azurecontainerapps.io/health)
· [`/docs`](https://ca-repo-expert.delightfulgrass-0e92a824.swedencentral.azurecontainerapps.io/docs).
Al escalar a cero, la primera petición tras un periodo inactivo tarda unos segundos en
despertar el contenedor.

## Qué hace

Un endpoint `/ask` de FastAPI entrega la pregunta a un agente **LangGraph** que
enruta → recupera → genera con citas → autoverifica la fundamentación → reintenta con un
fallback si la respuesta no está respaldada. La recuperación ejecuta **búsqueda vectorial
sobre colecciones de Qdrant Cloud** construidas a partir de nuestro propio contenido con
fragmentación personalizada, fusionadas entre docs/código/carrera. El agente es el dueño
del razonamiento y de la fusión; el servicio gestionado es el dueño del almacenamiento
vectorial + embeddings (build-vs-buy — ver [`ARCHITECTURE.md`](ARCHITECTURE.md)).

### El pipeline de recuperación, y por qué existe cada pieza

Cada pieza responde a un fallo observado, no anticipado. Importa más el motivo que la
lista, así que cada fila dice qué se rompió.

| Paso | Qué hace | Por qué |
|---|---|---|
| **Fragmentación por secciones** | un chunk por encabezado markdown, con el encabezado repetido en cada trozo, y las secciones largas partidas por frases | el modelo de embeddings trunca a ~256 tokens **en silencio**; 12 de 22 secciones de carrera se pasaban y su cola era irrecuperable |
| **Embeddings multilingües** | `intfloat/multilingual-e5-small`, con prefijos `query:`/`passage:` | el modelo anterior era solo inglés. El corpus está en inglés y las visitas preguntan en español: *"What projects has Jorge built?"* devolvía 6/6 fragmentos de carrera; la misma pregunta en español, 6/6 texto irrelevante |
| **Fusión ponderada** | los huecos se reparten entre colecciones según lo bien que encaja cada una, medido sobre el rango de puntuaciones de esa consulta | el RRF clásico ordena *dentro* de cada colección, así que todos los #1 empataban y la mezcla se volvía una cuota fija: 2 de 6 huecos por colección, preguntara lo que preguntara |
| **Expansión por vecinos** | cada acierto se amplía con los fragmentos contiguos (`seq` ± 1), fusionados en su propio texto | al partir secciones, una respuesta puede quedar a caballo entre dos; fusionar en vez de añadir mantiene la numeración `[n]` alineada con las citas |
| **Reescritura de consulta, con criterio** | las preguntas cortas, con siglas o de seguimiento se reescriben como pregunta autosuficiente antes de embeber | "ML" no cae cerca de "machine learning". Reescribirlo *todo* empeoraba las cosas — la expansión parecía una lista de palabras clave y casaba con índices — por eso está condicionada |
| **Memoria de conversación** | los turnos previos se reenvían como turnos de chat; el cliente los manda en cada petición | `/ask` es sin estado a propósito: cualquier réplica puede servir cualquier turno y no se guarda nada en el servidor |

### En qué consistió cada arreglo

La tabla de arriba es el diseño. Esto es lo que costó cada cambio y qué movió, porque
"mejoramos la recuperación" no es una afirmación que nadie pueda comprobar.

1. **Embeddings solo-inglés → multilingües.** Diagnosticado dejando fijos el índice y la
   fusión y cambiando solo el idioma de la pregunta: en inglés devolvía 6/6 fragmentos de
   carrera, en español 6/6 texto irrelevante. Cambio a `multilingual-e5-small` — las mismas
   384 dimensiones, así que el esquema de las colecciones no se tocó y solo hubo que
   recalcular los vectores — más los prefijos `query:`/`passage:` con los que se entrena esa
   familia. **Recuperación de carrera 0.6 → 1.0.**
2. **RRF → reparto proporcional.** El primer intento, un multiplicador de peso por
   colección, falló su propio test: escalar una colección hacia abajo deja igualmente todos
   sus resultados por detrás de los del líder, que se queda con todos los huecos. Se
   sustituyó por reparto por restos mayores sobre pesos derivados del rango de puntuaciones
   *de esa consulta* — necesario porque las similitudes de e5 se agrupan en una banda de
   ~0.78–0.88 donde los cocientes en bruto no dicen nada. Una colección sin nada relevante
   ya no ocupa ningún hueco.
3. **Secciones demasiado largas → cortes por frase.** Primero por párrafos, luego por final
   de frase y, como último recurso, por palabras, para ítems de lista y filas de tabla que
   no llevan puntuación; el encabezado se repite en cada trozo y se descuenta del
   presupuesto. **Carrera 22 → 56 fragmentos, el mayor de 4952 a 899 caracteres, ninguno
   por encima del límite.**
4. **Curación del corpus.** Excluidos ficheros de tareas y plantillas de prompts. La
   exclusión además no funcionaba: `fnmatch` deja que `*` cruce `/`, así que `**/tasks/**`
   exigía una barra antes de `tasks` y se dejaba dentro 1003 fragmentos de la raíz.
   Corregido en el comparador, con tests. **Docs 2885 → 1691 fragmentos.**
5. **Alineación del juez.** El juez de fidelidad recupera su propia evidencia y seguía
   haciéndolo con `top=5` recortado a 700 caracteres mientras el generador usaba 12
   fragmentos de 2400 — marcaba como no fundamentadas respuestas correctas porque su
   evidencia había quedado fuera. Una ejecución intermedia marcó **0.1** solo por esto. El
   juez ve ahora la misma amplitud.

Efecto medido sobre el conjunto de portfolio: **hit@6 0.8 → 1.0** (carrera 0.6 → 1.0),
fidelidad 0.7 → 1.0. El delta completo está en
[`docs/eval-qdrant-vs-azure.md`](docs/eval-qdrant-vs-azure.md) — incluida la advertencia de
que el punto 5 es un arreglo de medición y no de calidad, y no debe leerse como tal.

### Protección frente a abuso

`/ask` no requiere autenticación y gasta dinero en cada llamada — tres viajes al LLM:
enrutado, generación y juez de fundamentación. Está limitado a **10 preguntas por hora e
IP**, devolviendo `429` con `Retry-After`, y se rechaza *antes* de llamar al LLM, así que
una petición bloqueada no cuesta nada. `/health` está exento a propósito, para que la
página pueda despertar gratis el contenedor.

> **CORS no es la protección.** Solo lo aplican los navegadores; un script que llame al
> endpoint directamente se lo salta. Lo que protege el crédito es el límite por IP.

## Qué conocimiento tiene — tres fuentes heterogéneas

| # | Fuente | public | portfolio |
|---|---|---|---|
| 1 | Documentación / markdown (en Qdrant) | Docs de FastAPI + README | Markdown de los repos de portafolio |
| 2 | Código fuente (en Qdrant, fragmentado por símbolo) | `fastapi/**/*.py` | Python de los repos de portafolio |
| 3 | **Intercambiada por instancia** | **Issues/PRs de GitHub** — en vivo vía API | **Career KB** — indexada en Qdrant |

La tercera fuente difiere en *tipo* (herramienta de API en vivo vs fuente de conocimiento
indexada), cumpliendo el requisito de ≥3 fuentes heterogéneas. La instancia activa se elige
por completo mediante configuración (`src/repo_expert/config/instance.py`); ver
[`ARCHITECTURE.md`](ARCHITECTURE.md) para el diseño completo.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (gestiona Python 3.12 automáticamente).
- Un clúster gratuito de Qdrant Cloud (con inferencia del lado del servidor) + un deployment
  `gpt-5-mini` de Azure OpenAI. Se necesita un token de GitHub solo para la fuente de issues
  en vivo de la instancia public. Pasos de aprovisionamiento: [`docs/setup.md`](docs/setup.md).

## Instalación

```bash
uv sync                      # instala dependencias en .venv
cp .env.example .env         # luego completa las claves de Qdrant + Azure OpenAI + GitHub
```

Selecciona la instancia en `.env` (o por comando con `--instance`):

```bash
REPO_EXPERT_INSTANCE=public   # o: portfolio
```

Las claves requeridas están documentadas en [`.env.example`](.env.example). La
configuración falla rápido: una variable requerida ausente lanza un error al arranque
nombrando la variable problemática.

## Ejecución

```bash
# 1. Crear las colecciones de Qdrant, luego ingestar el/los repo(s) objetivo
uv run repo-expert provision
uv run repo-expert ingest
uv run repo-expert --instance portfolio ingest   # instancia portfolio

# 2. Servir la API (GET /health, POST /ask; docs interactivas en /docs)
uv run uvicorn repo_expert.api.app:app --reload

# 3. Preguntar
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question": "¿Cómo maneja FastAPI la inyección de dependencias?"}'
```

`GET /health` reporta la instancia activa, el repositorio objetivo y los conteos de
documentos por índice.

## Desarrollo

```bash
uv run ruff check .          # lint
uv run pytest                # tests unitarios (los de integración necesitan .env: -m integration)
```

## Evaluación

Un conjunto curado de preguntas/respuestas mide las dos cosas que importan en un RAG
agéntico: **relevancia de recuperación** y **fundamentación (groundedness)**. Regenerar con
`uv run repo-expert eval` (añade `--instance portfolio` para el conjunto de portafolio).

**Método**
- *Relevancia de recuperación* — por pregunta: (a) **exactitud de enrutamiento**, ¿eligió
  el router la(s) fuente(s) esperada(s); (b) **hit@k**, ¿coincidió un resultado top-k de la
  fuente esperada con la cita esperada (subcadena de archivo/sección) y el tipo.
- *Fundamentación* — se ejecuta el agente completo y luego un **juez LLM independiente**
  evalúa si cada afirmación de la respuesta está respaldada por evidencia recuperada de
  forma independiente. También se registra la propia bandera de autofundamentación del
  agente.

**Instancia public** (`fastapi/fastapi`, n=16 — 5 código, 7 docs, 3 issues, 1 multi-salto):

| Métrica | Valor |
| --- | --- |
| Exactitud de enrutamiento | **1.00** |
| Relevancia hit@6 | **1.00** (docs 1.0 · código 1.0 · issues 1.0 · mixto 1.0) |
| Tasa de fidelidad (juez) | **0.94** |
| Puntaje medio de fidelidad | **0.94** |
| Tasa de autofundamentación del agente | **1.00** |

Reporte completo: [`docs/eval-results-public.md`](docs/eval-results-public.md).

> ⚠️ **Estos números de la instancia public se midieron con `gpt-4o-mini` (2026-06) y no
> se han vuelto a ejecutar tras el cambio a `gpt-5-mini`.** Repetirlos requiere un
> `GITHUB_TOKEN` válido para la fuente de issues en vivo; los números de portfolio de abajo
> sí están actualizados.

**Instancia portfolio** (n=10, preguntas de carrera + repos de portafolio, re-ejecutada el
2026-09-21): **enrutamiento 1.0, relevancia hit@6 1.0 (carrera 1.0 · mixto 1.0),
fidelidad 1.0**
([`docs/eval-results-portfolio.md`](docs/eval-results-portfolio.md)). Las preguntas fuera
de tema son rechazadas por la barrera de alcance configurable. La nota de cambio de modelo
más abajo explica por qué se movió la fidelidad.

**Análisis / limitaciones** (stack Qdrant; comparación completa Azure→Qdrant en
[`docs/eval-qdrant-vs-azure.md`](docs/eval-qdrant-vs-azure.md)):
- La migración a Qdrant + un LLM más barato **mejoró** la instancia public: hit@6
  0.88 → 1.0, relevancia de código 0.6 → 1.0, fidelidad 0.75 → 0.94 — a ~75× menos costo.
- La **fusión RRF** impulsa la ganancia en código: los fragmentos de código puntúan más bajo
  que la prosa en coseno, así que un orden global por puntaje los marginaba; fusionar las
  colecciones por rango lo corrige.
- La recuperación de issues usa una **reescritura de consulta por LLM**: las preguntas en
  prosa se condensan a palabras clave porque la Search API de GitHub usa AND entre términos
  y no devuelve nada para prosa (0.0 → 1.0).
- Una regresión: el recall de **carrera** en portfolio bajó 1.0 → 0.6 — el costo del modelo
  de embeddings gratuito (`multilingual-e5-small`, 384-dim) y de dividir las secciones largas
  entradas de carrera más largas. Hay mitigaciones documentadas.
- La fundamentación usa un juez LLM (gpt-5-mini), por lo que los puntajes tienen varianza
  entre ejecuciones. El juez ya no corre a `temperature=0` — gpt-5-mini solo acepta su
  valor por defecto — así que la varianza es mayor que en ejecuciones anteriores.
- **Cambio de modelo 2026-09-20:** `gpt-4o-mini` dejó de poder desplegarse en Azure
  (obsoleto desde 2026-03-31), así que el stack pasó a `gpt-5-mini`. La recuperación no
  cambia; la fidelidad en portfolio pasa de 1.0 a 0.7, sobre todo porque gpt-5-mini juzga
  con más severidad (dos de los tres fallos puntúan 0.8–0.85). El delta completo está en
  [`docs/eval-qdrant-vs-azure.md`](docs/eval-qdrant-vs-azure.md).

## Documentación

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — componentes, flujo de datos, grafo del agente,
  decisiones.
- [`docs/setup.md`](docs/setup.md) — aprovisionamiento de Qdrant + Azure OpenAI.
- [`docs/deploy.md`](docs/deploy.md) — build del contenedor + despliegue en Azure Container Apps.
- [`docs/eval-qdrant-vs-azure.md`](docs/eval-qdrant-vs-azure.md) — deltas de la migración de backend.
- [`docs/phases/README.md`](docs/phases/README.md) — registro de desarrollo fase por fase.

## Licencia

Para fines de curso y demostración de portafolio.
