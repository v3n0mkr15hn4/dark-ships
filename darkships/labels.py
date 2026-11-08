"""labels.jsonl persistence: append-only, last line per event_id wins, resume at first unlabelled."""
import json
import os
from pathlib import Path

LABELS = ("real", "data_artefact", "unsure")


def load_labels(path):
    """Return {event_id: latest record}. Skips blank or half-written lines (e.g. after a crash)."""
    labels = {}
    path = Path(path)
    if not path.exists():
        return labels
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("event_id") and rec.get("label") in LABELS:
            labels[rec["event_id"]] = rec
    return labels


def append_label(path, record):
    """Append one record and force it to disk, so a crash loses at most the event being edited."""
    assert record["label"] in LABELS
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def first_unlabelled(event_ids, labels, start=0):
    """Index of the first event (from `start`, wrapping around) without a label; None if all done."""
    n = len(event_ids)
    for i in range(n):
        j = (start + i) % n
        if event_ids[j] not in labels:
            return j
    return None
