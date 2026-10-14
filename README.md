# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr is a small thrifting agent. You type what you want in plain language,
like `vintage graphic tee under $30, size M`. It searches 40 secondhand listings
for the best match, asks a model how that item would go with the clothes in your
wardrobe, and then writes a short caption you could post about the find. If
nothing matches, it doesn't carry on with nothing: it stops and tells you what
to change (the size, the price limit, or the keywords).



---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Looks through the 40 listings in `data/listings.json` and
  returns the ones that match the keywords, the size and the price ceiling,
  best match first. It does not call the model.
- **Inputs:**
  - `description` (str): keywords, e.g. `"vintage graphic tee"`.
  - `size` (str or None): e.g. `"M"`. `None` means "don't filter by size".
  - `max_price` (float or None): the most the user will pay, **inclusive**
    (a $30.00 item matches `max_price=30`). `None` means "don't filter by price".
- **Returns:** A `list[dict]` of at most 10 listing dicts
  (`config.SEARCH_RESULT_LIMIT`). Each dict is a listing exactly as it is in
  the data file, with the fields `id`, `title`, `description`, `category`,
  `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list),
  `brand` (str or None) and `platform`. The best match is first.
  - *Size match rule:* the listing's size is split into whole pieces
    (`"S/M"` becomes `s` and `m`; `"US 8.5"` becomes `us` and `8.5`) and the
    requested size has to equal one piece, ignoring case. So `"M"` matches `M`,
    `S/M` and `M/L`, but never `XL`, `US 9` or `One Size`.
  - *Keyword score rule:* each distinct keyword scores 2 if it appears in the
    title, otherwise 1 if it appears in the description, tags, category, colors
    or brand. Filler words ("a", "for", "under"...) are ignored and a trailing
    plural "s" is ignored, so `tees` matches `tee`. Score 0 means not a match.
    Ties go to the cheaper listing.
- **When it has nothing:** Returns an empty list, `[]`. Never `None`, never an
  exception. The loop branches on this.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfit ideas that put the
  thrifted item together with pieces from the user's wardrobe.
- **Inputs:**
  - `new_item` (dict): one listing dict, the same shape `search_listings`
    returns.
  - `wardrobe` (dict): `{"items": [...]}` where each item has `id`, `name`,
    `category`, `colors`, `style_tags` and `notes`.
- **Returns:** A non-empty `str` of plain text: one or two outfits. When the
  wardrobe has items, every outfit names pieces the user owns by their `name`
  from the wardrobe, and the prompt tells the model not to invent pieces.
- **When it has nothing:** There are two "nothing" cases.
  - *Empty wardrobe* (`{"items": []}`): not an error. It returns general styling
    advice for the item (what kinds of pieces go with it), still a non-empty
    string.
  - *Model sends back blank text:* returns a fixed one-sentence message saying
    no outfit ideas came back, never `""`.

### `create_fit_card`

- **What it does:** Asks the model to write a short social-media caption about
  the find, using the outfit idea.
- **Inputs:**
  - `outfit` (str): the text that `suggest_outfit` returned.
  - `new_item` (dict): one listing dict (the same item that went into
    `suggest_outfit`).
- **Returns:** A `str` caption of two to four sentences. It names the item, its
  price and its platform once each, and reads like a real post rather than a
  product description. It is different from run to run (temperature 0.9).
- **When it has nothing:** If `outfit` is `""` or only whitespace, it returns a
  fixed message string saying there is no outfit to write about and does **not**
  call the model. If the model sends back blank text, it returns a fixed
  one-sentence message saying so. It never raises.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in
`session["error"]` that names what the user could change (the size, the price
ceiling, or the keywords) and stop, leaving `outfit_suggestion` and `fit_card`
as `None`. Otherwise, put the first result in `session["selected_item"]` and go
on to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** With regular expressions, not the model
(`agent.py::_parse_query`). It looks for a phrase like `size M` or `size 8.5`
for the size, and a phrase like `under $30`, `max 40` or a bare `$30` for the
price. Both phrases are cut out, and whatever is left becomes the description.
A size or price that isn't mentioned stays `None`. Known limits: a size is only
found after the word "size" (a bare "M" is not read as a size), and "medium" or
"large" count as sizes only when they follow the word "size".

**What moves through the session:** In order:
1. `parsed` (description, size, max_price) from `_parse_query`
2. `search_results` (the list from `search_listings`)
3. `selected_item` (the first result, only if the list wasn't empty)
4. `outfit_suggestion` (from `suggest_outfit`, which reads `selected_item` and
   `wardrobe` out of the session)
5. `fit_card` (from `create_fit_card`, which reads `outfit_suggestion` and
   `selected_item` out of the session)

`error` is set only when the search is empty. I also added a `steps` field: the
names of the steps the loop ran, in order. A full run gives
`['parse_query', 'search_listings', 'suggest_outfit', 'create_fit_card']`; an
empty search gives `['parse_query', 'search_listings', 'diagnose_empty_search']`,
so the branch is visible in the session.

**What the loop looks like:** a `while` loop in `run_agent`. A variable called
`next_step` holds the name of the step to run, and each step decides what
`next_step` becomes based on what it just got back. The branch is the
`if not results:` line in the `search` step. `trace.check_iterations` runs on
every pass as the stop condition.

**The empty-search message:** `agent.py::_explain_empty_search` re-runs the
search with the size filter removed, then with the price filter removed, to
find which one was too strict, and says so (for example "Raise your price
limit. The best match is ... at $48, above your $10 limit."). If neither filter
is the cause, it asks for different keywords. These extra searches are plain
Python, so they use no model calls.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Vintage Band Tee — Faded Grey — $19.0 on depop

  Outfit:   Hey there! For nineteen dollars, this faded grey band tee is a total win. Since it is a size large, you have some great slouchy proportions to play with.

Outfit one pairs the band tee with your baggy straight-leg jeans, dark wash and black combat boots. Throw your vintage black denim jacket on top and add the black crossbody bag. This works because the relaxed graphic tee and chunky boots lean right into that effortless grunge vibe while the dark denim ties the whole look together.

Outfit two tucks the band tee into your wide-leg khaki trousers. Cinch the waist with your brown leather belt and slip on your chunky white sneakers. This balances the casual streetwear feel of the top with clean earth tones for an easy, high-low look.

  Fit card: Found this perfectly faded grey band tee on Depop for nineteen bucks and it has the absolute best 90s skater grunge energy. Going to live in this oversized fit all fall, whether it's thrown on with combat boots or tucked into baggy trousers. 🎸✨ #thrifted #grunge

2 model calls this session, 789 prompt + 215 output tokens
```

