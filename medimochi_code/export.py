import csv
import json
import os
import re
from pathlib import Path


FIELDS = ["Term", "Definition", "Source", "Field", "Document"]


def parse_terms(output_text: str) -> list[dict]:
    """Parse the model's JSON, tolerating ```json fences."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", output_text.strip())
    terms = json.loads(text)["terms"]
    if not isinstance(terms, list):
        raise ValueError("'terms' must be a list")
    for term in terms:
        if not isinstance(term.get("term"), str) or not term["term"].strip():
            raise KeyError("term")
    return terms


def dedupe_terms(terms: list[dict]) -> list[dict]:
    seen = {}
    for term in terms:
        seen.setdefault(term["term"].strip().lower(), term)
    return list(seen.values())


def check_terms_csv_writable(path: str = "terms.csv") -> None:
    file = Path(path)
    try:
        if file.exists():
            file.open("a").close()
        elif not os.access(file.resolve().parent, os.W_OK):
            raise PermissionError("the folder is not writable")
    except OSError as e:
        raise ValueError(
            f"Cannot write to {file.resolve()} ({e.strerror or e}). If the file is open in Excel or "
            "another program, close it and run again. Nothing was searched or charged."
        )


def save_terms_csv(terms: list[dict], field: str, document: str, path: str = "terms.csv") -> int:
    file = Path(path)
    with file.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        for t in terms:
            writer.writerow([t["term"], t["definition"], t.get("source") or "", field, document])
    return len(terms)
