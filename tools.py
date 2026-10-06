"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

How this file is organised, top to bottom:

    1. Imports and a few settings (the filler-word list, the fallback messages)
    2. Small helper functions that search_listings uses
    3. Tool 1: search_listings   (plain Python, no model)
    4. Small helper functions that the two model tools use
    5. Tool 2: suggest_outfit    (calls the model)
    6. Tool 3: create_fit_card   (calls the model)

The exact inputs, outputs and "what happens when there is nothing" for each
tool are written down in the README under **Tool Inventory**.
"""

import re  # "regular expressions": lets us split text into words

import config
from generate import generate
from utils.data_loader import load_listings


# ══════════════════════════════════════════════════════════════════════════════
# Settings used in this file
# ══════════════════════════════════════════════════════════════════════════════

# Words that appear in almost every search and say nothing about the clothes.
# If we kept them, "a vintage tee for me" would "match" any listing whose text
# happens to contain "a" or "for". So we throw them away before searching.
FILLER_WORDS = {
    "a", "an", "the", "and", "or", "of", "for", "in", "on", "to", "with",
    "i", "me", "my", "im", "is", "it", "that", "any", "some", "something",
    "looking", "look", "want", "need", "find", "show", "get", "please",
    "under", "below", "over", "than", "less", "max", "most", "up", "at",
    "size", "dollar", "dollars", "bucks", "usd",
}

# People say "medium", listings say "M". This turns the long word into the
# short one so that a search for size "medium" still finds size "M".
SIZE_NAMES = {"small": "s", "medium": "m", "large": "l"}

# Shown instead of a real answer when the model sends back nothing at all.
# (This can happen, for example, when its safety filter blocks a reply.)
NO_OUTFIT_MESSAGE = (
    "The model didn't send back any outfit ideas this time. Try asking again."
)
NO_CARD_MESSAGE = (
    "The model didn't send back a caption this time. Try asking again."
)
# Shown by create_fit_card when it is handed an empty outfit.
NO_OUTFIT_TO_WRITE_ABOUT = (
    "Can't write a fit card yet: there's no outfit to build the caption around."
)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers for search_listings
# ══════════════════════════════════════════════════════════════════════════════

def _split_into_words(text: str) -> list[str]:
    """
    Lowercase some text and cut it into words. Only letters and digits are kept,
    so punctuation disappears.

        "Vintage Levi's 501 Jeans — Medium Wash"
        → ["vintage", "levi", "s", "501", "jeans", "medium", "wash"]
    """
    return re.findall(r"[a-z0-9]+", text.lower())


def _ignore_plural(word: str) -> str:
    """
    Make "tees" and "tee" count as the same word by chopping a plural "s" off.

    We run BOTH the search words and the listing words through this, so they
    always get treated the same way. That is why a crude rule is good enough.

        "tees"    → "tee"      "jeans"  → "jean"      "dresses" → "dress"
        "dress"   → "dress"    "90s"    → "90s"       (too short to chop)

    Words ending in "ss" or "us" are left alone because that "s" is not a plural
    ("dress", "bus").
    """
    if word.endswith("sses"):          # dresses → dress
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us")):
        return word[:-1]
    return word


def _keywords_from(description: str) -> list[str]:
    """
    Turn what the user typed into the list of words worth searching for.

        "a vintage graphic tees"  →  ["vintage", "graphic", "tee"]

    Steps: split into words, drop one-letter words and filler words, ignore
    plurals, and remove repeats (keeping the order).
    """
    keywords = []
    for word in _split_into_words(description):
        if len(word) < 2 or word in FILLER_WORDS:
            continue
        word = _ignore_plural(word)
        if word not in keywords:       # skip repeats
            keywords.append(word)
    return keywords


def _size_pieces(size_text: str) -> set[str]:
    """
    Break a size into its whole pieces, so we can compare whole pieces instead
    of letters.

        "S/M"            → {"s", "m"}
        "XL (oversized)" → {"xl", "oversized"}
        "US 8.5"         → {"us", "8.5"}
        "W30 L30"        → {"w30", "l30"}

    Why not just check `"m" in listing_size`? Because that is also True for
    "One Size / Oversized"... and `"s" in "us 9"` is True too. Comparing whole
    pieces avoids those false matches. (The "." is kept so 8.5 stays one piece.)
    """
    pieces = set(re.findall(r"[a-z0-9.]+", size_text.lower()))
    # Turn "medium" into "m" (and so on) on the user's side.
    return {SIZE_NAMES.get(piece, piece) for piece in pieces}


def _size_matches(wanted_size: str, listing_size: str) -> bool:
    """
    True when every piece of the size the user asked for appears in the listing's
    size.

        wanted "M"  vs listing "S/M"    → True   ("m" is one of {"s", "m"})
        wanted "M"  vs listing "XL"     → False
        wanted "8"  vs listing "US 8"   → True
        wanted "8"  vs listing "US 8.5" → False  ("8" is not the piece "8.5")
    """
    wanted = _size_pieces(wanted_size)
    if not wanted:                      # e.g. the user typed only punctuation
        return True
    return wanted.issubset(_size_pieces(listing_size))


def _score_listing(listing: dict, keywords: list[str]) -> int:
    """
    Score how well one listing matches the keywords. Higher is better, and 0
    means "not a match at all".

    Each keyword is worth:
        2 points  if it is in the title  (the title is what the listing IS)
        1 point   if it is only elsewhere (description, tags, category, colors,
                  brand)
    """
    title_words = {_ignore_plural(w) for w in _split_into_words(listing["title"])}

    # Gather all the other text we are willing to search. Note `or ""`: for
    # most listings `brand` is None, and None has no .lower() — without this
    # one little guard the search would crash on 32 of the 40 listings.
    other_text = " ".join([
        listing["description"],
        " ".join(listing["style_tags"]),
        listing["category"],
        " ".join(listing["colors"]),
        listing["brand"] or "",
    ])
    other_words = {_ignore_plural(w) for w in _split_into_words(other_text)}

    score = 0
    for keyword in keywords:
        if keyword in title_words:
            score += 2
        elif keyword in other_words:
            score += 1
    return score


# ══════════════════════════════════════════════════════════════════════════════
# Tool 1: search_listings
# ══════════════════════════════════════════════════════════════════════════════

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Matched case-insensitively and by WHOLE pieces — "M" matches
                     "M" and "S/M" but not "XL" or "US 9". See _size_matches.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first (at most
        config.SEARCH_RESULT_LIMIT of them).
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Test it from a terminal:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    # Step 1: load every listing. (Always use the loader, never open the file
    # yourself — if the data ever moves, only the loader has to change.)
    all_listings = load_listings()

    # Step 2: turn the description into a clean list of keywords.
    keywords = _keywords_from(description)

    # Step 3: go through the listings one at a time. A listing has to survive
    # three gates: the price, the size, and having a keyword score above zero.
    matches = []  # will hold (score, listing) pairs
    for listing in all_listings:

        # Gate 1 — price. `is not None` matters: max_price=0 is a real (if
        # unlikely) ceiling, and a plain `if max_price:` would ignore it.
        if max_price is not None and listing["price"] > max_price:
            continue  # too expensive: skip to the next listing

        # Gate 2 — size. Only check when the caller gave us a size.
        if size and not _size_matches(size, listing["size"]):
            continue  # wrong size: skip to the next listing

        # Gate 3 — keywords. A score of 0 means no keyword was found anywhere.
        score = _score_listing(listing, keywords)
        if score == 0:
            continue  # nothing in common with the search: skip

        matches.append((score, listing))

    # Step 4: best match first. We sort by score (highest first), and if two
    # listings tie, the cheaper one goes first. The minus sign on the score is
    # the trick: Python sorts small → large, so -5 comes before -2.
    matches.sort(key=lambda pair: (-pair[0], pair[1]["price"]))

    # Step 5: hand back just the listings (drop the scores), capped at the limit.
    # If `matches` is empty this is simply [] — exactly what the spec promises.
    return [listing for _score, listing in matches[: config.SEARCH_RESULT_LIMIT]]


# ══════════════════════════════════════════════════════════════════════════════
# Helpers for the two model tools
# ══════════════════════════════════════════════════════════════════════════════

def _format_price(price) -> str:
    """24.0 → "$24", 24.5 → "$24.50". Whole prices look nicer without ".00"."""
    if price is None:
        return "an unknown price"
    if float(price) == int(price):
        return f"${int(price)}"
    return f"${price:.2f}"


def _describe_listing(item: dict) -> str:
    """
    Turn a listing dict into a few readable lines for a prompt. A model reads
    sentences far better than it reads a raw Python dict.
    """
    lines = [
        f"- Title: {item.get('title')}",
        f"- Category: {item.get('category')}",
        f"- Colors: {', '.join(item.get('colors') or [])}",
        f"- Style: {', '.join(item.get('style_tags') or [])}",
        f"- Size: {item.get('size')}",
        f"- Condition: {item.get('condition')}",
        f"- Price: {_format_price(item.get('price'))} on {item.get('platform')}",
    ]
    # Brand is None for most listings, so only mention it when there is one.
    if item.get("brand"):
        lines.append(f"- Brand: {item['brand']}")
    return "\n".join(lines)


def _describe_wardrobe_item(piece: dict) -> str:
    """One wardrobe item as one line, e.g.
    '- White ribbed tank top (tops; white; basics, minimal) — Goes with everything'"""
    line = (
        f"- {piece.get('name')} "
        f"({piece.get('category')}; "
        f"{', '.join(piece.get('colors') or [])}; "
        f"{', '.join(piece.get('style_tags') or [])})"
    )
    if piece.get("notes"):             # notes is None for many items
        line += f" — {piece['notes']}"
    return line


# ══════════════════════════════════════════════════════════════════════════════
# Tool 2: suggest_outfit
# ══════════════════════════════════════════════════════════════════════════════

# The "system" message sets how the model behaves for every request. The prompt
# (built below) is the specific question. Keeping the rules here means we don't
# repeat them twice.
OUTFIT_SYSTEM = (
    "You are a friendly personal stylist who helps people style secondhand "
    "finds. Be specific and practical. Write plain text only: no markdown "
    "headings, no tables, no bullet-point walls."
)


def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handled below.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, it returns general styling advice rather than
        raising or returning "".

    Test it from a terminal:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    # Pull the list of wardrobe pieces out safely. `(wardrobe or {})` copes with
    # wardrobe being None, and the final `or []` copes with a missing/None list.
    pieces = (wardrobe or {}).get("items") or []

    item_text = _describe_listing(new_item)

    if not pieces:
        # ── Empty wardrobe: we know nothing about what the user owns, so ask
        # for general advice. We must NOT let the model pretend it knows.
        prompt = (
            "A shopper is thinking about buying this thrifted item:\n"
            f"{item_text}\n\n"
            "They haven't told us what else they own. Give general styling "
            "advice: suggest one or two outfits described in general terms "
            "(for example 'straight-leg jeans and white sneakers'), and say "
            "what colors and styles pair well with it.\n"
            "Do not pretend to know what is in their closet. "
            "Keep it under 120 words."
        )
    else:
        # ── Wardrobe with items: ask for outfits built from what they own.
        wardrobe_text = "\n".join(_describe_wardrobe_item(p) for p in pieces)
        prompt = (
            "A shopper is thinking about buying this thrifted item:\n"
            f"{item_text}\n\n"
            "Here is everything in their wardrobe:\n"
            f"{wardrobe_text}\n\n"
            "Suggest one or two outfits that combine the thrifted item with "
            "pieces from this wardrobe.\n"
            "Rules:\n"
            "- Name wardrobe pieces by their exact name from the list above.\n"
            "- Only use pieces from the list. Don't invent clothes they don't own.\n"
            "- Say briefly why each outfit works (color, shape or vibe).\n"
            "- Keep it under 120 words."
        )

    text = generate(prompt, system=OUTFIT_SYSTEM)

    # The model can occasionally return nothing. Our spec promises a non-empty
    # string, so fall back to a message rather than returning "".
    return text.strip() or NO_OUTFIT_MESSAGE


# ══════════════════════════════════════════════════════════════════════════════
# Tool 3: create_fit_card
# ══════════════════════════════════════════════════════════════════════════════

CARD_SYSTEM = (
    "You write short, authentic social media captions for thrift hauls. You "
    "sound like a real person posting a find they're excited about, never like "
    "a product listing or an ad. Plain text only."
)


def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, it returns a descriptive message
        rather than raising (and doesn't spend a model call).

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    Same input, different words: this runs at config.TEMPERATURE (0.9) so the
    model varies. If three runs on the same item come out identical, it's one
    of two things, both in config.py:

        • CACHE_ENABLED — the adapter handed back an answer it already had
          (set AI201_CACHE=0 in your terminal to see real variation)
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    Test it from a terminal:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    # Guard first: with nothing to write about, don't waste a model call.
    # `not outfit` catches None and "", and .strip() catches "   ".
    if not outfit or not outfit.strip():
        return NO_OUTFIT_TO_WRITE_ABOUT

    prompt = (
        "Write a caption for a social media post about this thrift find.\n\n"
        "The find:\n"
        f"{_describe_listing(new_item)}\n\n"
        "The outfit idea:\n"
        f"{outfit}\n\n"
        "Rules:\n"
        "- Two to four sentences. No more.\n"
        "- Sound like a real person posting, not a product description.\n"
        "- Mention the item, its price and the platform it came from, "
        "once each.\n"
        "- Be specific about the vibe (a mood, a place, an era), not generic.\n"
        "- At most two emoji. A hashtag or two is fine.\n"
        "- Don't put quotation marks around the caption."
    )

    text = generate(prompt, system=CARD_SYSTEM)

    # Same safety net as suggest_outfit. Also strip quotes the model sometimes
    # wraps around the caption even though we asked it not to.
    return text.strip().strip('"') or NO_CARD_MESSAGE