The same agent on a query nothing can match. It stops after the search, so
there is no outfit and no fit card (`fit_card` stays `None`, and no model calls
are made):

```
$ python app.py ask 'designer ballgown size XXS under $5'

  I couldn't find anything for 'designer ballgown in size XXS under $5'.
Here's what you could change:
  - Try different keywords. Nothing in the listings matches 'designer ballgown', even with the size and price limits removed. Try the type of clothing, like 'jacket', 'jeans', 'dress' or 'sneakers'.

0 model calls this session
```

The session after a happy-path run (from `python agent.py`, shortened with `...`),
showing which item was selected and which steps ran. The full session printout is
produced by `python agent.py`:

```
  steps run: ['parse_query', 'search_listings', 'suggest_outfit', 'create_fit_card']
  "selected_item": { "id": "lst_033", "title": "Vintage Band Tee — Faded Grey", "price": 19.0, ... }
  "error": null
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print([(r['title'], r['price'], r['size']) for r in search_listings('graphic tee', max_price=30)])"
[('Graphic Tee — 2003 Tour Bootleg Style', 24.0, 'L'), ('Y2K Baby Tee — Butterfly Print', 18.0, 'S/M'), ('Vintage Band Tee — Faded Grey', 19.0, 'L'), ('Mesh Long-Sleeve Top — Black', 15.0, 'S/M'), ('Vintage Graphic Hoodie — Faded Black', 26.0, 'L'), ('Oversized Crewneck Sweatshirt — Vintage Navy', 20.0, 'XL (fits oversized)'), ('Low-Rise Cargo Pants — Khaki', 27.0, 'W29')]
```

The empty case of the same tool (nothing matches, so it returns an empty list,
not `None`):

```
$ python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
[]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[5], get_example_wardrobe()))"
Hey there! That 2003 tour bootleg tee is such a cool find for twenty-four bucks. Here are two ways to style it using what you already own.

First, pair the graphic tee with your baggy straight-leg jeans, dark wash and black combat boots. Layer the vintage black denim jacket on top and finish with the black crossbody bag. This works because it plays right into the grungy streetwear vibe, balancing the high waist of the jeans with the boxy tee.

Second, try tucking the tee into your wide-leg khaki trousers and adding the chunky white sneakers and brown leather belt. This creates a great contrast between the edgy top and crisp, minimal trousers for an effortless everyday look.
```

