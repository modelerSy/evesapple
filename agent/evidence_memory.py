"""Persistent Evidence Memory with conservative normalized-claim matching."""
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from backend.app.models import Evidence, EvidenceRequirement

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "eve_evidence.sqlite3"
_WORD_NUMBERS = {"one": "1", "two": "2", "three": "3", "four": "4", "seven": "7", "twelve": "12"}
_STOP_WORDS = {"using", "use", "after", "for", "the", "this", "a", "an", "by", "it", "product", "improves", "improve"}

def canonicalize(text: str) -> str:
    value = text.lower()
    for word, number in _WORD_NUMBERS.items():
        value = re.sub(rf"\b{word}\b", number, value)
    tokens = re.findall(r"[a-z]+|\d+|%", value)
    return " ".join(token for token in tokens if token not in _STOP_WORDS)

def critical_constraints(text: str) -> set[str]:
    value = canonicalize(text)
    return set(re.findall(r"\d+%?|\d+\s*(?:week|weeks|day|days|month|months|year|years)", value))

class EvidenceMemory:
    def __init__(self, path: Path = DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("""CREATE TABLE IF NOT EXISTS investigations (
            claim_id TEXT PRIMARY KEY, canonical_claim TEXT NOT NULL, original_claim TEXT NOT NULL,
            mode TEXT NOT NULL, components_json TEXT NOT NULL, requirements_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL, verification_json TEXT NOT NULL, retrieved_at TEXT NOT NULL,
            cacheable INTEGER NOT NULL DEFAULT 0)""")
        columns = {row[1] for row in self.connection.execute("PRAGMA table_info(investigations)")}
        if "cacheable" not in columns:
            # Existing runtime records may have been written after a partial
            # failure, so they are deliberately not eligible for reuse.
            self.connection.execute("ALTER TABLE investigations ADD COLUMN cacheable INTEGER NOT NULL DEFAULT 0")
        self.connection.commit()

    def lookup(self, claim: str, mode: str, components: list[str]) -> dict | None:
        wanted = canonicalize(claim)
        wanted_constraints = critical_constraints(claim)
        wanted_tokens = set(wanted.split())
        for row in self.connection.execute("SELECT * FROM investigations WHERE mode = ? AND cacheable = 1 ORDER BY retrieved_at DESC", (mode,)):
            stored_constraints = critical_constraints(row["original_claim"])
            if wanted_constraints != stored_constraints:
                continue
            stored_tokens = set(row["canonical_claim"].split())
            overlap = len(wanted_tokens & stored_tokens) / max(1, len(wanted_tokens | stored_tokens))
            stored_components = set(json.loads(row["components_json"]))
            component_overlap = (len(set(components) & stored_components) / max(1, len(set(components) | stored_components))) if components else 1.0
            if overlap >= 0.45 and component_overlap >= 0.5:
                return {key: row[key] for key in row.keys()} | {"match_score": round((overlap + component_overlap) / 2, 3)}
        return None

    def get_exact(self, claim: str, mode: str) -> dict | None:
        """Read a named demo record without invoking inference or research."""
        claim_id = f"{mode}:{canonicalize(claim)}"
        row = self.connection.execute("SELECT * FROM investigations WHERE claim_id = ?", (claim_id,)).fetchone()
        return ({key: row[key] for key in row.keys()} if row else None)

    def store(self, claim: str, mode: str, requirements: list[EvidenceRequirement], evidence: list[Evidence], verification: dict, *, cacheable: bool = False) -> None:
        canonical = canonicalize(claim)
        claim_id = f"{mode}:{canonical}"
        self.connection.execute("""INSERT OR REPLACE INTO investigations
            (claim_id, canonical_claim, original_claim, mode, components_json, requirements_json, evidence_json, verification_json, retrieved_at, cacheable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                claim_id, canonical, claim, mode,
                json.dumps([r.component for r in requirements]),
                json.dumps([r.model_dump() for r in requirements]),
                json.dumps([e.model_dump(mode="json") for e in evidence]),
                json.dumps(verification), datetime.now(timezone.utc).isoformat(), int(cacheable),
            ))
        self.connection.commit()

    @staticmethod
    def decode_evidence(record: dict) -> list[Evidence]:
        return [Evidence(**item) for item in json.loads(record["evidence_json"])]
