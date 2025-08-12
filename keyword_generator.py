#!/usr/bin/env python3

import os
from openai import OpenAI
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv
import json

# Try multiple .env locations
import os
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).parent

# Try loading .env from multiple locations
env_paths = [
    script_dir / '.env',  # Same directory as script
    Path.cwd() / '.env',  # Current working directory
    script_dir.parent / '.env',  # Parent directory
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

class KeywordGenerator:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            print("Warning: OPENAI_API_KEY not found in .env file - will use fallback method")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=self.api_key.strip('"'))
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {e} - will use fallback method")
                self.client = None
    
    def generate_keywords(self, html_content, url):
        """Generate keywords using OpenAI API"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # If no OpenAI client, use fallback immediately
        if not self.client:
            return self._fallback_keywords(soup, url)
        
        # Extract key content
        title = soup.find('title')
        title_text = title.text.strip() if title else ''
        
        h1_tags = soup.find_all('h1')
        h1_text = ' '.join([h.text.strip() for h in h1_tags])
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_desc_text = meta_desc.get('content', '') if meta_desc else ''
        
        body_sample = soup.get_text()[:800]  # First 800 chars
        
        domain = urlparse(url).netloc.replace('www.', '')
        
        prompt = f"""Analyze this website content and identify the BRAND NAME and PRIMARY KEYWORD, then generate 18 additional SEO keywords.

Website: {domain}
Title: {title_text}
H1 Tags: {h1_text}
Meta Description: {meta_desc_text}
Content Sample: {body_sample}

Your task:
1. FIRST: Identify the BRAND NAME (company/business name) from the content
2. SECOND: Identify the PRIMARY KEYWORD (main business/service term)
3. Generate 18 additional relevant SEO keywords

Structure the response as exactly 20 keywords in this order:
1. BRAND NAME (company/business name)
2. PRIMARY KEYWORD (main service/business focus)
3-20. Additional SEO keywords (secondary terms, industry keywords, long-tail keywords, location terms, product variations)

IMPORTANT RULES:
- Position 1 MUST be the brand/company name
- Position 2 MUST be the primary business/service keyword
- Return ONLY a valid JSON array with exactly 20 keywords
- No explanations, markdown, or additional text

Example format: ["BrandName", "primary_service", "secondary_keyword1", "secondary_keyword2", ...]

