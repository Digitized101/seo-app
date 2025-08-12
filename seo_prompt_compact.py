import os, json, re
from typing import Dict, List
from openai import OpenAI

# --- Config ---
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-nano")
API_KEY = os.getenv("OPENAI_API_KEY")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))

if not API_KEY:
    raise SystemExit("Missing OPENAI_API_KEY env var.")

client = OpenAI(api_key=API_KEY)

# --- Prompts (compressed, ASCII only) ---
SYSTEM_PROMPT = (
    "You are an SEO expert. Follow Google best practices for SEO. Return ONLY valid JSON per schema. "
    "All constraints are mandatory. If any field fails, self-correct before responding. No explanations."
)

USER_PROMPT_TEMPLATE = """Page: {page}
Primary KW: {primary_kw}
Secondary KWs: {secondary_kws}
Location: {location}
Tone: {tone}

Constraints:
- title: 50-60 chars, include brand + primary KW + 1 modifier [Top, Best, Leading, Professional, Trusted, Expert], no '&'
- h1: <=60 chars, include primary KW once
- h2: 2-3 unique entries, each <=70 chars
- meta_description: <=155 chars, benefit-led, include primary KW + location
- image_alt_text: 3 descriptive entries, <=120 chars, no '|' or emojis
- body_content: 200-400 words, include primary KW once + 1-2 secondary KWs naturally, scannable format, end with CTA

Schema:
{{
  "title": "string",
  "h1": "string",
  "h2": ["string", "string", "string"],
  "meta_description": "string",
  "image_alt_text": ["string", "string", "string"],
  "body_content": "string"
}}
"""

# --- Request payload builder ---
def build_user_prompt(
    page: str,
    primary_kw: str,
    secondary_kws: str,
    location: str,
    tone: str = "professional, trustworthy, action-oriented",
) -> str:
    return USER_PROMPT_TEMPLATE.format(
        page=page,
        primary_kw=primary_kw,
        secondary_kws=secondary_kws,
        location=location,
        tone=tone,
    )

# --- Load keywords from file ---
def load_keywords_from_file(filename):
    filepath = os.path.join('input_data', filename)
    brand_name = ""
    primary_keyword = ""
    secondary_keywords = []
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if '(BRAND NAME)' in line:
            brand_name = line.replace('(BRAND NAME)', '').strip()
        elif '(PRIMARY KEYWORD)' in line:
            primary_keyword = line.replace('(PRIMARY KEYWORD)', '').strip()
        elif line and not line.startswith('Keywords extracted') and not line.startswith('Extraction') and not line.startswith('Total') and not line.startswith('--'):
            if '(BRAND NAME)' not in line and '(PRIMARY KEYWORD)' not in line:
                secondary_keywords.append(line)
    
    return brand_name, primary_keyword, secondary_keywords

# Load keywords (using the .com file as example)
BRAND, PRIMARY, secondary_keywords_list = load_keywords_from_file('keywords_fortuneagronet_com_20250811_190001.txt')
MODIFIERS = {"Top","Best","Leading","Professional","Trusted","Expert"}

def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))

def validate(doc: Dict) -> List[str]:
    errors = []
    try:
        title = doc["title"].strip()
        h1 = doc["h1"].strip()
        h2 = [h.strip() for h in doc["h2"]]
        meta = doc["meta_description"].strip()
        alts = [a.strip() for a in doc["image_alt_text"]]
        body = doc["body_content"].strip()
    except Exception as e:
        return [f"schema_error: {e}"]

    # Title
    if not (50 <= len(title) <= 60): errors.append(f"title_length={len(title)}")
    if "&" in title: errors.append("title_contains_ampersand")
    if BRAND not in title: errors.append("title_missing_brand")
    if PRIMARY.lower() not in title.lower(): errors.append("title_missing_primary_kw")
    if not any(m in title for m in MODIFIERS): errors.append("title_missing_modifier")

    # H1
    if len(h1) > 60: errors.append(f"h1_length={len(h1)}")
    if len(re.findall(re.escape(PRIMARY), h1, flags=re.I)) != 1:
        errors.append("h1_primary_kw_not_once")

    # H2
    if not (2 <= len(h2) <= 3): errors.append("h2_count_invalid")
    if len(set(h2)) != len(h2): errors.append("h2_duplicates")
    for i, hh in enumerate(h2):
        if len(hh) > 70: errors.append(f"h2_{i}_too_long")

    # Meta
    if len(meta) > 155: errors.append(f"meta_length={len(meta)}")
    if "Gujarat" not in meta: errors.append("meta_missing_location")
    if PRIMARY.lower() not in meta.lower(): errors.append("meta_missing_primary_kw")

    # Image alts
    if len(alts) != 3: errors.append("image_alt_text_count")
    for i, a in enumerate(alts):
        if len(a) > 120: errors.append(f"alt_{i}_too_long")
        if "|" in a or "�" in a: errors.append(f"alt_{i}_invalid_chars")

    # Body
    wc = word_count(body)
    if not (130 <= wc <= 170): errors.append(f"body_word_count={wc}")
    if re.search(rf"{re.escape(PRIMARY)}", body, flags=re.I) is None:
        errors.append("body_missing_primary_kw")
    if body.strip()[-1] not in ".!?":
        errors.append("body_missing_terminal_punct")

    return errors

# --- OpenAI calls ---
def call_model(system_prompt: str, user_prompt: str) -> Dict:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)

def repair(doc: Dict, errors: List[str]) -> Dict:
    system = "You are an SEO expert. Return ONLY valid JSON. Fix ONLY the flagged fields; keep all other values unchanged."
    user = (
        "Violations: " + ", ".join(errors) +
        ". Correct the invalid fields. Keep valid fields identical. "
        "Return JSON in the exact same schema as before. No explanations.\nPrevious JSON:\n" +
        json.dumps(doc, ensure_ascii=False)
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)

def generate_with_validation(page:str, primary_kw:str, secondary_kws:str, location:str, tone:str, max_retries:int=MAX_RETRIES) -> Dict:
    user_prompt = build_user_prompt(page, primary_kw, secondary_kws, location, tone)
    doc = call_model(SYSTEM_PROMPT, user_prompt)
    errors = validate(doc)
    tries = 0
    while errors and tries < max_retries:
        doc = repair(doc, errors)
        errors = validate(doc)
        tries += 1
    return {"doc": doc, "errors": errors}

if __name__ == "__main__":
    # Use loaded keywords
    secondary_kws_text = ', '.join(secondary_keywords_list)
    
    print(f"Brand Name: {BRAND}")
    print(f"Primary Keyword: {PRIMARY}")
    print(f"Secondary Keywords: {secondary_kws_text}")
    print("\n" + "="*50 + "\n")
    
    result = generate_with_validation(
        page=f"{BRAND} homepage",
        primary_kw=PRIMARY,
        secondary_kws=secondary_kws_text,
        location="Gujarat, India",
        tone="professional, trustworthy, action-oriented",
    )

    if result["errors"]:
        print("Non-compliant after retries:", result["errors"])
    print(json.dumps(result["doc"], ensure_ascii=False, indent=2))
