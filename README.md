# LLM-powered-RAV (RAG Assessment & Validation)

Retrieval‑Augmented Generation (RAG) hat sich zum De‑facto‑Standard entwickelt, um das Reasoning großer Sprachmodelle mit externem Wissen zu verbinden.
Dennoch liefern RAG‑Systeme häufig zwar faktisch korrekte, aber **unvollständige** Antworten, in denen etwa beteiligte Akteure (*Welche Forschenden waren beteiligt?*) oder Mengenangaben (*Wie viele Grabungen fanden statt?*) fehlen.
Ziel dieser Arbeit ist es, drei komplementäre Verfahren zur Maximierung der **Antwort­vollständigkeit** zu entwickeln und in heterogenen Domänen – von archäologischen Berichten bis hin zu firmeneigenen Entwickler­dokumentationen / DSL‑Handbüchern – systematisch zu vergleichen.

---

Dies Projekt implementiert ein Pipline basierte RAG Evaluation basierend auf den Metriken, Recall, Precision, F1-Score und Korrektheit.
Dafür können verschiedene LLM Richter als Basis verwendet werden.
Aktuell implementierte RAG Systeme sind
- Hybrid RAG
- SubQuestion RAG
- HippoRAGv2

---

### Forschungsziele

1. **Antwort­vollständigkeit definieren und operationalisieren** – insbesondere für entitäts‑ und mengen­orientierte Fragen.
2. **Drei RAG‑Varianten konzipieren und implementieren** – Graph‑RAG, Sub‑Question Decomposition RAG und Program‑of‑Thought (PoT) RAG – die den Recall auf jeweils unterschiedliche Weise maximieren.
3. **Die Varianten quantitativ vergleichen** in Bezug auf Recall, Präzision, numerische Genauigkeit, Konsistenz und Latenz und daraus ableiten, wann sich der Mehraufwand für Graph‑RAG lohnt.

#### Sekundär Ziele
- Das System soll eine technische Übersicht über die Vorgangsunterlagen erstellen, einschließlich:
    - Anzahl und Struktur der Dokumente (Textdateien, Bilder, andere Binärdateien wie CAD, GIS)
	- Zeichenumfang bei Textdateien (ohne Stoppworte)
	- Erkennung von "leeren" oder nicht lesbaren Text-Dateien
	- Erkennung von Dopplungen (z.B. gleiche Inhalte sowohl als Word- als auch PDF-Datei)
---

### Ansatz A – Graph‑RAG

Graph‑RAG erweitert die Retrieval‑Phase um ein Wissensgraph‑Modell. Knoten und Kanten liefern eine explizite Aufzählung relevanter Entitäten; Traversierungen per Cypher oder SPARQL können somit garantieren, dass *alle* Personen, Grabungen, Funktionen oder Klassen gefunden werden, die einer Anfrage entsprechen. Microsofts Open‑Source‑GraphRAG zeigt zweistellige Recall‑Steigerungen bei Multi‑Entity‑Fragen. In dieser Arbeit werden (i) ein schlanker Wissensgraph (etwa ein Wikidata‑Ausschnitt oder eine DSL‑Symbol­tabelle) erstellt / wiederverwendet, (ii) ein Graph‑Retriever implementiert, der Tripel plus unterstützende Textsnippets liefert, und (iii) Graph‑ und Texttreffer vor der Generierung fusioniert.

### Ansatz B – Sub‑Question Decomposition

Aktuelle Arbeiten zur *Sub‑Question Coverage* zerlegen komplexe Anfragen in atomare Teilfragen und rufen für jede Facette Evidenz ab. Ein GPT‑4‑Turbo‑Prompt generiert die Zerlegung; die Retrieval‑Ergebnisse werden parallel eingeholt, dedupliziert und anschließend zu einer vollständigen Antwort samt Zitaten zusammengeführt.

### Ansatz C – Naive RAg

Program‑of‑Thought‑Prompts lassen das LLM ein kurzes Python‑Skript erzeugen, das numerische Ergebnisse aus den gefundenen Snippets berechnet und Chain‑of‑Thought um etwa 12 % übertrifft. Eine Ausführungs­umgebung samt „Calculator‑Tool“ stellt sicher, dass Zählungen (*„23 Grabungen“*) oder abgeleitete Kennzahlen exakt und nachvollziehbar sind.

---

### Versuchsdesign

