# Webscraper  
Scrapy-Based Crawler for Collecting Documentation Pages

This project contains a Scrapy crawler called **`docs`** that extracts structured information from documentation pages and outputs them as items for further processing. The project follows the standard Scrapy layout and includes item definitions, pipelines, and project configuration.

---

## Features

- A Scrapy spider (`docs.py`) that crawls target documentation pages.
- An item class defining all extracted fields.
- A pipeline system that processes scraped items (cleaning, storing, exporting).
- A ready-to-run startup script.
- Python packaging via `pyproject.toml`.

---

## Project Structure

.
├── scrapy.cfg
├── start_application.sh
├── webscraper/
│   ├── items.py
│   ├── pipelines.py
│   ├── settings.py
│   ├── docs.py
│   └── init.py
└── pyproject.toml

### `scrapy.cfg`
Top-level config telling Scrapy to use the `webscraper.settings` module. Allows deployment to Scrapyd if needed.

### `start_application.sh`
Simple shell script to run the spider:

- will scrape https://www.fh-erfurt.de/ and sub domains

```bash
scrapy crawl docs

items.py

Defines the data container for scraped information. Fields correspond to what the docs spider extracts.

pipelines.py

Handles post-processing of scraped items, such as:
- Cleaning and normalizing text
- Writing data to files or databases
- Applying any custom transformations

Enable/disable pipelines in settings.py.

settings.py

Scrapy configuration, including:
- Enabled pipelines
- Rate limits / delays
- Output formats
- User-agent settings
- Any project-wide configuration

docs.py

The actual spider.

Responsible for:
- Defining start URLs
- Extracting fields into Item objects
- Following links if required
- Yielding structured data for pipelines

pyproject.toml

Package metadata and dependencies.

Specifies:
- Python requirement (>=3.12,<3.13)
- Scrapy dependency
- Hatch-based build system
- Author information and README reference

⸻

Installation

Create a virtual environment (Python 3.12):

python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .

Or just install dependencies:

pip install scrapy

Running the Crawler

Use the provided script:

./start_application.sh

Or run Scrapy directly:

scrapy crawl docs

Output files or database entries depend on how pipelines.py is configured.

----

Customization
- Add new fields in items.py
- Expand or adjust parsing logic in docs.py
- Modify storage behavior in pipelines.py
- Override crawler behavior through settings.py

---

Notes
- This project uses Python 3.12, so ensure tooling and virtual environments match.
- If you deploy to Scrapyd, uncomment and configure the [deploy] section in scrapy.cfg.
