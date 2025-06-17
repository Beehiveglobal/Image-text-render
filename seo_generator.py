import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SEO_MATRIX = json.load(open("data/seo_matrix.json", encoding="utf-8"))
STYLE_GUIDE = json.load(open("data/style_guide.json", encoding="utf-8"))
ROTATION_PATH = "data/keyword_rotation_state.json"

def get_rotating_keywords(category, keyword_list, max_length, primary):
    if not os.path.exists(ROTATION_PATH):
        rotation_state = {}
    else:
        rotation_state = json.load(open(ROTATION_PATH, encoding="utf-8"))

    current = rotation_state.get(category, 0)
    ordered = keyword_list[current:] + keyword_list[:current]
    selected = []
    total_len = len(primary)

    for word in ordered:
        if total_len + len(word) + 2 <= max_length:
            selected.append(word)
            total_len += len(word) + 2
        else:
            break

    next_index = (current + len(selected)) % len(keyword_list) if keyword_list else 0
    rotation_state[category] = next_index
    with open(ROTATION_PATH, "w", encoding="utf-8") as f:
        json.dump(rotation_state, f, indent=2)

    return selected

def slugify(text):
    return text.lower().replace(" ", "-").replace("/", "-")

def generate_seo_full(product_name, category, description_text, dimension_overrides=None):
    if category not in SEO_MATRIX:
        raise ValueError(f"❌ Invalid category: {category}")

    keywords = SEO_MATRIX[category]
    primary = keywords.get("primary_keywords", ["furniture"])[0]
    secondary = get_rotating_keywords(category, keywords.get("secondary_keywords", []), 160, primary)
    all_keywords = [primary] + secondary

    prompt = f"""
Write a 100-word SEO introduction in a {STYLE_GUIDE['tone']} tone.
Use this product description as source:
\"\"\"{description_text}\"\"\"
Category: {category}
Primary Keyword (2–3x): {primary}
Secondary Keywords (1x each): {', '.join(secondary)}
Avoid: {', '.join(STYLE_GUIDE.get('avoid_phrases', []))}
Preferred Phrases: {', '.join(STYLE_GUIDE.get('preferred_phrases', []))}
Structure: {STYLE_GUIDE['structure']}
Mention use in hotels, restaurants, bars, or commercial settings.
Use third person.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    intro = response.choices[0].message.content.strip()

    default_dimensions = {
        "Height": "90 cm",
        "Depth": "55 cm",
        "Width": "44 cm",
        "Seat Height": "47 cm",
        "Weight": "6.5 kg"
    }

    dimensions = dimension_overrides if dimension_overrides else default_dimensions

    features_html = """
<h2>Product Features</h2>
<ul>
  <li><a href="/banquet-chairs#stackable">Stackable Banquet Chairs</a> – space-saving, ideal for storage and quick setup</li>
  <li><a href="/banquet-chairs#upholstered">Upholstered Banquet Chairs</a> – comfort-focused designs in fabric or vinyl</li>
  <li><a href="/banquet-chairs#black">Black Banquet Chairs</a> – a versatile and timeless colour for all venues</li>
  <li><a href="/banquet-chairs#commercial">Commercial Banquet Chairs</a> – made for hotels, function centres, and conference rooms</li>
  <li><a href="/banquet-chairs#sydney">Banquet Chairs Sydney</a> – serving the Greater Sydney hospitality and event market</li>
</ul>
""".strip()

    return {
        "intro": intro,
        "features_html": features_html,
        "dimensions": dimensions,
        "meta_title": f"{product_name} – {primary}"[:60],
        "meta_description": f"{product_name} is ideal for use in {', '.join(secondary)}."[:160],
        "meta_keywords": all_keywords,
        "url_key": slugify(f"{product_name} {primary}")
    }
