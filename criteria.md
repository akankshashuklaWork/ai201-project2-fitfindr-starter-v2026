# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
I picked 4 of 5 and not 5 of 5 because my search is a loose keyword match, so
some phrasings will miss. For example, "sweater" and "trainers" find nothing in
the listings, so a query that sounds reasonable can still end with no fit card.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
I picked 5 of 5 because no model runs on this path. The agent runs
`search_listings` (plain Python), sees the empty list and stops, so
`suggest_outfit` and `create_fit_card` never run. With no model call there is no
randomness, rate limit or model failure that could make it miss, so one miss
would be a real bug.

---

## 3. The item search found is the item the next tool received

Given five different queries that each match at least one listing, the id of the
item passed into `suggest_outfit` equals `session["selected_item"]["id"]` in 5
of 5 runs. (The test records the item `suggest_outfit` was called with, and
compares its id to the one in the session.)

**Why this target:**
I picked 5 of 5 because handing the item from one tool to the next is plain code
with no randomness, so one mismatch would be a real bug, not noise. I use five
different queries and not one query repeated, because the same query five times
would only show that the code gives the same answer each time. It would not show
that it works for different items.


---

## 4. The fit card shows the price as digits

For five different items, each fit card shows the item's price as a dollar amount
in digits (for example "$19") in 5 of 5 cards. "Nineteen bucks" does not count.

**Why this target:**
I will accept "$19" but not "nineteen bucks", because a price in digits is
something a person can plainly check for. I picked 5 of 5 even though the model
varies and may miss, because I don't want a target so easy I can't miss it, and a
miss will be something to diagnose. I use five different items so the result
doesn't depend on one item.


---

## 5. The price ceiling is respected, whichever way it's worded

Given five typed requests that each state a price ceiling in a different wording
(for example "under $30", "$30 max" and "under thirty dollars"), every listing in
`session["search_results"]` costs at most that ceiling, in 5 of 5 requests.

**Why this target:**
I am testing the whole agent, not just `search_listings`, because the search tool
on its own never went over a ceiling in my checks. What can go wrong is the
parser failing to read the ceiling out of a sentence: it only reads digits, so
"under thirty dollars" becomes no ceiling at all. I picked 5 of 5 because a
shopper who states a budget expects it to hold, and I expect I may miss it on
some wordings and will diagnose why.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
