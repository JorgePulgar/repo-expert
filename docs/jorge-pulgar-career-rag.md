# Jorge Pulgar — Career & Project Documentation

> **Purpose of this document.** This is the human/career layer of a knowledge base used by a chatbot that lets recruiters ask about Jorge Pulgar's profile and projects. It covers what the code and repo docs can't: Jorge's role on each project, outcomes and impact, and recruiter-facing summaries of each project's stack. It is meant to be ingested into a RAG system alongside repository documentation and source code.
>
> **How to read it.** Each section is written to stand on its own so it retrieves cleanly as an isolated chunk. Project names and "Jorge" are repeated intentionally.

---

## Profile summary

Jorge Pulgar is a Junior AI Engineer based in Madrid, Spain. He builds applied AI systems with a focus on Retrieval-Augmented Generation (RAG), LLM application development, and machine learning on the Azure stack. His work spans the full path from data and model to a working product: backend APIs (Python / FastAPI), frontends (React / TypeScript), and cloud AI services (Azure AI Foundry, Azure AI Search, Azure OpenAI, Azure Document Intelligence).

He pairs hands-on engineering with four Microsoft Azure certifications and a strong, self-directed portfolio. His strengths are RAG architecture, retrieval quality, anti-hallucination / citation integrity, LLM integration, turning ML models into deployed demos, and shipping end-to-end. He is early in his career (one professional internship plus a real client capstone and an extensive independent portfolio), and he is honest about that level rather than inflating it.

Jorge works in Spanish day to day and writes all of his professional and technical materials in English (every repository is documented in English with bilingual READMEs). He is direct, gives and takes feedback well, and prefers concise communication.

**Full name:** Jorge Pulgar (not "García" — a common misspelling to avoid).
**Location:** Madrid, Spain.

---

## Availability & target roles

Jorge is based in Madrid, Spain, and is open to Junior AI Engineer / AI Application Developer / ML Engineer roles across Europe. He works with remote-EU roles and is open to relocation for the right opportunity.

---

## Professional experience

### Datarmony — AI Application Developer (Internship), Mar–Jun 2025

At Datarmony, Jorge worked as an AI Application Developer on a 3-person Agile team. He built a financial document analysis application that used an LLM to analyse the documents being processed.

- **Role:** Jorge built the **entire backend**, including the integration with the **Google Gemini API** that runs the LLM analysis on the documents the app sends. This was his ownership end of the project.
- **Stack (recruiter language):** Python backend; Google Cloud Platform; Google Gemini API (LLM); document analysis / information extraction.
- **Why it mattered:** Jorge's first professional engineering experience and his entry point into production LLM application work — inside a real Agile delivery process with a team.
- **Outcome / impact:** The application was used internally at Datarmony. The company's intention was to use it with clients as well; Jorge cannot confirm whether that client-facing use was realised.

---

## Education

- **"Máster en IA e Ingeniería de Datos" — Tajamar (Madrid), Sep 2025 – Jun 2026.** An intensive private professional specialization program in AI and Data Engineering. **Framing note: this is a private professional program, not an accredited university degree, and should not be described in English as an "MSc" or "Master of Science."** Jorge's final project for the program (TFM — *Trabajo Fin de Máster*) is **LicitAI** (see Featured projects).
- **Grado Superior in Web Application Development — IES Pío Baroja (Madrid), 2023–2025.** Spain's higher vocational qualification in web application development, covering full-stack web fundamentals.

---

## Certifications

Jorge holds four Microsoft Azure certifications:

- **AI-102 — Azure AI Engineer Associate.** Designing and implementing AI solutions on Azure (Azure AI services, generative AI, knowledge mining).
- **DP-100 — Azure Data Scientist Associate.** Designing and running data science / ML workloads on Azure Machine Learning.
- **DP-300 — Azure Database Administrator Associate.** Administering Azure SQL database solutions.
- **DP-900 — Azure Data Fundamentals.** Core data concepts on Azure.