Return the JSON array now:"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an SEO expert specializing in keyword research and analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            keywords_json = response.choices[0].message.content.strip()
            
            # Clean up the response - remove markdown formatting if present
            if keywords_json.startswith('```json'):
                keywords_json = keywords_json.replace('```json', '').replace('```', '').strip()
            elif keywords_json.startswith('```'):
                keywords_json = keywords_json.replace('```', '').strip()
            
            # Try to parse JSON
            try:
                keywords = json.loads(keywords_json)
                if isinstance(keywords, list) and len(keywords) > 0:
                    # Clean keywords - remove empty strings and duplicates
                    clean_keywords = []
                    seen = set()
                    for kw in keywords:
                        if isinstance(kw, str) and kw.strip() and kw.strip().lower() not in seen:
                            clean_keywords.append(kw.strip())
                            seen.add(kw.strip().lower())
                    return clean_keywords[:20]
                else:
                    print(f"AI returned invalid format: {type(keywords)}")
                    return self._fallback_keywords(soup, url)
            except json.JSONDecodeError as json_err:
                print(f"JSON parsing error: {json_err}")
                print(f"Raw response: {keywords_json[:200]}...")
                return self._fallback_keywords(soup, url)
            
        except Exception as e:
            print(f"AI keyword generation error: {e}")
            return self._fallback_keywords(soup, url)
    
    def _identify_brand_name(self, soup, url):
        """Identify brand name from website content"""
        import re
        
        # Try domain name first
        domain = urlparse(url).netloc.replace('www.', '').split('.')[0]
        
        # Look for brand in title
        title = soup.find('title')
        if title:
            title_text = title.text.strip()
            # Look for capitalized words that might be brand names
            brand_candidates = re.findall(r'\b[A-Z][a-zA-Z]+\b', title_text)
            if brand_candidates:
                return brand_candidates[0]
        
        # Look in H1 tags
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            brand_candidates = re.findall(r'\b[A-Z][a-zA-Z]+\b', h1.text)
            if brand_candidates:
                return brand_candidates[0]
        
        # Fallback to domain name
        return domain.capitalize()
    
    def _fallback_keywords(self, soup, url):
        """Fallback keyword extraction if AI fails"""
        print("Using fallback keyword extraction...")
        import re
        from collections import Counter
        
        # Extract text from important elements with weights
        keywords = []
        
        # Title keywords (high weight)
        title = soup.find('title')
        title_words = []
        if title:
            title_words = re.findall(r'\b[a-zA-Z]{3,}\b', title.text.lower())
            keywords.extend(title_words * 3)  # Weight x3
        
        # H1 keywords (high weight)
        h1_tags = soup.find_all('h1')
        h1_words = []
        for h1 in h1_tags:
            h1_text_words = re.findall(r'\b[a-zA-Z]{3,}\b', h1.text.lower())
            h1_words.extend(h1_text_words)
            keywords.extend(h1_text_words * 2)  # Weight x2
        
        # Meta description keywords
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            meta_words = re.findall(r'\b[a-zA-Z]{3,}\b', meta_desc.get('content', '').lower())
            keywords.extend(meta_words * 2)  # Weight x2
        
        # Body text keywords
        body_text = soup.get_text().lower()
        body_words = re.findall(r'\b[a-zA-Z]{3,}\b', body_text)
        keywords.extend(body_words)
        
        # Remove stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'with', 'have', 'this', 'will', 'your', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'were'
        }
        
        filtered_keywords = [w for w in keywords if w not in stop_words and len(w) > 2]
        word_freq = Counter(filtered_keywords)
        
        # Identify brand name
        brand_name = self._identify_brand_name(soup, url)
        
        # Identify primary keyword from title and H1 tags first
        primary_keyword = None
        for word in title_words + h1_words:
            if word not in stop_words and len(word) > 2 and word.lower() != brand_name.lower():
                primary_keyword = word
                break
        
        # Get remaining keywords
        final_keywords = [word for word, count in word_freq.most_common(20) if count > 1]
        
        # Remove brand name and primary keyword from list if they exist
        final_keywords = [kw for kw in final_keywords if kw.lower() not in [brand_name.lower(), primary_keyword.lower() if primary_keyword else '']]
        
        # If we don't have enough keywords, add some generic business terms
        if len(final_keywords) < 18:
            generic_terms = ['business', 'service', 'company', 'professional', 'quality', 'solutions', 'products', 'expert', 'best', 'top']
            for term in generic_terms:
                if term not in final_keywords:
                    final_keywords.append(term)
                if len(final_keywords) >= 18:
                    break
        
        # Put brand name first, primary keyword second, then others
        result = [brand_name]
        if primary_keyword:
            result.append(primary_keyword)
        else:
            # If no primary keyword found, use most frequent non-brand word
            for word, count in word_freq.most_common():
                if word.lower() != brand_name.lower():
                    result.append(word)
                    break
        result.extend(final_keywords[:18])
        
        return result[:20]
    
    def save_keywords_to_file(self, keywords, url):
        """Save AI-generated keywords to file"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '').replace('.', '_')
        filename = f"ai_keywords_{domain}.txt"
        
        os.makedirs('seo/output', exist_ok=True)
        filepath = f"seo/output/{filename}"
        
        with open(filepath, 'w') as f:
            for i, keyword in enumerate(keywords, 1):
                if i == 1:
                    f.write(f"{keyword} (BRAND NAME)\n")
                elif i == 2:
                    f.write(f"{keyword} (PRIMARY KEYWORD)\n")
                else:
                    f.write(f"{keyword}\n")
        
        return filepath

def generate_keywords_from_html(html_content, url):
    """Main function to generate AI keywords from HTML"""
    try:
        generator = KeywordGenerator()
        keywords = generator.generate_keywords(html_content, url)
        filepath = generator.save_keywords_to_file(keywords, url)
        
        return {
            'keywords': keywords,
            'total_count': len(keywords),
            'file_path': filepath,
            'method': 'AI' if len(keywords) > 0 else 'fallback'
        }
    except Exception as e:
        print(f"Keyword generation failed completely: {e}")
        # Emergency fallback with basic keywords
        basic_keywords = ['business', 'service', 'company', 'professional', 'quality', 'best', 'top', 'expert', 'solutions', 'products']
        return {
            'keywords': basic_keywords,
            'total_count': len(basic_keywords),
            'file_path': None,
            'method': 'emergency_fallback'
        }