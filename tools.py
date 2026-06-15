"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """

    listings = load_listings()
    

    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]
    

    if size is not None:
        listings = [l for l in listings if size.lower() in l["size"].lower()]
    

    keywords = description.lower().split()
    
    def score(listing):
        text = (
            listing["title"].lower() + " " +
            listing["description"].lower() + " " +
            " ".join(listing["style_tags"]).lower()
        )
        return sum(1 for word in keywords if word in text)
    

    scored = [(listing, score(listing)) for listing in listings]
    scored = [(l, s) for l, s in scored if s > 0]
    

    scored.sort(key=lambda x: x[1], reverse=True)
    
    return [l for l, s in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """

    wardrobe_items = wardrobe.get("items", [])
    

    item_details = f"""
    Title: {new_item['title']}
    Category: {new_item['category']}
    Style tags: {', '.join(new_item['style_tags'])}
    Colors: {', '.join(new_item['colors'])}
    Condition: {new_item['condition']}
    Price: ${new_item['price']}
    """


    if not wardrobe_items:
        prompt = f"""You are a thrift fashion stylist. A user just found this secondhand item:
{item_details}
They don't have a wardrobe on file. Give them general styling advice — 
what kinds of pieces pair well with this item, what vibe it suits, 
and 1-2 outfit ideas using common wardrobe staples."""


    else:
        wardrobe_text = "\n".join([
            f"- {item['name']} ({item['category']}, {', '.join(item['colors'])})"
            for item in wardrobe_items
        ])
        prompt = f"""You are a thrift fashion stylist. A user just found this secondhand item:
{item_details}
Their current wardrobe includes:
{wardrobe_text}
Suggest 1-2 specific outfit combinations using the new item and 
named pieces from their wardrobe. Be specific about which pieces 
to pair together and why it works."""

    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )

    return response.choices[0].message.content

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """

    if not outfit or not outfit.strip():
        return "Unable to generate fit card — outfit description is missing."


    prompt = f"""You are writing a casual Instagram/TikTok caption for a thrift outfit post.

Item details:
- Name: {new_item['title']}
- Price: ${new_item['price']}
- Platform: {new_item['platform']}
- Colors: {', '.join(new_item['colors'])}
- Style: {', '.join(new_item['style_tags'])}

Outfit description:
{outfit}

Write a 2-4 sentence caption that:
- Sounds like a real person posting their OOTD, not a product description
- Mentions the item name, price, and platform naturally (once each)
- Captures the specific vibe of the outfit
- Feels authentic and casual, like something you'd actually post

Do not use hashtags. Do not start with "I"."""


    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=1.2
    )

    return response.choices[0].message.content

# ── Tool 4: compare_prices ────────────────────────────────────────────────────

def compare_prices(new_item: dict) -> str:
    """
    Compare the price of a listing against similar items in the dataset.

    Args:
        new_item: A listing dict for the item being considered.

    Returns:
        A string with a price assessment and reasoning.
    """
    listings = load_listings()


    new_tags = set(new_item.get("style_tags", []))
    new_category = new_item.get("category", "")

    comparable = []
    for listing in listings:
        if listing["id"] == new_item["id"]:
            continue
        if listing["category"] != new_category:
            continue
        tag_overlap = len(set(listing.get("style_tags", [])) & new_tags)
        if tag_overlap > 0:
            comparable.append(listing)

    if not comparable:
        return (
            f"No comparable listings found for {new_item['title']} "
            f"in the {new_category} category."
        )


    prices = [l["price"] for l in comparable]
    avg_price = sum(prices) / len(prices)
    min_price = min(prices)
    max_price = max(prices)
    item_price = new_item["price"]

    if item_price < avg_price * 0.8:
        assessment = "great deal"
        reasoning = f"It's priced ${avg_price - item_price:.2f} below the average."
    elif item_price <= avg_price * 1.1:
        assessment = "fair price"
        reasoning = f"It's close to the average price for similar items."
    else:
        assessment = "slightly high"
        reasoning = f"It's ${item_price - avg_price:.2f} above the average."

    return (
        f"Price assessment for {new_item['title']}: {assessment.upper()}\n"
        f"Item price: ${item_price:.2f}\n"
        f"Comparable listings ({len(comparable)} found): "
        f"avg ${avg_price:.2f}, range ${min_price:.2f}–${max_price:.2f}\n"
        f"Reasoning: {reasoning}"
    )

# ── Tool 5: style profile memory ─────────────────────────────────────────────

import json
from pathlib import Path

PROFILE_PATH = Path("data/style_profile.json")

def save_style_profile(wardrobe: dict, preferences: str = "") -> str:
    """
    Save user's wardrobe and style preferences to a local JSON file.

    Args:
        wardrobe: The user's wardrobe dict
        preferences: Optional string describing style preferences

    Returns:
        Confirmation message string
    """
    profile = {
        "wardrobe": wardrobe,
        "preferences": preferences
    }
    PROFILE_PATH.write_text(json.dumps(profile, indent=2))
    return "Style profile saved successfully."


def load_style_profile() -> dict | None:
    """
    Load the user's saved style profile from disk.

    Returns:
        Profile dict with 'wardrobe' and 'preferences' keys,
        or None if no profile exists.
    """
    if not PROFILE_PATH.exists():
        return None
    return json.loads(PROFILE_PATH.read_text())