He also holds a **Cambridge English certification at C1 level** (see Languages).

---

## Technical skills (recruiter language)

- **AI / LLM:** Retrieval-Augmented Generation (RAG) architecture; retrieval quality engineering; anti-hallucination / citation integrity; LLM application development; agentic systems and multi-agent orchestration, including LangGraph (compiled sub-graphs, human-in-the-loop interrupts, map-reduce / `Send` fan-out, intent routing); prompt engineering; LLM fine-tuning; structured extraction from documents; vector and hybrid search; semantic reranking; query rewriting.
- **Azure AI stack:** Azure OpenAI (gpt-4o / gpt-4o-mini, text-embedding-3-small), Azure AI Search (hybrid + HNSW vector search), Azure Document Intelligence (OCR), Azure AI Foundry, Azure Machine Learning, Azure Blob Storage, Azure Key Vault, Azure Application Insights.
- **Machine learning:** unsupervised anomaly detection (autoencoders), gradient-boosted classifiers (LightGBM), CNNs, model evaluation (PR-AUC and other metrics), ONNX runtime for in-browser inference.
- **Backend:** Python, FastAPI, Pydantic v2, SQLAlchemy, REST APIs, JWT auth (bcrypt), SQLite / PostgreSQL.
- **Frontend:** React 18, Vite, TypeScript, Tailwind, Next.js, HTML/CSS/JS.
- **Other LLM platforms:** Google Gemini API, OpenAI GPT-4o / GPT-4o-mini.
- **Privacy / compliance engineering:** PII anonymization with Microsoft Presidio for GDPR-safe pipelines; secrets management via Key Vault.
- **Ways of working:** Agile / Scrum, Conventional Commits, code review, Architecture Decision Records (ADRs), automated testing, GitHub Actions (CI / scheduling), AI-assisted development with Claude Code.
- **Languages:** Spanish (native); English (C1, Cambridge English certified — all technical documentation written in English).

---

## Featured projects

### LicitAI — AI RAG platform for analysing Spanish public tenders (client capstone / TFM)

**LicitAI** is an AI-powered RAG platform that analyses Spanish public procurement tenders (*licitaciones*). A user uploads the tender documents (pliegos — typically a PCAP and a PPT), and the system runs them through OCR → chunking → embedding → indexing, then lets the user **query the tender and get answers with real citations**, plus summaries and a fit/match score. It is dual-purpose: it is both Jorge Pulgar's **final project (TFM)** for the Tajamar program and a **real product built for the company Integra Tecnología**, developed in a team of three (with teammates Álvaro and Siro) under a Scrum process with weekly stakeholder check-ins.

**Stack (recruiter language):** Python / FastAPI backend with Pydantic v2 and SQLAlchemy; React 18 + Vite + TypeScript + Tailwind frontend; Azure for all AI — Azure OpenAI (gpt-4o-mini for generation, text-embedding-3-small for embeddings), Azure Document Intelligence (OCR), Azure AI Search (hybrid + HNSW vector search), Azure Blob Storage, Azure Key Vault, Azure Application Insights.

**Jorge's contribution (he owned the backend spine and several of the hardest parts):**

