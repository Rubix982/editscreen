"""Resolve the Wikidata QIDs RippleEdits names its subjects by.

    python3 validation/wikidata.py Q42 Q109270083

WHY THIS EXISTS, and why it is in `validation/` rather than in the package.

`editscreen` promised not to take a knowledge-base dependency, and the
RippleEdits adapter keeps that promise by reading the subject's label back
out of the entry's own test prompts. The whole question C-010 asks is
whether that recovery is right, and a recovery cannot be its own judge: if
the only evidence available is the prompts the label came from, a wrong
label that is consistent with those prompts is invisible.

So the adjudication, and only the adjudication, goes to the authority the
benchmark itself cites. Nothing here is imported by the package, nothing
here runs at screening time, and a scored result needs the cache rather
than the network.

WHAT IS SENT. A list of QIDs read out of the public benchmark file, to
Wikidata's public API, with a generic client name. No local path, no
identity, nothing about who is asking.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "wikidata.json"
API = "https://www.wikidata.org/w/api.php"
BATCH = 50          # the API's documented ceiling for wbgetentities
PAUSE = 0.5         # courtesy between calls; this runs a handful of times
AGENT = "editscreen-validation/0.2 (research tooling; batch label lookup)"


def _load() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def _fetch(qids: list[str]) -> dict:
    query = urllib.parse.urlencode({
        "action": "wbgetentities",
        "ids": "|".join(qids),
        "props": "labels|aliases",
        "languages": "en",
        # Some items — Q42 is one — hold their English label under the
        # `mul` multilingual code rather than `en`, and `languages=en`
        # alone comes back empty for them. Without this the lookup would
        # silently report the best-known entities in the corpus as having
        # no label, which is the shape of error that looks like data.
        "languagefallback": "1",
        "format": "json",
    })
    req = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=30) as fh:
        payload = json.load(fh)
    out = {}
    for qid, entity in (payload.get("entities") or {}).items():
        if entity.get("missing") is not None:
            out[qid] = {"label": None, "aliases": [], "missing": True}
            continue
        label = ((entity.get("labels") or {}).get("en") or {}).get("value")
        aliases = [a["value"] for a in (entity.get("aliases") or {}).get("en", [])]
        out[qid] = {"label": label, "aliases": aliases}
    return out


def labels(qids: list[str], refresh: bool = False) -> dict:
    """{qid: {label, aliases}} for every id asked for, cached on disk.

    The cache is the artifact. A scoring run reads it and never touches
    the network, so the numbers can be reproduced on a machine that has
    no route to Wikidata and by someone who does not want to re-ask it.
    """
    cache = _load()
    want = sorted({q for q in qids if refresh or q not in cache})
    for i in range(0, len(want), BATCH):
        chunk = want[i:i + BATCH]
        cache.update(_fetch(chunk))
        print(f"  fetched {i + len(chunk)}/{len(want)}", file=sys.stderr)
        if i + BATCH < len(want):
            time.sleep(PAUSE)
    if want:
        CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False,
                                    sort_keys=True) + "\n", encoding="utf-8")
    return {q: cache[q] for q in qids if q in cache}


if __name__ == "__main__":
    got = labels(sys.argv[1:])
    for qid, row in got.items():
        print(f"{qid}\t{row['label']}\t{', '.join(row['aliases'][:5])}")
