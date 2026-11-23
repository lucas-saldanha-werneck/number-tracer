import json
from decimal import Decimal
from pathlib import Path

from numtrace import coincidence_rate, extract_numbers, trace_answer
from numtrace.cli import main
from numtrace.tracer import load_facts

EXAMPLE = Path(__file__).parent.parent / "examples" / "example-facts.json"
FACTS = load_facts(json.loads(EXAMPLE.read_text())["facts"])


def status(answer):
    return {r["number"]: r["status"] for r in trace_answer(answer, FACTS)["numbers"]}


def test_extract_scales_and_kinds():
    n = extract_numbers("£1.2m, 15%, 1,250,000 and 3k")
    assert [x.value for x in n] == [Decimal("1200000"), Decimal("15"), Decimal("1250000"), Decimal("3000")]
    assert [x.kind for x in n] == ["money", "pct", "plain", "plain"]


def test_year_and_quarter_labels_are_skipped():
    assert extract_numbers("In 2025 Q3 was fine") == []


def test_direct_match_at_shown_precision():
    assert status("Revenue was £1.25m.") == {"£1.25m": "traced"}
    assert status("Revenue was £1.4m.")["£1.4m"] != "traced"
    assert status("Revenue was £1.3m.") == {"£1.3m": "traced"}  # 1.25 shown to 1 decimal can read 1.3


def test_rounded_number_within_half_digit():
    assert status("About £1.2m.") == {"£1.2m": "traced"}  # edge: 1.25 vs 1.2, inside +-0.05


def test_percentage_derived_with_formula():
    r = trace_answer("Revenue grew 25%.", FACTS)["numbers"][0]
    assert r["status"] == "derived" and "rev_2025" in r["how"]


def test_invented_number_fails_verdict():
    r = trace_answer("Revenue was £1.8m.", FACTS)
    assert r["verdict"] == "fail" and r["untraced"] == ["£1.8m"]


def test_finding_invented_number_can_trace_by_coincidence():
    # 1.4m is invented, but rev_2024 + debt = 1.4m. The tracer calls it derived and shows
    # the formula, so a human can see the sum makes no sense for "revenue".
    r = trace_answer("Revenue was £1.4m.", FACTS)["numbers"][0]
    assert r["status"] == "derived" and r["how"] == "sum: debt + rev_2024"


def test_percent_never_matches_money_fact():
    assert status("It was 900%.") == {"900%": "untraced"}


def test_sum_and_difference():
    assert status("Revenue minus costs is £350k.")["£350k"] == "derived"
    assert status("Revenue plus costs are £2.15m.")["£2.15m"] == "derived"


def test_coincidence_rate_is_a_fraction():
    assert 0 < coincidence_rate(FACTS) < 1


def test_eval_cases_all_pass(capsys):
    assert main([str(EXAMPLE), "--eval"]) == 0
    assert "6/6 cases as expected" in capsys.readouterr().out


def test_cli_exit_code_on_fail():
    assert main([str(EXAMPLE), "--answer", "Revenue was £9m."]) == 1
