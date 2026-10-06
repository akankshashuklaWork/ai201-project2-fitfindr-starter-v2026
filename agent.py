"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

How the loop works, in one picture:

        parse the query
              │
              ▼
       search_listings ──── nothing found? ──►  put a helpful message in
              │                                 session["error"] and STOP
              │ found something                 (suggest_outfit never runs)
              ▼
       suggest_outfit
              │
              ▼
       create_fit_card
              │
              ▼
            done

    python agent.py          runs both example paths below
"""

import re  # regular expressions: used to pull a size and a price out of text

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable  # noqa: F401 — you'll use this in unit 4


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        # Added by me: the names of the steps the loop actually ran, in order.
        # After a happy run it holds all four names; after an empty search it
        # stops at "diagnose_empty_search". That makes "did the branch work?" a
        # thing you can read straight off the session.
        "steps": [],
    }


# ── step 1 helper: turning the user's sentence into search inputs ─────────────
#
# The tools want three separate things (description, size, max_price) but the
# user types one sentence: "vintage graphic tee under $30, size M". This is the
# "parse" step. I use regular expressions (patterns that find text), not the
# model, so it is free, instant and gives the same answer every time.

# "under $30", "below 30", "less than $25.50", "max $40", "up to 20", "<= $15"
PRICE_PHRASE = re.compile(
    r"(?:\b(?:under|below|less than|no more than|at most|up to|max(?:imum)?)|<=?)"
    r"\s*\$?\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

# A bare "$30" with no word in front of it. We treat that as a ceiling too.
DOLLAR_AMOUNT = re.compile(r"\$\s*(\d+(?:\.\d+)?)")

# "size M", "size 8", "size 8.5", "size XXS", "size W30", "size US 8"
SIZE_PHRASE = re.compile(
    r"\bsize\s+((?:us\s+)?[a-z0-9]+(?:\.\d+)?)",
    re.IGNORECASE,
)


def _parse_query(query: str) -> dict:
    """
    Split a plain-language request into the three inputs search_listings needs.

        "vintage graphic tee under $30, size M"
        → {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}

    A size or price the user didn't mention comes back as None, which tells
    search_listings "don't filter on this".
    """
    text = query

    # Find the size, then cut that phrase out of the text so the words "size M"
    # don't end up in the keywords.
    size = None
    size_match = SIZE_PHRASE.search(text)
    if size_match:
        size = size_match.group(1)
        text = text.replace(size_match.group(0), " ")

    # Same idea for the price. Try the "under $30" style first, then a bare "$30".
    max_price = None
    price_match = PRICE_PHRASE.search(text) or DOLLAR_AMOUNT.search(text)
    if price_match:
        max_price = float(price_match.group(1))
        text = text.replace(price_match.group(0), " ")

    # Whatever is left is the description. Tidy up spaces and stray punctuation.
    description = re.sub(r"\s+", " ", text).strip(" ,.;")

    # Cutting out "size M" can leave a dangling word behind:
    #     "90s track jacket in size M"  →  "90s track jacket in"
    # so remove small connector words from the END of the description.
    description = re.sub(
        r"(?:\b(?:in|for|at|and|with|a|an|under|below)\s*)+$", "", description
    ).strip(" ,.;")

    return {"description": description, "size": size, "max_price": max_price}


# ── step 4 helper: what to tell the user when nothing matched ─────────────────

def _explain_empty_search(parsed: dict) -> str:
    """
    Build the message shown when search_listings finds nothing.

    "No results" doesn't help anyone: it doesn't say what to try next. So this
    re-runs the search with the size and/or price filter taken away, to find out
    WHICH part of the request was too strict, and then says so.

    These extra searches are plain Python (no model calls), so they cost nothing.
    """
    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]

    # If there is nothing to search for, the fix is to say what they want.
    if not description:
        return (
            "I couldn't tell what you're looking for. Say what kind of item you "
            "want, for example 'denim jacket under $50' or 'platform sneakers "
            "size 8'."
        )

    # Rebuild the request in words, so the user sees what was actually searched.
    asked_for = description
    if size:
        asked_for += f" in size {size}"
    if max_price is not None:
        asked_for += f" under ${max_price:g}"   # :g turns 30.0 into "30"

    tips = []  # each tip is one thing the user could change

    # Was the SIZE the problem? Search again without it.
    if size:
        without_size = search_listings(description=description, size=None, max_price=max_price)
        if without_size:
            best = without_size[0]   # the tool sorts best-first
            tips.append(
                f"Try a different size. Without the size filter, the best match "
                f"is {best['title']} (size {best['size']}, ${best['price']:g})."
            )

    # Was the PRICE the problem? Search again without it.
    if max_price is not None:
        without_price = search_listings(description=description, size=size, max_price=None)
        if without_price:
            best = without_price[0]
            tips.append(
                f"Raise your price limit. The best match is {best['title']} "
                f"at ${best['price']:g}, above your ${max_price:g} limit."
            )

    # Neither filter alone fixed it, but maybe it is the two of them together.
    if size and max_price is not None and not tips:
        without_both = search_listings(description=description, size=None, max_price=None)
        if without_both:
            example = without_both[0]
            tips.append(
                f"Loosen both the size and the price. For example: "
                f"{example['title']} (${example['price']:g}, size {example['size']})."
            )

    # Still nothing: the keywords themselves match no listing.
    if not tips:
        tips.append(
            f"Try different keywords. Nothing in the listings matches "
            f"'{description}', even with the size and price limits removed. "
            f"Try the type of clothing, like 'jacket', 'jeans', 'dress' or "
            f"'sneakers'."
        )

    lines = [f"I couldn't find anything for '{asked_for}'.", "Here's what you could change:"]
    lines += [f"  - {tip}" for tip in tips]
    return "\n".join(lines)


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    How it works: `next_step` holds the name of the step to run. Each time round
    the `while` loop we run that one step, and the step itself decides what
    `next_step` becomes, based on what it just got back. That is the whole idea
    of a planning loop: the result of this step picks the next step.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    next_step = "parse"   # where the loop starts
    loops = 0             # how many times we have been round the loop

    while next_step != "done":

        # Safety net: if a bug ever makes the loop go round forever, this stops
        # it with a clear error once `loops` passes MAX_ITERATIONS (config.py).
        # This run only needs four trips, so you should never see it fire.
        loops += 1
        trace.check_iterations(loops)

        # ── Step: parse ──────────────────────────────────────────────────────
        if next_step == "parse":
            session["parsed"] = _parse_query(session["query"])
            session["steps"].append("parse_query")
            next_step = "search"

        # ── Step: search (this one contains THE BRANCH) ──────────────────────
        elif next_step == "search":
            parsed = session["parsed"]
            results = search_listings(
                description=parsed["description"],
                size=parsed["size"],
                max_price=parsed["max_price"],
            )
            session["search_results"] = results
            session["steps"].append("search_listings")

            # Debugging tip: if this branch ever does something you didn't
            # expect, print what it is checking, right here, before the `if`:
            #     print("DEBUG results =", repr(results))

            # ┌──────────────────────────────────────────────────────────────┐
            # │ THE BRANCH. An empty list is "falsy" in Python, so            │
            # │ `not results` is True exactly when nothing matched.           │
            # └──────────────────────────────────────────────────────────────┘
            if not results:
                # Path A — nothing found. Explain what to change, then stop.
                # We do NOT call suggest_outfit with nothing to style.
                session["steps"].append("diagnose_empty_search")
                session["error"] = _explain_empty_search(parsed)
                next_step = "done"
            else:
                # Path B — found something. Pick the best match (the tool sorts
                # best-first, so that is results[0]) and save it in the session.
                session["selected_item"] = results[0]
                next_step = "outfit"

        # ── Step: outfit ─────────────────────────────────────────────────────
        elif next_step == "outfit":
            # Notice both inputs come OUT OF THE SESSION, not from a variable
            # left over from the search step. That is the "session state" rule.
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"],
                session["wardrobe"],
            )
            session["steps"].append("suggest_outfit")
            next_step = "fit_card"

        # ── Step: fit card ───────────────────────────────────────────────────
        elif next_step == "fit_card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"],
                session["selected_item"],
            )
            session["steps"].append("create_fit_card")
            next_step = "done"

        # ── Anything else is a typo in this function, so fail loudly ─────────
        else:
            raise ValueError(f"run_agent was told to run an unknown step: {next_step!r}")

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        print(f"  steps run: {session['steps']}")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")
    print(f"  steps run: {session['steps']}")


def _print_session(session: dict) -> None:
    """Print the whole session, so you can check the state with your own eyes.
    (The wardrobe and the long search list are shortened to keep it readable.)"""
    import json

    shown = dict(session)
    shown["wardrobe"] = f"<{len(session['wardrobe'].get('items', []))} wardrobe items>"
    shown["search_results"] = [
        f"{r['id']}: {r['title']}" for r in session["search_results"]
    ]
    print(json.dumps(shown, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    happy = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    _show(happy)
    print("\n--- the session at the end (Milestone 5: check selected_item) ---")
    _print_session(happy)

    print("\n=== A query it can't ===")
    sad = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    _show(sad)

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