| Variante          | Retrieval‑Ebene          | Reasoning‑Ebene                  | Validierung                 |
| ------------------| ------------------------ | -------------------------------- | --------------------------- |
| **Baseline**      | Dense + BM25 Top‑k       | Direkte Generierung              | –                           |
| **HippoRAG2‑RAG** | KG‑Traversal + Dense     | Direkte Generierung              | Graph/Text‑Konsistenz‑Check |
| **Decomp‑RAG**    | Dense Top‑k je Teilfrage | Zusammenführen der Sub‑Antworten | Coverage‑Estimator          |

---

### Geeignete Evaluations­datensätze

1. **RAGEval* / Dragonball Dataset
2. **When to Use Graphs in RAG A Comprehensive Analysis for Graph Retrieval-Augmented Generation** / Dragonball Dataset
2.1. Medical-Dataset
2.2. Noval-Dataset

Jeder Datensatz wird im Verhältnis 70 / 30 in Entwicklungs‑ und Blind‑Test‑Split aufgeteilt. Zielmetrik: **Answer Recall** (+ 20 Prozent­punkte gegenüber Baseline) bei höchstens 5 Prozent­punkten Precision‑Verlust, **Numeric‑F1** ≥ 0,9, **Consistency** ≥ 95 % und **Latenz** < 2 × Baseline. Signifikanz­tests erfolgen über Bootstrapping und gepaarte t‑Tests.

---

### Erwartete Beiträge

* Eine modulare Open‑Source‑RAG‑Plattform mit austauschbaren Graph‑, Decomposition‑ und PoT‑Bausteinen.
* Eine empirische Gegenüberstellung, die zeigt, wann Graph‑Strukturen messbare Vollständigkeits­gewinne gegenüber Prompt‑Engineering bringen.
* Ein reproduzierbares Benchmark‑Framework und Reporting‑Template für künftige RAG‑Vollständigkeits­studien.

Durch die Kombination von **strukturiertem Retrieval (Graph‑RAG)**, **logischer Zerlegung** und **ausführbarem Reasoning** setzt die Arbeit einen neuen Maßstab für verlässliche, vollständig aufgelistete Antworten in wissenskritischen Anwendungen.

---

### Projektstruktur

---

source/
Der Hauptquellcode der Anwendung.
Enthält alle zentralen Komponenten, die für die Entwicklung und den Betrieb der Anwendung notwendig sind.
- applications/ – Einstiegspunkt der Applikation, inkl. Dockerfile, API-Definitionen und Startskripte.
- api/ – Implementierung der API-Endpunkte.
- lib/ – Zentrale Bibliotheken und Hilfsfunktionen.
- services/ – Backend-Services und Anwendungslogik.
- README.md – Dokumentation zur Applikationsarchitektur.
- start_sonar.sh – Skript zur statischen Codeanalyse.
- pyproject.toml / uv.lock – Python-Umgebungsdefinition und Abhängigkeiten.

---

deployment/
Alle Konfigurations- und Infrastrukturdateien für das Deployment der Anwendung.
- YAML-Dateien für verschiedene Komponenten (ai.yaml, api.yaml, rag_instances.yaml, etc.).
- config/ – Umgebungs- und Systemkonfigurationen.
- prompts/ – Definitionen von Prompt-Vorlagen.
- start.sh / stop.sh – Start- und Stop-Skripte für den Deploymentsprozess.
- README.md – Separate Dokumentation zur Infrastruktur und den Services.

---

evaluation_data/

Datengrundlage und Ergebnisse der Evaluationsprozesse.
- datasets/ – Ursprüngliche Datensätze.
- datasets_question/ – Fragebasierte Datensätze zur Evaluation.
- evaluation_results/ – Ausgabedaten, Statistiken und Analyseergebnisse der Evaluationsläufe.

---

small_scripts/

Sammlung von Hilfs-, Analyse- und Visualisierungsskripten, die zur Evaluation, Datenaufbereitung oder Ergebnisauswertung dienen.
Unterteilt in mehrere Funktionsbereiche:
- embedding_times/ – Skripte und CSVs zur Laufzeitmessung von Embedding-Prozessen. Enthält z. B. prefect_times.py und verschiedene Messdateien.
- graphrag_bench/ – extract_txt.py zur Extraktion von Texten für Benchmarking.
- manual_eval/ – Skripte zum generieren des Recalls basierend auf der Manuellen Bewertung
- visual/ – Tools zur Visualisierung von Evaluationsdaten (z. B. recall_diagram.py, Diagramme und Histogramme).
- web-scraper/ – Ein Scrapy-basiertes Modul zur automatisierten Datenerfassung der ai.fh-erfurt.de und fh-erfurt.de

