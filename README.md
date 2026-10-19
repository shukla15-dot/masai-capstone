# Mamaearth Returns & Growth Intelligence Pipeline

A three-layer, fully reproducible analytics pipeline that answers one question for
Mamaearth's Growth Analytics team:

> **Where are returns really coming from, and what is the true revenue picture once
> the data is cleaned?**

The three layers are wired together in one direction — **SQL → Python → GenAI** —
and no layer reports a number it did not itself compute or receive from the layer
before it.

| Layer | Folder | What it does | Feeds forward |
|-------|--------|--------------|---------------|
| 1. SQL relational layer | `sql/` | Builds the SQLite store and runs 9 business reports on the **raw** data | Establishes the raw baseline (e.g. raw revenue ₹99,860.20) |
| 2. Python wrangling & EDA | `analysis/` | Cleans the raw CSVs, reconciles against Part 1, finds the real patterns, writes charts | Produces the **verified** numbers and `narrator/findings.json` |
| 3. GenAI insight narrator | `narrator/` | Turns `findings.json` into an SCR business narrative (Gemini + offline fallback) | Produces `sample_output.txt`, the board-ready writeup |

---

## Repository structure

```
masai-capstone/
├── README.md                     ← you are here
├── requirements.txt              ← pandas, matplotlib, google-genai
├── data/                         ← source CSVs, committed exactly as given (never hand-edited)
│   ├── customers.csv             (45 rows)
│   ├── products.csv              (16 rows)
│   └── orders.csv                (180 rows, deliberately messy)
├── sql/                          ← Part 1
│   ├── schema.sql                three tables (PK / FK / NULL rules)
│   ├── seed_data.sql             INSERTs generated from the CSVs (blanks → NULL)
│   └── reports.sql               9 reports (a–i) with exact output pasted as comments
├── analysis/                     ← Part 2
│   ├── clean_and_eda.py          cleaning + EDA; writes narrator/findings.json at the end
│   └── visualize.py              writes the two PNGs
├── visualizations/               ← Part 2 output
│   ├── return_rate_by_payment.png
│   └── monthly_revenue_trend.png
└── narrator/                     ← Part 3
    ├── findings.json             verified figures, written by code (never hand-typed)
    ├── generate_narrative.py     SCR narrative: online Gemini + keyless offline fallback
    └── sample_output.txt         saved narrative the numeric checker is verified against
```

---

## Setup (once)

Requires **Python 3.10+** and the **sqlite3** command-line tool.

```bash
# from the repo root
python -m venv .venv

# activate it:
#   Windows PowerShell:   .venv\Scripts\Activate.ps1
#   Windows cmd:          .venv\Scripts\activate.bat
#   macOS / Linux:        source .venv/bin/activate

pip install -r requirements.txt
```

> The offline narrator path (Part 3) needs **no** third-party library and no API key.
> `google-genai` is only required for the optional live Gemini call.

---

## Run order

Part 1 and Part 2 are independent (either can run first); Part 3 depends on the
`findings.json` that Part 2 writes. The natural top-to-bottom order is:

### Part 1 — SQL layer

```bash
sqlite3 mamaearth.db < sql/schema.sql       # create the 3 tables (re-runnable: drops first)
sqlite3 mamaearth.db < sql/seed_data.sql    # load 45 / 16 / 180 rows; blank cells → NULL
sqlite3 mamaearth.db < sql/reports.sql      # run reports a–i
```

`reports.sql` already contains each query's **exact expected output** pasted as a
comment block above the query, so you can compare your run against the brief line
by line. Headline raw figure: **total revenue = ₹99,860.20** across 180 orders.

*(`mamaearth.db` is a build artifact and is git-ignored — it is rebuilt from the
committed `.sql` files every time.)*

### Part 2 — Python wrangling, EDA & charts

```bash
python analysis/clean_and_eda.py            # prints every step; writes narrator/findings.json
python analysis/visualize.py                # writes the two PNGs to visualizations/
```

`clean_and_eda.py` runs directly on the **raw CSVs** (not the SQL database), prints
every intermediate result, asserts each number against the brief, and — as its final
step — **writes `narrator/findings.json`** from the numbers it just computed. This is
how the verified figures flow into Part 3 without ever being hand-typed.

Headline cleaned figures: **cleaned revenue = ₹97,358.30** (₹2,501.90 below the raw
total, exactly the value of the 5 removed duplicate orders), **COD return rate 44.4%**,
**highest-risk segment COD + Tier-2 = 54.5%**, **true peak month = March (₹20,318.90)**.

### Part 3 — GenAI narrator

```bash
# Offline (default, zero config, fully deterministic — no key, no network, no .env):
python narrator/generate_narrative.py
```

**Online (optional).** To make the real Gemini call, provide a free API key. Two ways:

*Option A — `.env` file (recommended).* Copy the template and paste your key:

```bash
cp .env.example .env            # macOS / Linux
Copy-Item .env.example .env     # Windows PowerShell
# then edit .env and set:  GEMINI_API_KEY=your-free-key
python narrator/generate_narrative.py
```

*Option B — shell environment variable (no file):*

```bash
# PowerShell:   $env:GEMINI_API_KEY = "your-free-key"; python narrator/generate_narrative.py
# bash:         GEMINI_API_KEY=your-free-key python narrator/generate_narrative.py
```

### How to generate a free Gemini API key

1. Go to **[aistudio.google.com](https://aistudio.google.com)** — *not* `gemini.google.com`
   (that's the consumer chatbot). Sign in with a **personal** Gmail account.
2. Click **"Get API key"** → **"Create API key"** → **"Create API key in new project."**
3. **Copy the key immediately** — it is shown in full only once. Paste it into `.env`.
4. It's free; never enable billing, never use a paid-only key, and never commit it
   (`.env` is git-ignored).

The script loads `findings.json`, builds an SCR (Situation–Complication–Resolution)
narrative, saves it to `narrator/sample_output.txt`, and runs a numeric-accuracy
checker that confirms all five key figures (97,358.30 / 44.4 / 54.5 / 2,501.90 /
March + 20,318.90) are present. With a key set it calls Gemini (`temperature=0`,
explicit token limit, 30 s timeout, full `try/except`); if no key is set or the call
fails, it automatically falls back to the offline template. `sample_output.txt` in
this repo is the **offline** output, so the pipeline is gradable with zero API spend.

---

## How the layers connect

```
raw CSVs ──> Part 1 SQL reports        (raw baseline: ₹99,860.20, return rates, etc.)
raw CSVs ──> Part 2 clean_and_eda.py   (clean → reconcile → EDA)
                      │
                      ├──> visualizations/*.png
                      └──> narrator/findings.json  ──> Part 3 generate_narrative.py ──> sample_output.txt
```

Every number in the narrative traces back through `findings.json` to a value computed
in `clean_and_eda.py`, which in turn reconciles against the Part 1 SQL baseline — the
pipeline's golden rule, end to end.

---

## Notes

- The source CSVs in `data/` are committed exactly as provided and are **never**
  hand-edited; all cleaning happens in Part 2's Python code.
- The two bulk-quantity outliers (`O0011`, `O0098`) are **flagged, not dropped** —
  they are excluded only from the corrected monthly trend, which is why January's
  apparent revenue lead turns out to be an artifact.
- Both Python scripts are deterministic: re-running them regenerates identical numbers,
  identical `findings.json`, and identical PNGs from the raw CSVs every time.