The empty-wardrobe case of the same tool. It gives general advice instead of
failing, and doesn't name any pieces because it doesn't know what the user owns:

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[5], get_empty_wardrobe()))"
That 2003 tour tee is an absolute score for twenty-four bucks. Since it has that worn-in grunge feel and a relaxed large fit, you can easily build some great streetwear looks with it.

Try pairing it with baggy light-wash denim and chunky black skate shoes for an effortless nineties vibe. Another cool option is tucking it into a plaid pleated mini skirt with black combat boots and sheer tights.

Stick to a color palette of blacks, whites, grays, and denim blues to keep the focus on the graphic. To elevate the style, throw on an oversized leather biker jacket or a distressed denim vest. Silver chain necklaces and a worn beanie will finish the outfit off perfectly.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Obsessed with how perfectly broken-in these vintage Levi's are for running errands in the Lower East Side. Snagged them on depop for $38 and I'm living in them with my beat-up white sneakers all fall. 👖✨ #thriftfinds
```

The Milestone 4 variation check: the same `create_fit_card` call three times.
With the cache on (the default) the three answers were word-for-word identical,
because the starter hands back the answer it already has for an identical
prompt. With `AI201_CACHE=0` they were three different captions:

```
$ AI201_CACHE=0 python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Finally tracked down the holy grail of slouchy 90s denim with these vintage Levi's. Snagged them on Depop for thirty eight bucks and the wash is just completely unmatched. Gonna live in these with beat-up white sneakers for Sunday morning coffee runs. #vintagelevis

Finally found the perfect pair of vintage Levi's 501s and they fit like an absolute dream for lazy Saturday coffee runs. Snagged them on depop for thirty-eight bucks and honestly, nothing beats that broken-in 90s denim feel. Just throwing these on with beat-up white sneakers and a plain tee and I'm out the door. #thriftedstyle

Finally tracked down the holy grail of 90s skater denim on Depop. These vintage Levi's 501s were thirty-eight bucks and fit like an absolute dream. Just gonna live in these with beat-up white sneakers all through autumn. 👖✨ #thrifted #grunge
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1: the message for an empty search**

- *What I asked for:* I gave Claude the assignment and asked it to help me build
  the planning loop with beginner-friendly comments. Milestone 5 says the
  message for an empty search must name what the user could change, so "No
  results" isn't enough.
- *What came back:* A loop whose branch (`if not results`) sets
  `session["error"]` using a helper, `_explain_empty_search`, that re-runs the
  search without the size filter and then without the price filter to find which
  one was too strict. When Claude ran it on test queries, it found two
  problems. The parser left a dangling word, so "90s track jacket in size M"
  produced a message saying "in in size M". And the tips pointed at loose
  matches: it suggested a bucket hat for a track-jacket search, and the price tip
  used the cheapest match, which was a slip dress.
- *What I changed:* The parser now strips small connector words ("in", "for",
  "a") from the end of the description. The two tips now name the best match
  with its title, size and price, so the user can see what the advice is pointing
  at. (Claude made these changes in `agent.py`.)

**Moment 2: the fit card prices**

- *What I asked for:* `create_fit_card`, a caption that mentions the item, its
  price and its platform once each, and then the Milestone 4 check of running it
  three times on the same item.
- *What came back:* Three word-for-word identical captions, because the
  starter's cache was handing back the same answer. With `AI201_CACHE=0` they
  were three different captions. But across the five distinct captions Claude
  generated, only one wrote the price in digits ("$38"). The others wrote it as
  words ("thirty eight bucks", "nineteen bucks").
- *What I changed:* I left the prompt as it is on purpose, and turned the problem
  into criterion 4 in `criteria.md` (the card must show the price in digits, in
  5 of 5 cards), so Unit 4 can test and diagnose it.

**A note on `criteria.md`:** I chose the targets (for example 5 of 5 across five
different queries for criterion 3, and testing the whole agent for criterion 5)
and the reasons came from my answers. Claude wrote the wording from my choices.
Claude also found, when asked to attack the criteria, the places where a tester
would have to guess (for example what counts as a "try").

