import os
from openai import OpenAI

MODEL_NAME = "gpt-4.1-nano"
# Load your OpenAI API key from environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load keywords from file
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
brand_name, primary_keyword, secondary_keywords = load_keywords_from_file('keywords_fortuneagronet_com_20250811_190001.txt')

# Use all secondary keywords
secondary_keywords_text = ', '.join(secondary_keywords)

messages = [
    {
        "role": "system",
        "content": "You are an SEO expert. Follow Google best practices. Prioritize readability, CTR, and non-duplicative phrasing. Respect length limits. Use primary keyword in Title, H1, and Meta Description. Use modifiers to make Title more compelling. Avoid keyword stuffing. Return ONLY valid JSON matching the schema. No extra text."
    },
    {
        "role": "user",
        "content": f'''Page: {brand_name} homepage
Primary keyword: {primary_keyword}
Secondary keywords: {secondary_keywords_text}
Location: Gujarat, India
Tone: professional, trustworthy, action-oriented

Deliver:
- title: 50–60 chars, compelling, includes brand + primary keyword
- h1: concise, natural, includes primary keyword once
- h2: array of 2–3 supporting headings
- meta_description: <=155 chars, benefit-led, includes primary + location
- image_alt_text: array of 3 descriptive alts (products/uses), <=120 chars each, incorporate relevant secondary keywords naturally
- body_content: ~200 words, scannable, includes primary keyword + naturally integrate multiple secondary keywords from the list, clear CTA

Output JSON schema:
{{
  "title": "string",
  "h1": "string",
  "h2": ["string", "string", "string"],
  "meta_description": "string",
  "image_alt_text": ["string", "string", "string"],
  "body_content": "string"
}}'''
    }
]

print(f"Brand Name: {brand_name}")
print(f"Primary Keyword: {primary_keyword}")
print(f"Secondary Keywords: {secondary_keywords_text}")
print("\n" + "="*50 + "\n")

response = client.chat.completions.create(
    model=MODEL_NAME,
    messages=messages
)

print(response.choices[0].message.content)