- **Core backend and the first working RAG slice.** Jorge built the first end-to-end backend slice that made the product actually work: authentication (JWT with bcrypt), the RAG query service, the summary service, and the match-score service — the spine of the app (log in → ask a question about a pliego → get an answer, a summary, and a fit score). He owned this because it is the highest-risk, highest-value part: if the query/answer loop doesn't work, nothing else matters.
- **The Licitación data-model re-architecture.** Jorge introduced the `Licitacion` entity and reworked RAG to be multi-document. A real licitación bundles several documents (a PCAP, a PPT, possibly multiple *lotes*), so he restructured the model so a licitación owns many pliegos, and made the RAG layer search across all of them while still filtering by user and by licitación. This was a root-cause fix to a wrong data model rather than a patch, and it touched domain models, ingestion, indexing, the pipeline, and the query service at once.
- **Ingestion / OCR / indexing pipeline (co-author; lead on OCR and RAG quality).** Teammate Álvaro laid down first implementations; Jorge was the second major hand across all of it and the primary author on OCR specifically. He made the pipeline aware of the multi-document model and improved retrieval quality. When answers came back with gaps, he **root-caused the problem to infrastructure**: the Azure Document Intelligence resource was on the F0 (free) tier, which silently limited processing so pages were lost before chunking. He documented the F0→S0 finding as the true root cause and added a diagnostic script — a good example of "understand why it fails before touching code."
- **Citation integrity (anti-hallucination).** In public procurement a hallucinated number or wrong page reference can cause a bad bid or a missed deadline, so Jorge made the answers trustworthy: citation validation now uses the real OCR page count (so the system can't cite a page that doesn't exist), and answers cite only the chunks actually used rather than dumping every retrieved chunk as a "source." Every LicitAI citation is therefore both real and relevant.
- **Observability and secrets.** Jorge wired the backend into Azure Application Insights so production failures are visible, loading the connection string from Azure Key Vault rather than hardcoding it — handling both "can we see what's breaking" and "we don't leak secrets."
- **Memoria Técnica — his flagship feature (technical-proposal generator).** Jorge's biggest single piece of ownership: a feature that takes the PPT (the technical-requirements pliego) and produces a draft *propuesta técnica* — the document a bidding company would actually submit. He built it backend-first in layers (data models → service/prompt/endpoint skeleton → full flow): generate an outline, generate the proposal, let the user refine it through a markdown chat, and export to PDF, with the design decisions captured in ADRs. The most advanced piece is a **multi-agent fan-out**: instead of one model call writing the whole proposal, sections are generated in parallel by separate agent calls and then assembled — which both raises quality (section-scoped generation stays focused instead of drifting) and cuts latency.

**Why it mattered:** A real client problem (making dense public tender documents searchable, citable, and actionable), a real team, a real delivery cadence — the closest thing in Jorge's portfolio to professional product work, and the project where his anti-hallucination and retrieval-quality work shows most.

**Outcome / impact:** Not yet measurable — the product has not yet been handed over to Integra, so there is no adoption data to report.

---

### RAG Assistants Platform — multi-assistant RAG platform (flagship personal project)

**RAG Assistants Platform** is Jorge Pulgar's flagship personal project: a platform for creating and running multiple isolated RAG assistants, each with its own knowledge base.

- **Jorge's role:** Sole author — designed and built the full system (backend, retrieval, frontend) in roughly 7 days using Claude Code as a development accelerator.
- **What he built / engineering highlights:** Structural isolation with **one search index per assistant** (so assistants can't leak each other's data); **query rewriting** to improve retrieval; **hybrid search plus a semantic reranker** for relevance. Roughly 4,000 lines of code with 56 tests.
- **Stack (recruiter language):** Azure AI Foundry, Azure AI Search (vector + hybrid + semantic reranking), Python / FastAPI backend, React + TypeScript frontend.
- **Why it mattered:** Demonstrates Jorge's depth in production-style RAG architecture — multi-tenant isolation, retrieval-quality engineering, and a tested, full-stack build.
- **Outcome / impact:** Portfolio / demonstration project (no external users claimed); the value is the architecture and engineering quality.

---

### Fraud Detection Autoencoder (`fraud-autoencoder`) — unsupervised anomaly detection

**Fraud Detection Autoencoder** is a machine learning project by Jorge Pulgar that detects fraudulent transactions using an unsupervised autoencoder for anomaly detection. It is one of his strongest individual pieces for ML depth.

