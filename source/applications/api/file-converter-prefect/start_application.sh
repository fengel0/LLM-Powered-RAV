export LOG_LEVEL=info
export LOG_SECRETS=True

export POSTGRES_HOST="127.0.0.1"
export POSTGRES_PORT="5432"
export POSTGRES_DATABASE="production-db"
export POSTGRES_USER="root"
export POSTGRES_PASSWORD="password"

export S3_HOST=127.0.0.1:9000
export S3_ACCESS_KEY=root
export S3_SECRET_KEY=password
export S3_SESSION_KEY=
export S3_IS_SECURE=false


#export SYSTEM_PROMPT=$'Du bist „DocVision-Beschreiber“, ein Spezialist für präzise, objektive Bildbeschreibungen von Abbildungen, die aus größeren Dokumenten (PDFs, Präsentationsfolien, Forschungsarbeiten, gescannte Seiten usw.) extrahiert wurden.\n\nFür jede Anfrage erhältst du:\n• ein BILD aus dem Dokument\n• den UMGEBUNGSTEXT, der im Ursprungsdokument direkt vor und/oder nach dem Bild stand (nur als Kontext)\n\nDeine Aufgabe:\n1. Gib eine lebendige, in sich geschlossene Beschreibung dessen, was im BILD visuell vorhanden ist.\n2. Beginne mit einer Ein-Satz-Zusammenfassung (≤ 25 Wörter), damit der Leser sofort den Kern versteht.\n3. Folge mit detaillierten Angaben und beschreibe, wo zutreffend:\n   – Bildtyp (Foto, Diagramm, Tabelle, Grafik, Screenshot, Illustration usw.)\n   – Haupt-Bildelemente, ihre Positionen und räumlichen Beziehungen\n   – sichtbaren Text im Bild (Beschriftungen, Achsentitel, Legenden, Überschriften)\n   – Farben, Formen, Muster, Texturen, Perspektive, Beleuchtung, künstlerisches Medium oder Stil\n   – Anzahl und Eigenschaften von Personen, Objekten, Symbolen & Icons; Gesten oder Emotionen\n   – bei Daten­grafiken: Variablen, Einheiten, Skalen, Trends, Ausreißer, besondere Annotationen\n4. Nutze den UMGEBUNGSTEXT nur, um mehrdeutige Elemente oder Abkürzungen im BILD zu klären.\n   • Gib diesen Text **nicht** wörtlich wieder und paraphrasiere ihn nicht ausführlich.\n5. Bleibe neutral und sachlich; schreibe im Präsens; vermeide Spekulationen über nicht Sichtbares.\n6. Gib reine deutsche Prosa ohne Markdown, Metadaten oder zusätzliche Kommentare aus – nur die Beschreibung.'
#export PROMPT=$'--- UMGEBUNGSTEXT (Kontext zum Bild) ---\nDer folgende Ausschnitt stammt aus dem ursprünglichen Dokument und steht unmittelbar vor bzw. nach der Abbildung. Nutze ihn ausschließlich, um unklare Elemente des Bildes zu verstehen oder Abkürzungen aufzulösen. Gib diesen Text weder wörtlich wieder noch paraphrasiere ihn ausführlich.\n'

export OLLAMA_TIMEOUT=6000
export OLLAMA_HOST="http://we.ai.fh-erfurt.de:20000"
export OLLAMA_MODEL="gemma3:4b"

export FILE_CONVERTER_API="http://127.0.0.1:1234"

export OTEL_HOST="127.0.0.1:4317"
export OTEL_ENABLED=true
export OTEL_INSECURE=true

#export PREFECT_API_URL=http://10.0.0.50:4200/api
export PREFECT_API_URL=https://prefrect.home-vtr4v3n.de/api
#export PREFECT_API_URL=http://10.0.0.205:4200/api


python src/file_converter_prefect/main.py
