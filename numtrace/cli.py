import argparse
import json
import sys
from pathlib import Path

from .tracer import coincidence_rate, load_facts, trace_answer


def run_eval(path: Path) -> int:
    data = json.loads(path.read_text())
    facts = load_facts(data["facts"])
    ok = 0
    for case in data["cases"]:
        res = trace_answer(case["answer"], facts)
        got = {r["number"]: r["status"] for r in res["numbers"]}
        match = got == case["expected"]
        ok += match
        print(f"{'ok  ' if match else 'DIFF'} {case['name']}")
        if not match:
            print(f"     expected {case['expected']}\n     got      {got}")
    print(f"\n{ok}/{len(data['cases'])} cases as expected")
    print(f"coincidence rate: {coincidence_rate(facts):.0%} of whole percentages 1-99 "
          f"derive from these {len(facts)} facts by chance")
    return 0 if ok == len(data["cases"]) else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="numtrace", description=__doc__)
    p.add_argument("facts", type=Path, help="JSON file with a 'facts' list")
    p.add_argument("--answer", help="answer text to check")
    p.add_argument("--eval", action="store_true", help="run the 'cases' in the facts file")
    a = p.parse_args(argv)
    if a.eval:
        return run_eval(a.facts)
    if not a.answer:
        p.error("give --answer or --eval")
    res = trace_answer(a.answer, load_facts(json.loads(a.facts.read_text())["facts"]))
    for r in res["numbers"]:
        print(f"{r['status']:9} {r['number']:10} {r['how']}")
    print(f"verdict: {res['verdict']}")
    return 0 if res["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
