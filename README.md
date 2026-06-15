# FitFindr — Starter Kit

A multi-tool AI agent that helps users find secondhand pieces and figure out 
how to wear them. FitFindr orchestrates three tools in sequence — searching 
listings, suggesting outfits, and generating a shareable fit card — while 
handling failures gracefully at each step.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

4. Run the app:

```bash
python app.py
```

## Tool Inventory

### Tool 1: search_listings(description, size, max_price)
- **Inputs:** `description` (str) — keywords describing the item; `size` (str or None) — size to filter by; `max_price` (float or None) — upper price limit
- **Output:** List of listing dicts sorted by relevance score, each containing id, title, description, category, style_tags, size, condition, price, colors, brand, platform. Returns `[]` if nothing matches.
- **Purpose:** Searches and ranks listings from listings.json by keyword overlap with the description, after filtering by price and size.

### Tool 2: suggest_outfit(new_item, wardrobe)
- **Inputs:** `new_item` (dict) — a listing dict; `wardrobe` (dict) — has an `items` key with a list of wardrobe item dicts, may be empty
- **Output:** Non-empty string with 1-2 outfit suggestions from the LLM.
- **Purpose:** Sends the new item and wardrobe to the LLM and asks for specific outfit combinations, or general styling advice if wardrobe is empty.

### Tool 3: create_fit_card(outfit, new_item)
- **Inputs:** `outfit` (str) — outfit suggestion from suggest_outfit; `new_item` (dict) — the listing dict
- **Output:** 2-4 sentence casual Instagram-style caption string.
- **Purpose:** Generates a shareable, authentic-sounding caption for the outfit using the LLM at higher temperature for variety.

## How the Planning Loop Works

The agent runs a sequential loop with conditional branching:

1. Parse the user query with regex to extract description, size, and max_price
2. Call `search_listings` with the parsed parameters
3. **Branch:** if results is empty → set `session["error"]` and return immediately. `suggest_outfit` and `create_fit_card` are never called.
4. If results exist → set `session["selected_item"] = results[0]`
5. Call `suggest_outfit` with the selected item and wardrobe
6. Call `create_fit_card` with the outfit suggestion and selected item
7. Return the completed session

The agent does not call all three tools unconditionally — it stops at step 3 if search returns nothing, avoiding downstream calls with empty input.

## State Management

The agent maintains a `session` dict throughout one interaction:

```python
session = {
    "query": query,              # original user query
    "parsed": {},                # extracted description, size, max_price
    "search_results": [],        # all matching listings
    "selected_item": None,       # top result — passed into suggest_outfit
    "wardrobe": wardrobe,        # user's wardrobe
    "outfit_suggestion": None,   # returned by suggest_outfit — passed into create_fit_card
    "fit_card": None,            # returned by create_fit_card
    "error": None,               # set on early termination
}
```

Each tool reads its inputs from the session and writes its output back — no data is re-entered between steps.

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets `session["error"]` = "No listings found — try broader search terms or a higher price limit" and returns immediately |
| suggest_outfit | Wardrobe is empty | Still calls LLM but prompts for general styling advice instead of specific combinations |
| create_fit_card | outfit string is empty | Returns "Unable to generate fit card — outfit description is missing" without calling the LLM |

**Concrete example from testing:**
Running `search_listings("designer ballgown", size="XXS", max_price=5)` returns `[]`. The agent sets the error message and stops — `suggest_outfit` and `create_fit_card` are never called. The user sees: "No listings found — try broader search terms or a higher price limit."

## Spec Reflection

**One way the spec helped:** Filling in the planning loop section of planning.md before writing any code made the conditional branching logic clear before implementation. When it came to writing `run_agent()`, the exact branches were already decided — the code followed directly from the spec.

**One way implementation diverged:** The spec assumed query parsing would be simple. In practice, regex-based parsing works well for price and size but can miss edge cases in how users phrase descriptions. A more robust implementation would use the LLM to parse the query instead of regex.

## AI Usage

**Instance 1 — suggest_outfit implementation:**
I gave Claude the Tool 2 spec block from planning.md (inputs, return value, failure mode) and the wardrobe data structure printed from `get_example_wardrobe()`. I asked it to implement the function using Groq's llama-3.3-70b-versatile. I reviewed the generated code and added the `client = _get_groq_client()` call since the starter repo used a helper function instead of a global client variable.

**Instance 2 — planning loop implementation:**
I gave Claude the architecture diagram and planning loop section from planning.md and asked it to implement `run_agent()` in agent.py. I verified the generated code branched on the `search_listings` result before using it, and confirmed it did not call all three tools unconditionally.

## Stretch Features

### Retry Logic with Fallback
If `search_listings` returns no results and a size filter was applied, 
the agent automatically retries without the size filter and notifies 
the user with a ⚠️ warning in the listing panel. If results are still 
empty after retry, the agent sets `session["error"]` and stops.

### Price Comparison Tool: compare_prices(new_item)
- **Inputs:** `new_item` (dict) — a listing dict
- **Output:** String with price assessment (GREAT DEAL / FAIR PRICE / 
  SLIGHTLY HIGH), item price, average price of comparable listings, 
  price range, and reasoning.
- **How comparisons are made:** Finds listings with the same category 
  and at least one overlapping style_tag, calculates average and range 
  from those comparables, then assesses the item price against the average.

### Style Profile Memory
Saves the user's wardrobe and style preferences to `data/style_profile.json` 
between sessions. Users can save their current wardrobe and preferences with 
the Save Profile button, and reload them in a future session with Load Profile 
— without re-describing their wardrobe. Storage approach: local JSON file 
written and read with Python's `json` and `pathlib` modules.

## State Management

The agent maintains a `session` dict throughout one interaction:

```python
session = {
    "query": query,              # original user query
    "parsed": {},                # extracted description, size, max_price
    "search_results": [],        # all matching listings
    "selected_item": None,       # top result — passed into suggest_outfit
    "wardrobe": wardrobe,        # user's wardrobe
    "outfit_suggestion": None,   # returned by suggest_outfit — passed into create_fit_card
    "fit_card": None,            # returned by create_fit_card
    "price_comparison": None,    # returned by compare_prices
    "retry_note": None,          # set if size filter was removed on retry
    "error": None,               # set on early termination
}
```

Each tool reads its inputs from the session and writes its output back — 
no data is re-entered between steps.