- **Jorge's role:** Sole author — data, model, evaluation, and demo.
- **What he built / engineering highlights:** An autoencoder trained to reconstruct normal transactions, flagging anomalies by reconstruction error; evaluated with **PR-AUC ≈ 0.37** and benchmarked against baselines; ships with an **in-browser demo running via ONNX** so the model can be tried without a server.
- **Stack (recruiter language):** Unsupervised deep learning (autoencoder), Python ML tooling, PR-AUC evaluation on imbalanced data, ONNX runtime for client-side inference.
- **Why it mattered:** Shows correct handling of a hard, imbalanced ML problem, honest metric-based evaluation against baselines, and the ability to ship a model as a usable demo.
- **Outcome / impact:** Portfolio project; the headline is a working, benchmarked anomaly detector with a live browser demo.

---

### Invoice Insights (`ai-invoice-analyzer`) — invoice data extraction (SaaS-style)

**Invoice Insights** (`ai-invoice-analyzer`) is a full-stack SaaS application by Jorge Pulgar, built with one teammate, aimed at freelancers and small businesses (autónomos and pymes) in Spain. It extracts tax/fiscal data from invoice PDFs using generative AI and presents a financial dashboard (KPIs, monthly evolution, top clients/suppliers, quarterly VAT).

- **Jorge's role:** Jorge built the **entire backend** — the Azure AI Foundry (GPT-4o) structured-extraction integration, the JSON validation, the Express + SQLite API, authentication (JWT / bcrypt), and PDF handling. His teammate built the React / TypeScript frontend and dashboard.
- **What it does / engineering highlights:** A user uploads an invoice PDF; the backend extracts the text (including multi-page PDFs) and makes a **single Azure AI Foundry (GPT-4o) call that returns only structured JSON** (invoice number, date, taxable base, VAT/IRPF amounts, total, type). The backend then **validates that JSON** (date format, ISO currency code, totals coherence), persists it, and the frontend renders the dashboard, with VAT/IRPF computed from the extracted fields. A **draft/confirm review flow** lets the user check extractions before they are saved. By design it uses **generative-AI extraction plus deterministic backend logic — no agents / multi-agent system** (an explicit course constraint). Privacy-by-design: the uploaded PDF is deleted from disk after extraction (GDPR).
- **Stack (recruiter language):** Node.js (≥20) + Express backend with SQLite (`better-sqlite3`), JWT auth (bcrypt), file upload (multer), PDF parsing (pdfjs-dist); React + TypeScript (Vite) frontend with Tailwind and Chart.js; Azure AI Foundry (GPT-4o) for structured JSON extraction.
- **Why it mattered:** A practical, business-facing use of generative AI (document → validated structured data → financial insights), packaged as a real product with authentication, persistence, and a dashboard.
- **Outcome / impact:** Course / portfolio project; runs locally end to end (no public deployment recorded).

---

### ClarityBank (`clarity-bank`) — two-level transaction categorisation (course project)

**ClarityBank** is a transaction-categorisation system by Jorge Pulgar, built as a specialization-program course project (note: this is **not** his TFM — LicitAI is). It classifies bank transactions in two levels, combining a classical ML model with an LLM fallback for accuracy and cost control.

- **Jorge's role:** Jorge owned the **API, the PII anonymization, the anomaly detection, and the insights** components. His teammate trained the machine learning model.
- **What he built / engineering highlights:** A two-level pipeline — **Level 1** a LightGBM classifier (91.2% accuracy) handles easy cases; **Level 2** escalates only uncertain cases to an Azure OpenAI LLM, reaching **96.1% combined accuracy** with a **15.83% escalation rate**. He made it **GDPR-safe by anonymising PII with Microsoft Presidio** before any data reaches the LLM, and analysed cost at scale (~€222/month total at a 340k-user scale). Roughly 3,479 lines of code with 55 tests.
- **Stack (recruiter language):** Python / FastAPI backend, Streamlit interface, LightGBM, Azure OpenAI, Microsoft Presidio (PII anonymization).
- **Why it mattered:** A genuinely thoughtful systems-design project — escalating only hard cases to the expensive model keeps accuracy high while controlling cost, and the Presidio anonymization shows privacy-by-design thinking.
- **Outcome / impact:** Course project; headline results are the accuracy/cost trade-off (96.1% combined, 15.83% escalation, ~€222/month at 340k users) and a tested full-stack delivery.

