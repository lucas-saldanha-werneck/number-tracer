"""Check that every number in an assistant's answer traces to a source fact.

Pure standard library. A number is:
  traced    - equals a source fact, at the precision the answer shows
  derived   - equals a sum, difference, share or change of two source facts
  untraced  - neither
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from decimal import Decimal

SCALES = {"k": 10**3, "thousand": 10**3, "m": 10**6, "million": 10**6,
          "bn": 10**9, "billion": 10**9}
CURRENCY = {"£": "money", "$": "money", "€": "money"}

NUMBER_RE = re.compile(
    r"(?<![\w.])(?P<cur>[£$€])?\s?(?P<int>\d{1,3}(?:,\d{3})+|\d+)(?P<dec>\.\d+)?"
    r"\s?(?P<suf>%|bn|billion|million|thousand|m|k)?(?![\w])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Fact:
    id: str
    label: str
    value: Decimal
    unit: str  # "money", "pct" or "count"


@dataclass
class Found:
    text: str
    value: Decimal      # value in base units (1.2m -> 1200000)
    tolerance: Decimal  # half of the last shown digit, in base units
    kind: str           # "money", "pct" or "plain"


def load_facts(rows: list[dict]) -> list[Fact]:
    return [Fact(r["id"], r["label"], Decimal(str(r["value"])), r["unit"]) for r in rows]


def extract_numbers(text: str) -> list[Found]:
    found = []
    for m in NUMBER_RE.finditer(text):
        suf = (m.group("suf") or "").lower()
        cur = m.group("cur")
        dec = m.group("dec") or ""
        raw = m.group("int").replace(",", "") + dec
        # a bare 4-digit year is not a claim
        if not cur and not suf and not dec and len(raw) == 4 and 1990 <= int(raw) <= 2099:
            continue
        scale = Decimal(SCALES.get(suf, 1))
        shown = Decimal(raw)
        step = Decimal(1).scaleb(-len(dec.lstrip(".")))  # 10^-decimals
        kind = "pct" if suf == "%" else ("money" if cur else "plain")
        found.append(Found(m.group(0).strip(), shown * scale, step / 2 * scale, kind))
    return found


def _kind_ok(kind: str, unit: str) -> bool:
    if kind == "pct":
        return unit == "pct"
    if kind == "money":
        return unit == "money"
    return unit in ("count", "money")


def _close(a: Decimal, b: Decimal, tol: Decimal) -> bool:
    return abs(a - b) <= tol


def trace_number(n: Found, facts: list[Fact]) -> dict:
    for f in facts:
        if _kind_ok(n.kind, f.unit) and _close(f.value, n.value, n.tolerance):
            return {"number": n.text, "status": "traced", "how": f"{f.id} ({f.label})"}
    for a, b in itertools.permutations(facts, 2):
        if a.unit != b.unit or a.unit == "pct":
            continue
        if n.kind == "pct":
            if b.value != 0 and _close(a.value / b.value * 100, n.value, n.tolerance):
                return {"number": n.text, "status": "derived",
                        "how": f"share: {a.id} / {b.id}"}
            if b.value != 0 and _close((a.value - b.value) / b.value * 100, n.value, n.tolerance):
                return {"number": n.text, "status": "derived",
                        "how": f"change: ({a.id} - {b.id}) / {b.id}"}
        elif _kind_ok(n.kind, a.unit):
            if a.id < b.id and _close(a.value + b.value, n.value, n.tolerance):
                return {"number": n.text, "status": "derived", "how": f"sum: {a.id} + {b.id}"}
            if _close(a.value - b.value, n.value, n.tolerance) and a.value > b.value:
                return {"number": n.text, "status": "derived", "how": f"difference: {a.id} - {b.id}"}
    return {"number": n.text, "status": "untraced", "how": ""}


def trace_answer(answer: str, facts: list[Fact]) -> dict:
    results = [trace_number(n, facts) for n in extract_numbers(answer)]
    bad = [r for r in results if r["status"] == "untraced"]
    return {"verdict": "fail" if bad else "pass", "numbers": results,
            "untraced": [r["number"] for r in bad]}


def coincidence_rate(facts: list[Fact]) -> float:
    """Share of whole-number percentages 1..99 that 'derive' from the facts by chance.

    A high value means a derived match proves little: a human must read the formula.
    """
    hits = 0
    for p in range(1, 100):
        n = Found(f"{p}%", Decimal(p), Decimal("0.5"), "pct")
        if trace_number(n, facts)["status"] != "untraced":
            hits += 1
    return hits / 99
