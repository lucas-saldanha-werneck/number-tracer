# number-tracer

Independent demo, not affiliated with Codat.

Takes the text of an assistant's answer and a list of source facts, and checks that each number in the answer comes from a source. A number is `traced` if it equals a fact at the precision the answer shows. It is `derived` if it equals a sum, difference, share or change of two facts, and the tool prints the formula. Otherwise it is `untraced`, and the answer fails.

I wrote it after reading a job description about an assistant for commercial banking, where every number in an answer has to trace to a source and nobody should believe a percentage without its denominator. It is a small version of that check, plain Python with no dependencies.

## Run it

Python 3.12 (the version CI uses). Nothing to install except pytest for the tests.

```sh
python -m numtrace examples/example-facts.json --answer "Revenue grew 25% from 2024 to 2025, to £1.25m."
python -m numtrace examples/example-facts.json --eval
```

The first command prints one line per number and exits with 1 if any number is untraced. The second runs the six cases stored in the example file and then prints the coincidence rate (see below).

The facts file is a JSON list. Each fact has an `id`, a `label`, a `value` and a `unit` of `money`, `pct` or `count`. The file in `examples/` is invented example data.

## What it does with a number

- Reads `£1.2m`, `$900k`, `15%`, `1,250,000`. Skips bare years like 2025.
- Treats the digits shown as a precision: `£1.2m` matches any fact within 0.05m of 1.2m. So 1,250,000 can be written as £1.2m or £1.3m and both trace.
- Never matches a percentage to a money fact, or the other way round.
- For percentages, tries share (a / b) and change ((a − b) / b) for every pair of facts. For amounts, tries sum and difference of every pair.

## A finding from the example data

With seven invented facts, 11 of the 99 whole-number percentages from 1% to 99% come out as `derived` by chance. A made-up amount does the same. The example answer "Revenue was £1.4m" is invented, but prior-year revenue plus the loan balance is £1.4m, so the tool reports `derived: sum: debt + rev_2024`.

So a `derived` result is not proof. It is a formula that a person has to read and accept. The more facts there are, the more often an invented number finds some pair to hide behind. `--eval` prints this rate for your facts. The direct `traced` result has no such problem, and a test in `tests/` pins down the coincidence case.

## What was tested

Twelve offline tests with pytest, run in CI on every push:

- number extraction (scales, currency, percent, thousands separators, years skipped)
- direct matches at the shown precision, including the 1.25 / 1.2 / 1.3 edge
- derived percentages, sums and differences, with the formula text
- an invented number failing the verdict, and the exit code of the command
- the coincidence case above
- the six cases in the example file, through `--eval`

## What was not tested

- Real answers from a real assistant. All text in the tests is written by hand.
- Real financial data. The facts are invented.
- Currencies are only recognized by symbol (£ $ €), and a £ amount can match a $ fact. Unit conversion is not done.
- Negative numbers, ranges ("5 to 7 months") and numbers written as words.
- Percentage points versus percent. A change of 28% to 30% is two points, and the tool does not model that.
- Answers longer than a few paragraphs, and speed on large fact lists. The pair search grows with the square of the number of facts.
- Python versions other than the one used here (3.15) and the one in CI.