---

### Sales Receptivity CNN (`sales-receptivity-cnn`) — emotion recognition

**Sales Receptivity CNN** is a computer-vision project by Jorge Pulgar that uses a convolutional neural network (CNN) to recognise emotions, framed around sales receptivity.

- **Jorge's role:** Sole author.
- **What he built:** A CNN-based emotion classifier with a **live web demo**.
- **Stack (recruiter language):** Convolutional neural network (deep learning, computer vision), deployed as a live web demo.
- **Why it mattered:** Rounds out his ML range into computer vision, and again shows the habit of shipping a model as a usable demo.
- **Outcome / impact:** Portfolio project with a working live demo.

---

### FinBot — LLM fine-tuning (with honest overfitting analysis)

**FinBot** is a project by Jorge Pulgar in which he fine-tuned an LLM (GPT-4o-mini) for a finance-oriented task.

- **Jorge's role:** Sole author.
- **What he built / engineering highlights:** A fine-tuning workflow on GPT-4o-mini, including a **documented overfitting analysis** — Jorge explicitly recorded where the model overfit rather than hiding it.
- **Stack (recruiter language):** LLM fine-tuning (OpenAI GPT-4o-mini), evaluation of training dynamics.
- **Why it mattered:** Shows he understands fine-tuning as an engineering process with failure modes, and documents negative findings honestly.
- **Outcome / impact:** Learning/portfolio project; the value is the documented, honest analysis.

---

### Multi-Agent Job Application System — personal multi-agent pipeline

**Multi-Agent Job Application System** is a personal automation project by Jorge Pulgar: a multi-agent pipeline that scrapes job offers daily, filters them against his profile, and drafts applications for human review.

- **Jorge's role:** Sole author / architect.
- **What he built / engineering highlights:** An **orchestrator plus specialised agents** that scrape postings, filter by fit, and generate application drafts; a **human-in-the-loop** design where nothing is sent automatically — every draft is reviewed by a person via a dashboard. Scheduling via GitHub Actions; data in SQLite; review UI in Next.js.
- **Stack (recruiter language):** Multi-agent LLM architecture (orchestrator + specialised agents), Azure OpenAI (GPT-4o + GPT-4o-mini), GitHub Actions, SQLite, Next.js dashboard. Jorge is introducing **LangGraph** to orchestrate parts of the pipeline.
- **Why it mattered:** Demonstrates agentic system design and responsible automation with a human approval gate.
- **Outcome / impact:** Personal tooling / portfolio project demonstrating multi-agent design.

---

### Interview Research Agent (`interview-preparation-agent`) — LangGraph agent with human-in-the-loop

**Interview Research Agent** is a LangGraph agent by Jorge Pulgar that researches a company before an interview and produces a Markdown briefing. Given a company name, it runs parallel research on what the company does, its recent news, and its real tech stack, generates three specific interview questions, and assembles a briefing — pausing for human review at each key step.

- **Jorge's role:** Sole author.
- **What he built / engineering highlights (real LangGraph depth):**
  - **Human-in-the-loop via `interrupt()`** — the graph pauses so a person can approve the generated questions and the final briefing, request a wording edit, or send it back to search the web again for fresh data. Generation and review are deliberately split into separate nodes, so that resuming after a pause does not re-run the LLM and regenerate everything.
  - **Intent-routed feedback** — an LLM classifier decides whether the user's feedback is a cheap rewrite (`edit`) or a request to re-search (`research` / `tech_stack`), and routes accordingly.
  - **Compiled sub-graphs** — `research`, `tech_stack`, and `briefing` are each compiled graphs used as nodes inside a parent graph; they communicate through shared state keys and inherit the parent's checkpointer, so an `interrupt()` inside a sub-graph bubbles up correctly. Each declares an `output_schema` to avoid write collisions when running concurrently.
  - **Map-reduce parallelism with `Send`** — each research sub-graph fans its web searches out in parallel (MAP via `Send`), fans them back in through a reducer channel that concatenates results, then a single `synthesize` node summarises with the LLM. This gives **two levels of parallelism**: the research and tech-stack sub-graphs run concurrently, and each runs its three searches concurrently.
  - **Verifiability** — an `inspect_run.py` harness streams the graph with `subgraphs=True` to prove the sub-graphs and the map-reduce fan-out actually executed in parallel, rather than just producing a plausible-looking output.
