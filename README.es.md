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
fusión RRF · LangGraph (RAG correctivo/agéntico) · FastAPI · Azure OpenAI `gpt-4o-mini`.
Desplegado gratis en Hugging Face Spaces. Python 3.12, gestionado con
[uv](https://docs.astral.sh/uv/). Costo recurrente ~$0–1/mes.

## Qué hace

Un endpoint `/ask` de FastAPI entrega la pregunta a un agente **LangGraph** que
enruta → recupera → genera con citas → autoverifica la fundamentación → reintenta con un
fallback si la respuesta no está respaldada. La recuperación ejecuta **búsqueda vectorial
sobre colecciones de Qdrant Cloud** construidas a partir de nuestro propio contenido con
fragmentación personalizada, fusionadas entre docs/código/carrera con **Reciprocal Rank
Fusion**. El agente es el dueño del razonamiento y de la fusión; el servicio gestionado es
el dueño del almacenamiento vectorial + embeddings (build-vs-buy — ver
[`ARCHITECTURE.md`](ARCHITECTURE.md)).

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
  `gpt-4o-mini` de Azure OpenAI. Se necesita un token de GitHub solo para la fuente de issues
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

**Instancia portfolio** (n=10, preguntas de carrera + repos de portafolio): **enrutamiento
1.0, relevancia hit@6 0.8 (carrera 0.6 · mixto 1.0), fidelidad 1.0**
([`docs/eval-results-portfolio.md`](docs/eval-results-portfolio.md)). Las preguntas fuera
de tema son rechazadas por la barrera de alcance configurable.

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
  de embeddings gratuito (`all-MiniLM-L6-v2`, 384-dim, ventana de ~256 tokens) que trunca las
  entradas de carrera más largas. La fundamentación se mantiene en 1.0; hay mitigaciones
  documentadas.
- La fundamentación usa un juez LLM (gpt-4o-mini), por lo que los puntajes tienen pequeña
  varianza entre ejecuciones.

## Documentación

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — componentes, flujo de datos, grafo del agente,
  decisiones.
- [`docs/setup.md`](docs/setup.md) — aprovisionamiento de Qdrant + Azure OpenAI.
- [`docs/deploy.md`](docs/deploy.md) — build del contenedor + despliegue en Hugging Face Spaces.
- [`docs/eval-qdrant-vs-azure.md`](docs/eval-qdrant-vs-azure.md) — deltas de la migración de backend.
- [`docs/phases/README.md`](docs/phases/README.md) — registro de desarrollo fase por fase.

## Licencia

Para fines de curso y demostración de portafolio.
