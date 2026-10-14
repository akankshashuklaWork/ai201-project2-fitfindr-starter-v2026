"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
    # Criteria 3 and 4 both need "five DIFFERENT items", not one item run five
    # times — criterion 3 is plain Python (no randomness, so repeating one
    # query would just prove the code agrees with itself, not that it works
    # across items) and criterion 4's price-in-digits check needs real variety
    # too. So instead of one scenario run five times, these are five separate
    # scenarios, each a different matching query. Each full run produces both
    # the session state criterion 3 checks AND the fit card criterion 4
    # checks, so the run log's "Try 1"-"Try 5" for these two rows map to these
    # five queries (one try each) instead of five repeats of one query.
    {
        "name": "criteria 3+4, item 1: vintage levi jeans",
        "query": "vintage levi jeans",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        "name": "criteria 3+4, item 2: platform mary janes",
        "query": "platform mary janes",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        "name": "criteria 3+4, item 3: leather bomber jacket",
        "query": "leather bomber jacket",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        "name": "criteria 3+4, item 4: silk button-down shirt",
        "query": "silk button-down shirt",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        "name": "criteria 3+4, item 5: tie-dye long sleeve",
        "query": "tie-dye long sleeve",
        "wardrobe": "example",
        "criterion": 3,
    },

    # Criterion 5 needs the SAME price ceiling worded five different ways, to
    # see whether the parser (a regex in agent.py, not the model) catches the
    # ceiling no matter how it's phrased. "jeans" matches three listings
    # ($38, $36, $30), so a $35 ceiling is a real test: only the $30 one
    # should survive. One wording ("thirty five dollars") has no digits in it
    # on purpose — that's the one I expect the regex to miss.
    {
        "name": "criterion 5, wording 1: under $35",
        "query": "jeans under $35",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        "name": "criterion 5, wording 2: $35 max",
        "query": "jeans, $35 max",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        "name": "criterion 5, wording 3: no more than $35",
        "query": "jeans, no more than $35",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        "name": "criterion 5, wording 4: up to $35",
        "query": "jeans, up to $35",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        "name": "criterion 5, wording 5: under thirty five dollars",
        "query": "jeans, under thirty five dollars",
        "wardrobe": "example",
        "criterion": 5,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
