# AI label suggestions for the top 50 (to be reviewed; not final labels)

Source: Claude Opus 5.5, from numeric evidence: other vessels heard within 3 nm during the gap, each vessel's full-day transmission pattern, and area reception statistics. Distances are to the Galveston entrance (29.33 N, 94.70 W). Maps were not inspected one by one.

Vessel names, type codes, class and length come straight from the AIS data (typed in by the crew; not verified against any registry). Words like 'berth', 'tour boat', 'crew boat' or 'alongside a larger ship' are guesses from behaviour (speed, size, repeated stationary positions) and are marked '- guess'.

Rules:

- **R1 artefact:** gap of 15 min or less, speed steady and the ship covered about the distance its speed predicts (short dropout; nothing unexplained happened).
- **R2 artefact:** an innocent cause is visible: moored, coverage edge, or a unit received only sporadically all day even while moving (flicker).
- **R3 real:** 45 min or more, moving, other vessels within 3 nm heard during the gap, no innocent cause visible.
- **R4 unsure:** everything else, e.g. out-and-back trips that could leave coverage, or no neighbours to prove reception.

| Rank | Vessel | Suggested | Conf. | Rule | Evidence |
|---|---|---|---|---|---|
| 1 | ACCP 1 | real | medium | R3 | Fast 9 m Class B boat silent 11.9 h on a round trip; endpoints well covered (13 Class B heard); when moving it is heard ~70% of minutes, so crossing the covered bay should have produced dozens of reports, but 0 arrived. Innocent alternative: parked elsewhere with the unit powered off (unprovable) |
| 2 | LONGHORN | data_artefact | medium | R2 | Arrived 17:33 at the spot where it sat at 0 kn for hours earlier today (likely its berth - guess); next heard 0.5 nm away already moving off at 21:55: probably silent while moored |
| 3 | T & L | data_artefact | medium | R2 | T & L sends only 22 pings all day, mostly isolated single pings while trawling at 2 kn: unit transmits but is rarely received (weak Class B) |
| 4 | MORNING LORD | real | low | R3 | Class A trawler silent 2.0 h while trawling straight in East Bay; 5 Class B boats within 3 nm were heard during the gap; East Bay Class A median report gap is 1.3 min |
| 5 | T & L | data_artefact | medium | R2 | T & L: same weak-unit pattern (22 pings all day, isolated single pings) |
| 6 | MORNING LORD | real | low | R3 | MORNING LORD silent 2.2 h trawling in East Bay; Class B boats within 3 nm were heard during the gap; 13 gaps today (a faulty unit is also possible) |
| 7 | MORNING LORD | real | low | R3 | MORNING LORD silent 2.1 h trawling in East Bay; 3 Class B boats within 3 nm were heard during the gap |
| 8 | THAI EXPRESS 1 | unsure | low | R4 | THAI EXPRESS 1 silent 1.6 h trawling ~15 nm off West Galveston; only 1 other vessel within 3 nm to show reception; start of a ~6 h period of patchy reports |
| 9 | SEAGULL II | unsure | low | R4 | Class B passenger boat (repeated loops near Galveston channel look like a harbour tour boat - guess) out-and-back 68 min; area well covered (16 Class B heard); may have been at its pier between trips |
| 10 | unnamed | unsure | low | R4 | Unnamed Class B pleasure boat, 40 min loop at Freeport; only 14 pings all day; area covered (6 Class B heard nearby) |
| 11 | MORNING LORD | real | low | R3 | MORNING LORD silent 67 min trawling in East Bay; 3 Class B boats within 3 nm were heard during the gap |
| 12 | AET RESPONSIBILITY | data_artefact | medium | R2 | AET RESPONSIBILITY ~42 nm off Galveston: reported with no break over 10 min from 00:30 to 10:07, then isolated single reports every 10-20 min while manoeuvring = transmitting but intermittently received (possibly shadowed alongside a larger ship - guess) |
| 13 | MORNING LORD | real | low | R3 | MORNING LORD silent 52 min trawling in East Bay; 2 Class B boats within 3 nm were heard during the gap |
| 14 | AQUABLISS | data_artefact | low | R2 | 274 m tanker first heard 12:48 ~15 nm off Galveston while stopped, then nothing for 7.4 h; only 34 reports all day: poorly received all day (cause unknown; low-power setting is a guess); this gap is steady outbound transit 19-26 nm out |
| 15 | AET RESPONSIBILITY | data_artefact | low | R2 | AET RESPONSIBILITY flicker pattern (isolated pings) while manoeuvring offshore; transmitting, intermittently received |
| 16 | CAPT MAJESTIC | data_artefact | low | R2 | Class B fishing boat poorly received all day: every 15-60 min while parked, and only 33 reports in 2 h while moving afterwards; a 37 min gap as it leaves its berth (guess) fits that pattern |
| 17 | MORNING STAR II | unsure | low | R4 | Class B trawler 1.8 h after leaving an anchorage where it was heard only every 10-30 min; heard regularly for hours afterwards |
| 18 | AQUABLISS | data_artefact | low | R2 | AQUABLISS: same poorly received tanker (34 reports all day), 27 min during steady outbound transit 26-31 nm off Galveston |
| 19 | THAI EXPRESS 1 | data_artefact | medium | R2 | THAI EXPRESS 1 flicker period: gap between two isolated single pings (11:34, 11:59) = transmitting, intermittently received |
| 20 | T & L | data_artefact | medium | R2 | T & L: same weak-unit pattern |
| 21 | CAVS KREWE | data_artefact | low | R2 | CAVS KREWE slowing from 3 to 2 kn; 16 min later it is 0.05 nm away, then stops (0.6 kn) and never reports again that day: arriving and coming to rest (near Clear Lake/Kemah - guess) |
| 22 | HUNTER T | data_artefact | medium | R2 | 29 m passenger-type vessel (offshore crew boat - guess) first heard parked ~40 nm out, then northbound at steady 16-18 kn; silent from 38 to 26 nm off Galveston, heard continuously once closer: edge of reception for this vessel |
| 23 | SANDRA KAY | unsure | low | R4 | Class B trawler 1.3 h near Galveston beach, steady 2.4 kn; no other vessel within 3 nm to prove reception |
| 24 | A-TEAM | data_artefact | high | R2 | A-TEAM moored at the same spot all day (every report at 29.282, -94.839; moved 0.00 nm across the gap); the reported 2.4 kn is GPS noise |
| 25 | THAI EXPRESS 1 | data_artefact | medium | R2 | THAI EXPRESS 1 flicker period (short segments between gaps) |
| 26 | CM-DJ-01 | data_artefact | medium | R2 | 8 m Class B boat at its parking spot near Port Arthur before, during and after the gap (moved 0.03 nm; 0.2-0.7 kn before, 0.5 kn after); speed spikes are manoeuvring |
| 27 | AET RESPONSIBILITY | data_artefact | low | R2 | AET RESPONSIBILITY flicker pattern while manoeuvring offshore |
| 28 | THAI EXPRESS 1 | data_artefact | medium | R2 | THAI EXPRESS 1 flicker period |
| 29 | MISS LOIS | unsure | low | R4 | Class B trawler 58 min in East Bay, steady; heard only every 10-30 min while anchored earlier (could be the spot, could be the unit) |
| 30 | THAI EXPRESS 1 | data_artefact | medium | R1 | THAI EXPRESS 1, 12 min, speed steady (3.1 -> 2.7 kn) and it covered the expected distance (turned 224 -> 117 at the end of a tow line); short dropout |
| 31 | LUCKY NIKKI | unsure | low | R4 | LUCKY NIKKI 56 min at the start of its day while trawling into East Bay; poorly received while anchored there later (single pings every 30-90 min), but that is a parked-reception pattern, not proof of a weak unit |
| 32 | THAI EXPRESS 1 | data_artefact | medium | R1 | THAI EXPRESS 1, 14 min, steady speed, covered the expected distance; short dropout |
| 33 | MORNING LORD | data_artefact | low | R1 | MORNING LORD, 14 min, steady trawl speed, covered the expected distance; short dropout |
| 34 | AET RESPONSIBILITY | data_artefact | medium | R2 | AET RESPONSIBILITY, 11 min between isolated single reports while manoeuvring: transmitting, intermittently received |
| 35 | T & L | data_artefact | medium | R2 | T & L: same weak-unit pattern |
| 36 | T & L | data_artefact | medium | R2 | T & L: same weak-unit pattern |
| 37 | MORNING LORD | data_artefact | low | R1 | MORNING LORD, 13 min, steady trawl, covered the expected distance; short dropout |
| 38 | THAI EXPRESS 1 | data_artefact | medium | R1 | THAI EXPRESS 1, 13 min, steady, covered the expected distance; short dropout |
| 39 | AET RESPONSIBILITY | data_artefact | medium | R2 | AET RESPONSIBILITY, 12 min between isolated single reports (11:45, 11:57): transmitting, intermittently received |
| 40 | THAI EXPRESS 1 | data_artefact | medium | R1 | THAI EXPRESS 1, 11 min, steady, covered the expected distance; short dropout |
| 41 | UAL BODEWES | data_artefact | high | R1 | 119 m cargo ship, 12 min during steady 11.3 kn transit ~33 nm off Galveston; heard continuously otherwise |
| 42 | MAGGIE MAE | unsure | low | R4 | MAGGIE MAE on its only trip of the day: slowed from 19 to 7 kn just before the gap, 14 min later 1.3 nm on at 20 kn (half the expected distance): a short unexplained pause |
| 43 | THAI EXPRESS 1 | data_artefact | medium | R1 | THAI EXPRESS 1, 11 min, steady, covered the expected distance; short dropout |
| 44 | MORNING LORD | data_artefact | low | R1 | MORNING LORD, 10 min, steady trawl (3.0 -> 3.3 kn, course 237 -> 247); short dropout |
| 45 | C TRUC 9 | data_artefact | high | R1 | 61 m cargo ship, 11 min during steady 9 kn transit ~55 nm off Galveston, heard continuously otherwise |
| 46 | MORNING LORD | data_artefact | low | R1 | MORNING LORD, 10 min, steady trawl (2.8 -> 2.5 kn, course 353 -> 344); short dropout |
| 47 | C TRUC 9 | data_artefact | high | R1 | 61 m cargo ship, 10 min during steady 9 kn transit ~50 nm offshore |
| 48 | BOW ENGINEER | data_artefact | high | R1 | Tanker, exactly 10 min (the threshold) during steady 13.7 kn transit ~30 nm off Galveston |
| 49 | LADY FIATH | unsure | low | R4 | Class B pleasure boat, 24 min right after its first report of the day near Port Arthur (marina - guess); area covered; heard regularly afterwards |
| 50 | ACCP 1 | unsure | low | R4 | ACCP 1, 10 min silent at 24-28 kn but moved only 1.3 nm straight-line (~4 nm expected): it slowed, stopped or looped; ends at the single 11:10 report that starts its 12 h silence (#1), so same episode |
