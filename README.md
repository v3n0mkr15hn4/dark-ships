# Dark ships: AIS gap detection, Houston–Galveston, 2026-04-15 (UTC)

**Data:** MarineCadastre `ais-2026-04-15.csv.zst` (227,742,913 bytes; 7,806,560 rows).
**Bounding box:** lat 28.40–29.90, lon −95.60 to −93.70.

**Run it:**
```powershell
scripts/download.ps1                         # downloads the raw file into data/raw/ (not in git)
python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r requirements.txt
python run.py --config config.toml           # one command: raw -> events.parquet (~1 min first run, ~15 s after)
streamlit run app/review.py                  # review page; labels -> out/labels.jsonl
python -m pytest                             # 13 tests
```

**Outputs:**
- `out/events.parquet`: all 515 gaps with features.
- `out/labels.jsonl`: the 50 reviewed events.
- `DATA.md`: the data card.
- `PLAN.md`: the design, and every decision change with its reason.

## 1. Scoring rule and the three features that mattered most

A **gap** is a silence of at least `max(10 min, 10 × expected interval)`. The expected interval depends on the transmitter class and the vessel's state before the silence: 60 s when moving, 180 s when anchored, moored or slow (NOAA keeps at most one report per minute).

**Score:**
`score = 100 × (0.35·D + 0.30·C + 0.15·U + 0.10·K + 0.10·T) × suppressors`
- **D:** log of the gap relative to the expected interval
- **C:** were other vessels heard near the gap's endpoints during it
- **U:** was it moving when it went silent
- **K:** time not explained by a straight transit
- **T:** type prior (commercial Class A is required to transmit)

**Suppressors** for known false alarms: coverage hole ×0.2, port/berth/anchorage ×0.2, impossible jump ×0.3, shared MMSI ×0.1.

The weights were frozen before review (git tag `weights-frozen`).

**The three that mattered,** from the leave-one-out ablation (how many of the top 50 survive when one part is removed):

| Part removed | Top 50 kept |
|---|---|
| **U** (underway when silent) | 36 |
| **T** (vessel type and class) | 36 |
| **Port/berth suppressor** | 40 |

Coverage C barely mattered (49 of 50 kept). The box is inside receiver range and busy enough that some other vessel is almost always heard within about 10 nm.

## 2. What fooled me

**Of the top 50: 6 real, 34 data artefact, 10 unsure.**
- Precision of `real`: 0.40 in the top 10, 0.12 in the top 50.
- The 6 real events come from just **two vessels**:
  - **MORNING LORD**, a Class A shrimp trawler: 5 silences of 52 min to 2.2 h while trawling in East Bay, with nearby Class B boats still heard.
  - **ACCP 1**, a fast Class B boat: 12 h silent on a round trip through a well-covered channel.

**Most common false alarm (16 of 34):** a transmitter that is **on but only intermittently received**. Isolated single reports between gaps prove the unit was transmitting, and a switched-off unit sends nothing. Next most common: short dropouts of 15 min or less during steady motion (13), and boats parked across the gap (4).

**What fooled me along the way:**
- **"Poorly received while parked" is not "weak transmitter".** ACCP 1 was heard 22% of the time at its dock but about 70% while moving, and another Class B boat at the same dock was also under-received. It was the spot, not the unit.
- **The moving-ship exception to the port rule** is fooled by GPS speed noise (a moored boat "doing" 2.4 kn). It can also rank the same parked silence 2nd or 157th, depending on the speed caught at each end.
- **A neighbour "also went silent" check** that ignored 5 minutes at each end was meaningless for 10–16 min gaps. I caught it and removed it before labelling.

## 3. Data problems in the raw feed

**Handled:**
- 4,643 rows from non-ship MMSIs (SART, AtoN, other), removed by ship-range filter
- 1,793 duplicate (mmsi, time) rows, deduplicated
- Out-of-order rows, sorted per vessel before finding gaps
- Sentinel values: none present in 2025+ files, still filtered defensively
- Class A and B reporting rates, and NOAA's 1-minute downsampling, built into the expected interval
- BBox edge effects: the full national-day track is used for vessels seen in the box
- Day boundary: never treated as a gap

**Not handled (and why):**
- **Vessels that go dark and don't return within the day:** needs neighbouring days.
- **Stale navigation status:** speed is trusted instead.
- **GPS positions on land and noisy speeds of moored boats:** rare; noted in DATA.md.
- **The raw file is about 7× Excel's row limit:** inspect it with DuckDB instead.

## 4. With a week I would compute…
- **Day ±1 files:** gaps across midnight, plus "first or last report far from any edge or berth". Vessels that go dark and never return are arguably the most interesting dark ships.
- **A per-vessel reception baseline:** a flicker detector to separate intermittent reception from a switch-off.
- **A finer, class-aware coverage test:** 3 nm, Class B neighbours for Class B gaps.
- **Merged episodes:** one silence split by a single report becomes one event.
- **Better context:** distance to coast and to receivers.
- **A second annotator.**

**From you I would need:**
- receiver-station locations and outage logs;
- satellite AIS for offshore traffic;
- a vessel registry, to verify names and types;
- any confirmed dark-vessel cases as ground truth.

## 5. AI tools and web resources used

| Tool / resource | What for | What I checked or changed |
|---|---|---|
| Claude Code (Claude Opus 5.5) | PLAN.md; pipeline, app and tests code; data profiling; explanations of AIS fields | Reviewed each block. Asked for a coverage redesign and a monotonic coverage rule, and rejected the first coverage feature (it boosted coverage holes). |
| Claude Code + `frontier-search` skill | Verifying the current MarineCadastre format and recency (2026 `.csv.zst`, 2025+ schema) on the primary NOAA pages | Format confirmed against the NOAA data dictionary |
| Claude Code: **label suggestions** | **49 of the 50 labels started as AI suggestions** with evidence (`out/ai_suggestions.md`), which I reviewed and accepted. #1 I labelled myself. | Challenged several claims, which led to corrections: "weak transmitter" → location; wrong distances; a flawed neighbour check; ACCP 1 checked directly in the raw file. |
| MarineCadastre blob index, NOAA InPort #77594, AIS data dictionary and FAQ (May 2026) | File naming, schema, 1-minute downsampling, terrestrial-only coverage (40–50 mi) | |
| USCG NAVCEN *Types of AIS* / *Class A reports* | Reporting rates, sentinel values, MMSI classes | The Class B 30 s rate is from ITU-R M.1371, not confirmed on NAVCEN |
| Iowa Environmental Mesonet ASOS archive (GLS, LBX) | Fog check for the chosen day (visibility 9–10 mi) | |
| DuckDB, Streamlit, pydeck docs; PyPI | Reading `.zst`, map layers, package versions | Versions pinned from the tested venv (`requirements.txt`) |
