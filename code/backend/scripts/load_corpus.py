#!/usr/bin/env python
"""Walk data/, ingest every document, replace instead of pile up.

    uv run python scripts/load_corpus.py
    uv run python scripts/load_corpus.py --reset            # wipe the collection first
    uv run python scripts/load_corpus.py --strategy dynamic --base-url http://localhost:7799

Doing `curl -X POST /ingest` by hand once per document (Assignment 3, Part 4) is
the point at which you write a loader. This one reads the YAML front-matter every
document already carries (title, product, audience, effective, version) and sends
it as metadata alongside the text, so Part 4 improvement #2 (real metadata) and
Part 5 improvement #2 (metadata filters) have something to work with.

Re-running this script is safe: `source` is the file stem, and the backend derives
each chunk's id from (source, index) — see app/vectorstore.py `stable_point_id`.
Re-ingesting a document replaces its chunks instead of duplicating them.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


def parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    """Split a document into its `--- ... ---` header and the body below it."""
    text = raw.strip()
    if not text.startswith("---"):
        return {}, text
    _, _, rest = text.partition("---")
    header, sep, body = rest.partition("---")
    if not sep:
        return {}, text
    meta: dict[str, str] = {}
    for line in header.strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://localhost:7799")
    ap.add_argument("--data-dir", default=str(DATA_DIR))
    ap.add_argument("--strategy", default="dynamic", choices=["static", "dynamic", "sentence", "semantic"])
    ap.add_argument("--reset", action="store_true", help="DELETE /collection before ingesting")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    files = sorted(p for p in data_dir.glob("*.md") if p.name.lower() != "readme.md")
    if not files:
        print(f"No .md documents found in {data_dir}", file=sys.stderr)
        return 1

    with httpx.Client(base_url=args.base_url, timeout=60) as client:
        if args.reset:
            r = client.delete("/collection")
            r.raise_for_status()
            print(f"Reset collection: {r.json()}")

        ok, failed = 0, 0
        for path in files:
            meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
            source = path.stem
            payload = {
                "text": body,
                "strategy": args.strategy,
                "source": source,
                "title": meta.get("title"),
                "product": meta.get("product"),
                "audience": meta.get("audience"),
                "effective": meta.get("effective"),
                "version": meta.get("version"),
            }
            try:
                r = client.post("/ingest", json=payload)
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                failed += 1
                print(f"FAIL  {path.name}: {e.response.status_code} {e.response.text}", file=sys.stderr)
                continue
            except httpx.HTTPError as e:
                failed += 1
                print(f"FAIL  {path.name}: {e}", file=sys.stderr)
                continue
            data = r.json()
            ok += 1
            print(f"OK    {path.name:<32} source={source:<28} "
                  f"chunks={data['count']:<3} strategy={data['strategy']}")

    print(f"\n{ok} ingested, {failed} failed, out of {len(files)} documents.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
