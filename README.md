# CircuLink Terminal

> **AI-Driven Marketplace for Industrial Circular Economy**  
> A production-quality Python TUI (Terminal User Interface) that connects industrial buyers and sellers of waste materials, by-products, and recyclables using intelligent fuzzy matching, real-time GSTIN compliance, and Gemini 2.5 Flash AI reasoning.

---

## Features

| Feature | Detail |
|---|---|
| **GSTIN-gated KYC** | Full 15-character GSTIN regex validation with Indian state-code lookup |
| **AI Byproduct Prediction** | Seller describes a process → Gemini 2.5 Flash predicts likely marketable byproducts |
| **Hazardous Screening** | 57-substance database (CAS + name); CAS match → exact → substring → RapidFuzz ≥85 — blocked listings never appear in search |
| **Intelligent Search** | Buyer enters a query → Gemini expands synonyms → RapidFuzz ensemble scoring → ranked results |
| **Weighted Scoring** | `final_score = 0.7 × fuzzy_score + 0.3 × location_score` |
| **Location Proximity** | Haversine distance + exponential decay; 100+ Indian industrial cities pre-geocoded |
| **Persistent Storage** | `~/.circularlink/` flat-JSON store; JSONL audit trail for every LLM call |
| **Full TUI** | Rich color scheme, sidebar navigation, modal dialogs — zero browser required |

---

## Quick Start

```bash
pip install circularlink
circularlink
```

### From source (editable install)

```bash
git clone https://github.com/your-org/circularlink.git
cd circularlink
pip install -e .
circularlink
```

Requires **Python 3.11+**.

---

## First Run

1. On launch you will see the **Welcome / Login** screen.
2. Switch to the **Register** tab.
3. Enter your company details — GSTIN is validated live.
4. Paste your **Google AI Studio API key** (from [aistudio.google.com](https://aistudio.google.com)).
5. Register → you enter the main application.

Subsequent launches auto-restore your session via `~/.circularlink/config.json`.

> **💡 Need test data?** See [SAMPLE_DATA.md](SAMPLE_DATA.md) for ready-to-use company credentials and testing scenarios.

---

## Navigation

| Key | Screen |
|---|---|
| `F1` | Dashboard — stats, recent matches, LLM audit log |
| `F2` | Buy: Intelligent Sourcing — search / browse / history |
| `F3` | Sell: Inventory — AI scan, manual add, hazard status |
| `F4` | KYC / Settings — edit profile, change API key, logout |
| `Ctrl+Q` | Quit |

---

## Architecture

```
src/circularlink/
├── app.py                  # Root App — LoginEvent, LogoutEvent, screen routing
├── __main__.py             # CLI entry point  →  circularlink
├── styles.tcss             # Textual CSS — Industrial Earth & Tech palette
│
├── core/
│   ├── gstin.py            # GSTIN regex validator + state-code lookup
│   ├── geo.py              # City geocoding, haversine, location scoring
│   ├── hazard.py           # 4-strategy hazardous material checker
│   ├── matcher.py          # FuzzyMatcher: ensemble NLP + weighted geo scoring
│   └── gemini_agent.py     # Gemini 2.5 Flash: byproduct prediction + keyword expansion
│
├── storage/
│   └── db.py               # JSON persistence layer (companies, products, matches, logs)
│
├── screens/
│   ├── welcome.py          # Login + Registration + live GSTIN validation
│   ├── dashboard.py        # F1 — stats, match table, LLM log
│   ├── buyer.py            # F2 — search, Gemini expansion, ranked results
│   ├── seller.py           # F3 — AI byproduct scan, hazard check, inventory
│   ├── kyc.py              # F4 — profile management, logout, account delete
│   └── modals.py           # MessageModal, ConfirmModal, AddProductModal, SearchModal
│
└── data/
    └── hazardous.csv       # 57 hazardous substances (CAS + name + UN number)
```

### Scoring Formula

$$\text{final\_score} = 0.7 \times \text{fuzzy\_score} + 0.3 \times \text{location\_score}$$

- **fuzzy\_score** = ensemble average of RapidFuzz `token_set_ratio`, `token_sort_ratio`, `partial_ratio` across product name and description
- **location\_score** = $e^{-d / (R/5)}$ where $d$ is Haversine distance in km and $R$ is `max_radius_km` (default 2000 km)

### Hazard Check Strategy (defence-in-depth)

1. CAS number regex match against CSV
2. Exact name match (case-insensitive)
3. Substring containment (both directions)
4. RapidFuzz `token_set_ratio` ≥ 85

Any hit → product status set to `blocked`; never returned in buyer search.

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `GOOGLE_API_KEY` | Fallback API key if none stored in DB |

Recommended: set key via the **KYC / Settings** screen (stored locally, never transmitted outside Gemini API calls).

---

## Storage

All data is stored under `~/.circularlink/`:

```
~/.circularlink/
├── config.json         # api_key, current_company_id
├── companies.json      # Registered companies
├── products.json       # Product listings (approved / blocked / pending)
├── matches.json        # Saved search results
└── llm_logs/
    └── YYYY-MM-DD.jsonl  # Append-only Gemini call audit log
```

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `textual` | ≥0.80.0 | TUI framework |
| `google-generativeai` | ≥0.8.0 | Gemini 2.5 Flash API |
| `rapidfuzz` | ≥3.9.0 | Fuzzy NLP matching |
| `rich` | ≥13.7.0 | Terminal rendering |
| `geopy` | ≥2.4.0 | Geocoding utilities |

---

## Color Scheme

| Role | Hex | Usage |
|---|---|---|
| Background Deep | `#1A1B26` | Screen background |
| Background Panel | `#24253A` | Sidebar, cards |
| Seller / Red | `#E06C75` | Seller UI, warnings |
| Buyer / Green | `#98C379` | Buyer UI, success |
| AI / Blue | `#61AFEF` | Gemini highlights |
| Hazard / Amber | `#D19A66` | Hazard banners |
| Accent / Purple | `#C678DD` | Hotkeys, accents |

---

## Publishing to PyPI

```bash
pip install build twine
python -m build
twine upload dist/*
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

Built with [Textual](https://github.com/Textualize/textual) by Textualize, [Google Generative AI](https://ai.google.dev/), and [RapidFuzz](https://github.com/maxbachmann/RapidFuzz).
