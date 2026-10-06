# Data notes (Milestone 1)

What I found when I read `data/listings.json` and `data/wardrobe_schema.json`
before writing any tools. `search_listings` can only filter on fields that
exist, so I wrote them down first.

## A listing (40 of them in `data/listings.json`)

| Field | Type | Example | Notes |
|---|---|---|---|
| `id` | str | `lst_006` | unique |
| `title` | str | `Graphic Tee — 2003 Tour Bootleg Style` | best place for keywords |
| `description` | str | `Vintage-style bootleg tee with faded graphic...` | a sentence or two |
| `category` | str | `tops` | one of tops, bottoms, outerwear, shoes, accessories |
| `style_tags` | list[str] | `["graphic tee", "vintage", "grunge"]` | tags can be two words |
| `size` | str | `L` | **messy**, see below |
| `condition` | str | `good` | excellent, good or fair |
| `price` | float | `24.0` | ranges from 12.0 to 75.0 |
| `colors` | list[str] | `["black"]` | |
| `brand` | str or None | `None` | **None for 32 of the 40 listings** |
| `platform` | str | `depop` | depop, poshmark or thredUp |

## Things that will bite if I'm not careful

- **Sizes are not one clean format.** I saw `M`, `S/M`, `M/L`, `L/XL`,
  `XL (oversized)`, `One Size`, `W30 L30`, `US 8.5`... A plain substring test
  would match `"s"` inside `"us 9"`, so search has to split a size into whole
  pieces and compare those instead.
- **`brand` is usually `None`.** Any code that does `brand.lower()` crashes on
  most listings, so every use of `brand` needs a None check.
- **Prices are floats**, so "under $30" should be a `<=` comparison on a
  number, not a string match.

## A wardrobe item (what `suggest_outfit` receives)

A wardrobe is a dict with one key, `items`, holding a list of items:

| Field | Type | Example |
|---|---|---|
| `id` | str | `w_001` |
| `name` | str | `Baggy straight-leg jeans, dark wash` |
| `category` | str | `bottoms` |
| `colors` | list[str] | `["dark blue", "indigo"]` |
| `style_tags` | list[str] | `["denim", "streetwear", "baggy"]` |
| `notes` | str or None | `"High-waisted, sits above the hip"` (often `None`) |

## What an empty wardrobe looks like

```python
{"items": []}
```

It is **not** `None` and it is **not** missing the `items` key. It has the same
shape as a full wardrobe, with nothing in the list. So `suggest_outfit` has to
check `len(wardrobe["items"]) == 0`, not `wardrobe is None`.