- **Stack (recruiter language):** Python; LangGraph (compiled sub-graphs, `interrupt()` human-in-the-loop, `Send` map-reduce fan-out, conditional/intent routing, `MemorySaver` checkpointer); Azure OpenAI / Azure AI Foundry (gpt-4o) as the model; Tavily for web search.
- **Why it mattered:** This is Jorge's deliberate, real-depth LangGraph project — it exercises the framework's harder features (sub-graphs, interrupts, map-reduce fan-out, conditional routing) rather than a toy single-chain agent, and keeps a human approval gate on every output.
- **Outcome / impact:** Personal mini-project demonstrating production-style LangGraph patterns.

---

### Fleet — Claude Code "AI Layer" reference implementation (`Large-Codebases-AI-Layer`)

**Fleet** is a project by Jorge Pulgar: a concrete, runnable reference implementation of the patterns in Anthropic's article *"How Claude Code works in large codebases."* The article explains how to build an effective "harness" around an AI coding assistant but shows no code — Fleet is that harness, built from scratch on a real Python monorepo with every component validated end to end. The app itself (a B2B field-service platform managing jobs, technicians, and clients across 5 services and 2 shared packages) is deliberately just realistic scaffolding; the value is the AI Layer built around it.

- **Jorge's role:** Sole author. Original code; he credits Anthropic's article for the patterns and Cole Medin's "helpline" repo as a structural reference.
- **What he built / engineering highlights — the six AI-Layer extension points:**
  - **Hierarchical `CLAUDE.md` files** — a deliberately lean root file plus per-service / per-package files that load only in their own directory (e.g. the billing money-rules load when editing billing).
  - **Hooks** — a `SessionStart` hook that orients the assistant from `git status`, and a self-improving `Stop` hook that, after each turn, spawns a background process to propose edits to the `CLAUDE.md` files so they don't rot, protected by a recursion guard.
  - **Path-scoped skills** — instruction files that auto-activate by directory (billing money rules, API route-adding steps, scoped-test selection) using progressive disclosure.
  - **Read-only explorer subagent** — a subagent restricted to `Read` / `Grep` / `Glob` (no write/edit) that maps unfamiliar code before edits, preserving the main agent's context.
  - **AST-based codebase-search MCP server** — exposes `where_is`, `find_references`, and `outline` by parsing the Python AST, giving precise navigation that grep can't (no false hits from comments or strings).
  - **Distributable plugin** — bundles the portable pieces into a one-command install so a new engineer gets the full baseline on day one.
- **Validation:** a suite (`validate_all.py`) checks 13 things end to end — the CLAUDE.md hierarchy, both hooks, all three skills, the read-only subagent, the language-server handshake, the MCP server's tool calls, and the plugin bundle — and writes a `VALIDATION.md` report each run.
- **Stack (recruiter language):** Python monorepo (managed with `uv`), `pytest`, `pyright` language server, Model Context Protocol (MCP) server, and the full set of Claude Code extension points (CLAUDE.md, hooks, skills, subagents, plugins).
- **Why it mattered:** Shows Jorge doesn't just use AI dev tools ad hoc — he engineers the tooling/harness around them at a systems level and validates it end to end. A strong signal of AI-assisted-engineering maturity.
- **Outcome / impact:** Open-source reference / methodology project; the deliverable is a fully validated, reusable AI Layer.

---

## How Jorge works