**Moment 3: the whole of unit 4**

- *What I asked for:* I gave Claude this unit's assignment doc and asked it to
  do the work end to end: move a tool onto MCP, trigger the three failure
  modes, run my five criteria five tries each, diagnose the misses, pick and
  make one improvement, and write it all up.
- *What came back:* `search_listings` registered in `mcp_server.py` and
  wired through `mcp_client.call_tool` in `agent.py`, trace calls on every
  step, and a handler for `ModelUnavailable` (the other two failure modes —
  empty search, empty wardrobe — already worked from unit 3). For criteria 3
  and 4, Claude pointed out that my criteria ask for five *different* items,
  not one item run five times, and wrote five scenarios instead of relying
  on `run_eval.py`'s default of repeating one scenario — I checked this
  against my own wording in `criteria.md` and it's right. The real test run
  found two misses: fit cards sometimes wrote the price in words instead of
  digits (criterion 4, 3/5), and the price-ceiling parser missed a request
  worded with no digits at all ("under thirty five dollars", criterion 5,
  4/5). Claude's diagnosis tied both to the same root idea — numbers as
  words instead of digits — showing up on two different sides of the agent
  (the model's output vs. the regex parser).
- *What I changed:* I agreed with picking the criterion 4 fix (one line
  added to the fit-card prompt, telling the model to always use digits) over
  the criterion 5 fix, because a word-to-number parser is more lines and
  more edge cases than I could carefully check in one pass, and the unit
  only allows one change. Re-running all five criteria after the fix showed
  criterion 4 moved to 5/5 and nothing else moved — both run logs below are
  the real output from those two runs, not simulated or written from
  description.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

For criteria 1 and 2, "five tries" means the SAME query run five separate
times — that's what those two criteria actually test (does it hold up on
repeat runs). For criteria 3, 4 and 5, "five tries" means five DIFFERENT
inputs (five different items, or the same price ceiling worded five
different ways) — repeating one item five times would only show the code
agrees with itself, not that it works across items. Criteria 3 and 4 are
measured off the same five runs, since one full run produces both the
session state criterion 3 checks and the fit card criterion 4 checks.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before 2nd tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected item is the item passed to suggest_outfit | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card shows the price in digits | 5 of 5 | FAIL | PASS | PASS | PASS | FAIL | MISSED (3/5) |
| 5. Price ceiling respected, however worded | 5 of 5 | PASS | PASS | PASS | PASS | FAIL | MISSED (4/5) |

For row 3/4, Try 1–5 are the five different items: vintage Levi's jeans
($38), platform Mary Janes ($55), leather bomber jacket ($75), silk
button-down ($28), tie-dye long sleeve ($17).
For row 5, Try 1–5 are the five different wordings of a $35 ceiling: "under
$35", "$35 max", "no more than $35", "up to $35", "under thirty five
dollars".

**Real output from one try each**, naming the file and function that
produced it:

**Criterion 1** — `agent.py::run_agent`, try 1, query `"vintage graphic tee
under $30"`:

```
Found:    Vintage Band Tee — Faded Grey — $19.0 on depop
Outfit:   Hey there! That faded grey band tee is an amazing find, and at
nineteen dollars, it is totally worth grabbing...
Fit card: Found this perfectly worn-in grey band tee on depop for $19 and I
am obsessed. The fade is totally earned and...
steps run: ['parse_query', 'search_listings (via MCP)', 'suggest_outfit',
'create_fit_card']
```

**Criterion 2** — `agent.py::_explain_empty_search`, try 1, query
`"designer ballgown size XXS under $5"`:

```
I couldn't find anything for 'designer ballgown in size XXS under $5'.
Here's what you could change:
  - Try different keywords. Nothing in the listings matches 'designer
    ballgown', even with the size and price limits removed. Try the type
    of clothing, like 'jacket', 'jeans', 'dress' or 'sneakers'.
steps run: ['parse_query', 'search_listings (via MCP)', 'diagnose_empty_search']
```