- **End-to-end builder.** Comfortable across the stack — data and models, Python/FastAPI backends, React/TypeScript frontends, and Azure cloud AI services — so he can take a project from idea to working product.
- **RAG and retrieval-quality specialist.** His deepest area is making retrieval *trustworthy*: hybrid search, reranking, query rewriting, multi-tenant isolation, and citation integrity (answers that cite only real, used sources).
- **Root-cause engineer.** He fixes causes, not symptoms — e.g. tracing missing answers in LicitAI to an Azure Document Intelligence free-tier limit rather than papering over it with retrieval tweaks.
- **Honest and rigorous.** He documents negative results (the FinBot overfitting analysis; a separate experiment where a neural network underperformed plain linear regression on a small dataset, which he kept and documented). His project claims can be trusted.
- **Tests and process.** His larger projects ship with real test suites (56 tests, 55 tests), ADRs, Conventional Commits, code review, and Agile/Scrum where teams are involved.
- **Bilingual delivery.** Works in Spanish, documents everything in English; every repo has bilingual READMEs.
- **Direct communicator.** Concise, gives and receives feedback, pushes back when he disagrees.

---

## Common recruiter questions (FAQ)

**Q: What is Jorge's strongest area?**
Applied RAG and LLM application engineering on Azure — building retrieval systems with hybrid search, reranking, query rewriting, multi-tenant isolation, and real citation integrity, then shipping them as full-stack apps.

**Q: What's his single best project to look at?**
For real client/team delivery and anti-hallucination depth, **LicitAI** (his TFM, built for Integra Tecnología). For RAG architecture on a personal build, the **RAG Assistants Platform**. For machine-learning depth, the **Fraud Detection Autoencoder**.

**Q: Does Jorge have professional experience?**
Yes — a 2025 internship at Datarmony as an AI Application Developer, where he built the entire backend (including the Gemini API LLM integration) for a financial document analysis app on a 3-person Agile team. He also delivered LicitAI as a real client project for Integra Tecnología. He is early-career; much of his depth beyond that comes from an extensive, rigorously documented personal portfolio.

**Q: Is he junior or mid-level?**
Junior. He has strong project depth for his level but is honest about being early in his career.

**Q: Does he have a university degree?**
He completed a Grado Superior (higher vocational qualification) in Web Application Development, and is completing a private AI & Data Engineering specialization program at Tajamar. That program is a private professional program, not an accredited university degree.

**Q: What's his experience with RAG specifically?**
Substantial for a junior: a flagship multi-assistant RAG platform (per-assistant index isolation, hybrid search, semantic reranking, query rewriting), and LicitAI, where he owned the RAG query service, the multi-document re-architecture, OCR/retrieval quality, and citation integrity over Spanish procurement documents.

**Q: Has he worked in teams and with Agile?**
Yes — the Datarmony internship and the LicitAI capstone were both team projects with Agile/Scrum, code review, ADRs, and Conventional Commits.

**Q: What cloud and certifications does he have?**
Azure-first, with four Microsoft certifications: AI-102 (AI Engineer Associate), DP-100 (Data Scientist Associate), DP-300 (Database Administrator Associate), DP-900 (Data Fundamentals).

**Q: What languages does he speak?**
Spanish (native) and English at C1 level, certified by Cambridge English. All of his technical documentation is written in English.

**Q: What's his experience with LangGraph and agents?**
He builds agentic systems and has real LangGraph depth, not just surface familiarity. His **Interview Research Agent** uses compiled sub-graphs, human-in-the-loop `interrupt()` pauses, `Send`-based map-reduce fan-out with two levels of parallelism, and intent-routed feedback. He also designed a multi-agent job-application pipeline (orchestrator + specialised agents, human approval gate) and is introducing LangGraph to orchestrate parts of it, and used a multi-agent fan-out for proposal generation in LicitAI.

**Q: Where is he based and is he open to relocating?**
Based in Madrid, Spain. He works with remote-EU roles and is open to relocation for the right opportunity.

---

## Contact

- **Email:** jorgepulgar.ai@gmail.com
- **LinkedIn:** https://www.linkedin.com/in/jorgepulgar
- **GitHub:** github.com/JorgePulgar