**Criterion 3** — `agent.py::run_agent`, item 1 ("vintage levi jeans"):
`session["selected_item"]["id"]` was `lst_001`, and the trace line right
below it shows `suggest_outfit`'s input was `Vintage Levi's 501 Jeans —
Medium Wash ($38.0, depop)` — the same listing, same id. True for all 5
items.

**Criterion 4** — `tools.py::create_fit_card`, the two FAILs:

```
item 1 (vintage Levi's, $38): "scored these broken-in 501s for
thirty-eight bucks on depop and honestly my search for the perfect
mid-90s str..."

item 5 (tie-dye long sleeve, $17): "Scored this pastel tie-dye long sleeve
on depop for seventeen bucks and I'm obsessed with the dreamy 90s skate..."
```

**Criterion 5** — `tools.py::search_listings` (called via MCP), wording 5
("jeans, under thirty five dollars"):

```
search_results prices: [30.0, 36.0, 38.0]
```
Two of those three — $36 and $38 — are over the $35 ceiling the user typed.

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | Matching query completes all three tools | 4 of 5 | MET (5/5) | Ran the same matching query 5 times with caching off; all 5 ran parse → search → outfit → fit card and returned a non-empty fit card. 5 ≥ 4, so it's met. |
| 2 | Impossible query stops before 2nd tool | 5 of 5 | MET (5/5) | Ran the same impossible query 5 times; `search_listings` returned `[]` all 5 times and the loop stopped at `diagnose_empty_search` — `suggest_outfit` never ran (checked `session["steps"]`). |
| 3 | Selected item is the item passed to suggest_outfit | 5 of 5 | MET (5/5) | Ran 5 different matching queries; for each, compared `session["selected_item"]["id"]` against the item `suggest_outfit` was actually called with (visible in the trace). All 5 matched. |
| 4 | Fit card shows the price in digits | 5 of 5 | MISSED (3/5) | Ran 5 different items once each, read the fit card text, and checked for a `$<number>` pattern instead of a spelled-out price. 2 of 5 ("thirty-eight bucks", "seventeen bucks") failed. 3 < 5, so it's missed. |
| 5 | Price ceiling respected, however worded | 5 of 5 | MISSED (4/5) | Ran the same $35 ceiling worded 5 different ways, and checked every price in `session["search_results"]` against $35. 4 wordings held; "under thirty five dollars" let two over-budget listings through. 4 < 5, so it's missed. |

**Diagnoses**

**Criterion 4 — fit card price in words.** Tool: `create_fit_card`
(`tools.py`). Mechanism: `create_fit_card`'s prompt tells the model to
mention the price, but never says what *format* to write it in, so the
model is free to pick — most of the time it chose digits ("$19", "$42"),
but on 2 of 5 items it chose words ("thirty-eight bucks", "seventeen
bucks"). This isn't a code bug: the tool receives and forwards the correct
price every time (confirmed by checking `new_item["price"]` against what's
in the prompt). It's a prompt gap — nothing constrains the model's
*phrasing* of a number it was handed correctly. No pattern by item price
size (a $38 item and a $17 item both failed, a $55 item and a $28 item
both passed) — this reads as the model's free choice of tone on a given
generation, not something tied to the data.

**Criterion 5 — price ceiling missed for word-written numbers.** Loop
branch: the parser in `agent.py::_parse_query`, specifically the
`PRICE_PHRASE` / `DOLLAR_AMOUNT` regular expressions. Mechanism: both
regexes require at least one digit character (`\d+`) to recognize a price.
"under thirty five dollars" has no digits in it at all, so neither regex
matches, `max_price` comes back `None`, and `search_listings` runs with no
price filter — so all three "jeans" listings come back, including two over
the $35 the user actually said. The tool and the loop both did exactly
what they were told; the parser just never learned to read a price spelled
out in words.

**The pattern across both misses:** both are the same root idea — "a
number written as words instead of digits" — showing up on two different
sides of the agent. Criterion 4 is the *output* side (the model writes a
price in words). Criterion 5 is the *input* side (the regex can't read a
price written in words). Same theme, two different mechanisms, which is
why I could only cleanly fix one of them this unit without touching two
things at once.

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path** — `python app.py ask 'vintage graphic tee under $30' --trace`

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: 10 items: Vintage Band Tee — Faded Grey, Graphic Tee — 2003 Tour Bootleg Style, Y2K Baby Tee — Butterfly Print … +7 more
[3] suggest_outfit
      in:  Vintage Band Tee — Faded Grey ($19.0, depop)
      out: Hey there! For nineteen dollars, this faded grey band tee is a total win. Since it is a size large, you have s…
[4] create_fit_card
      in:  Hey there! For nineteen dollars, this faded grey band tee is a total win. Since it is a size large, you have s…
      out: Found this perfectly faded grey band tee on Depop for nineteen bucks and it has the absolute best 90s skater g…
```

**Empty search** — `python app.py ask 'designer ballgown size XXS under $5' --trace`

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: dict with keys: description, size, max_price
[2] search_listings (via MCP)
      in:  dict with keys: description, size, max_price
      out: [] (empty)
[3] diagnose_empty_search
      in:  dict with keys: description, size, max_price
      →    empty search, stopping before suggest_outfit
```

The empty-search trace stops after step 3 — `suggest_outfit` and
`create_fit_card` never run. The happy path runs all 4 steps. That
difference is the branch working.

**On the MCP move:** `search_listings` is registered as a tool in
`mcp_server.py` (name, one-line description, and typed inputs —
`description: str`, `size: str | None`, `max_price: float | None`). In
`agent.py::run_agent`, the direct call was swapped for
`mcp_client.call_tool("search_listings", {...})`, which starts the server
over stdio, calls the tool, and unwraps the JSON response back into the
same list of dicts `search_listings` always returned. The returned value
did **not** change shape — same list of listing dicts, same fields — which
is the promise MCP makes. The only visible difference is in the trace: the
step name says `search_listings (via MCP)` instead of `search_listings`,
and a bad call now raises `MCPError` instead of whatever `tools.py` would
raise directly, so I added a `try/except MCPError` around the call that
turns a dead server into a readable message instead of a crash.


---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** One line added to the rule list inside
`create_fit_card`'s prompt (`tools.py`):

```
"- Write the price in digits with a dollar sign, like $38. Never "
"spell it out in words (not 'thirty-eight dollars' or 'thirty-eight "
"bucks').\n"
```

**Which failure it was meant to fix:** Criterion 4 (fit card price in
digits), diagnosed above as a prompt gap — nothing told the model what
format to use for the price, so it sometimes picked words. This is the
"rewrite one prompt" improvement from the milestone's list, and it's the
single change made this unit; the MCP move is the only other thing that
changed in the code.

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before 2nd tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Selected item is the item passed to suggest_outfit | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card shows the price in digits | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Price ceiling respected, however worded | 5 of 5 | PASS | PASS | PASS | PASS | FAIL | MISSED (4/5) |

Row 3/4 and row 5 use the same five items / five wordings as the before
run, run again after the prompt change.

Real output, criterion 4, the two items that failed before —
`tools.py::create_fit_card`:

```
item 1 (vintage Levi's, $38): "scored these vintage 501s on depop for $38
and honestly they fit like a absolute dream. obsessed with the medi..."

item 5 (tie-dye long sleeve, $17): "Obsessed with this pastel tie-dye long
sleeve I just scored on Depop for $17. It gives the sweetest 90s indie..."
```

**Did it help, and how do I know:** Yes. Criterion 4 went from MISSED
(3/5) to MET (5/5) — all five fit cards wrote the price in digits,
including both items that failed before. I re-ran all five criteria, not
just criterion 4, and criteria 1, 2 and 3 stayed at MET (5/5) — the change
didn't break anything else. Criterion 5 is untouched, still MISSED (4/5)
on the same wording as before, which is expected: the prompt change only
touches `create_fit_card`'s output, not the regex parser that criterion 5
depends on. One change, one criterion moved, nothing else did.


---

## What's Still Broken

**Criterion 5 — price ceiling missed when it's spelled out in words.**
Still MISSED (4/5). The regex in `agent.py::_parse_query` only recognizes a
price written with digits. "under thirty five dollars" has no digits, so
no ceiling is ever set, and listings over budget slip into
`session["search_results"]`.

What I'd do: write a small word-to-number lookup (one, two, three, ... up
to maybe a hundred, plus compounds like "thirty five") and check for that
pattern after the digit-based regexes fail, instead of giving up with
`max_price = None`. I didn't do this now because the unit only allows one
change, and the fit-card prompt fix (criterion 4) was the more contained,
more clearly measurable one — a word-number parser touches more lines and
has more edge cases (hyphens, "a hundred" vs "100", "thirty-five" vs
"thirty five") to get right than I could verify carefully in this pass.

I stopped there on purpose, not because I ran out of time — the two misses
share a root cause (numbers as words instead of digits), and fixing both
at once would have made it harder to tell which change caused which
result. The MCP move and the criterion 4 prompt fix are the two changes
this unit allows for; criterion 5's fix is next unit's "one thing."


<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
