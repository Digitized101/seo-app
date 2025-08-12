import requests
from bs4 import BeautifulSoup
import re

def analyze_body_content_seo(html: str, keyword_list: list = [], brand_name: str = "") -> dict:
    """
    Analyze HTML body content for SEO issues with 100-point scoring
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {
        'issues': [],
        'suggestions': [],
        'word_count': 0,
        'character_count': 0,
        'score': 0,
        'status': '',
        'status_icon': ''
    }
    
    score = 0
    
    # Get body content
    body = soup.find('body')
    if not body:
        result['issues'].append('No body tag found')
        result['suggestions'].append('Add a proper body tag to your HTML')
        return result
    
    # Extract text content from body
    body_text = body.get_text(separator=' ', strip=True)
    result['character_count'] = len(body_text)
    
    # Count words
    words = body_text.split()
    result['word_count'] = len(words)
    
    # Word count check (30 points)
    if result['word_count'] >= 300:
        if result['word_count'] <= 2000:
            score += 30
            result['suggestions'].append('Content length is optimal for SEO')
        else:
            score += 25
            result['suggestions'].append('Consider breaking long content into sections with subheadings')
    elif result['word_count'] >= 150:
        score += 15
        result['issues'].append(f'Content could be longer ({result["word_count"]} words)')
        result['suggestions'].append('Add more content - aim for at least 300 words for better SEO')
    else:
        result['issues'].append(f'Content too short ({result["word_count"]} words)')
        result['suggestions'].append('Add more content - aim for at least 300 words for better SEO')
    
    # Check for empty body
    if result['word_count'] == 0:
        result['issues'].append('Body content is empty')
        result['suggestions'].append('Add meaningful content to your page')
        return result
    
    # Brand name overuse check
    if brand_name and result['word_count'] > 0:
        body_lower = body_text.lower()
        brand_count = body_lower.count(brand_name.lower())
        brand_density = (brand_count / result['word_count']) * 100
        
        if brand_density > 2:
            result['issues'].append(f'Brand name "{brand_name}" overused ({brand_density:.1f}% density)')
            result['suggestions'].append(f'Reduce brand name usage - use pronouns or "we/our" instead')
        elif brand_density > 1.5:
            result['suggestions'].append(f'Brand name usage is high ({brand_density:.1f}%) - consider variation')
    
    # Keyword coverage check (40 points) - skip brand name (first keyword)
    keyword_score = 0
    if keyword_list and len(keyword_list) > 1:
        body_lower = body_text.lower()
        
        for i, keyword in enumerate(keyword_list[1:], 1):  # Skip brand name
            keyword_lower = keyword.lower()
            keyword_count = body_lower.count(keyword_lower)
            keyword_density = (keyword_count / result['word_count']) * 100 if result['word_count'] > 0 else 0
            
            if i == 1:  # Primary keyword (25 points)
                if 1 <= keyword_density <= 2.5:
                    keyword_score += 25
                    result['suggestions'].append(f'Primary keyword "{keyword}" density is optimal ({keyword_density:.1f}%)')
                elif 0.5 <= keyword_density < 1:
                    keyword_score += 15
                    result['issues'].append(f'Primary keyword density could be higher ({keyword_density:.1f}%)')
                    result['suggestions'].append(f'Increase primary keyword "{keyword}" usage to 1-2% density')
                elif keyword_density > 3:
                    keyword_score += 10
                    result['issues'].append(f'Primary keyword density too high ({keyword_density:.1f}%)')
                    result['suggestions'].append(f'Reduce primary keyword "{keyword}" usage to avoid keyword stuffing')
                elif keyword_count == 0:
                    result['issues'].append(f'Primary keyword "{keyword}" not found in body content')
                    result['suggestions'].append(f'Include primary keyword "{keyword}" naturally in your content')
                else:
                    keyword_score += 5
                    result['issues'].append(f'Primary keyword density too low ({keyword_density:.1f}%)')
                    result['suggestions'].append(f'Increase primary keyword "{keyword}" usage to 1-2% density')
            elif i < 3:  # Secondary keywords (up to 15 points total)
                if keyword_count > 0:
                    keyword_score += min(7, keyword_count * 2)
                    result['suggestions'].append(f'Secondary keyword "{keyword}" found in content')
                else:
                    result['suggestions'].append(f'Consider including secondary keyword "{keyword}" in content')
    
    score += keyword_score
    
    # Check for heading structure
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    if not headings:
        result['issues'].append('No headings found in content')
        result['suggestions'].append('Add headings (H1, H2, H3) to structure your content')
    else:
        h1_tags = soup.find_all('h1')
        if len(h1_tags) == 0:
            result['issues'].append('No H1 tag found')
            result['suggestions'].append('Add an H1 tag as the main heading')
        elif len(h1_tags) > 1:
            result['issues'].append(f'Multiple H1 tags found ({len(h1_tags)})')
            result['suggestions'].append('Use only one H1 tag per page')
    

    
    # Check for internal and external links
    links = soup.find_all('a', href=True)
    internal_links = [link for link in links if not link['href'].startswith(('http://', 'https://', 'mailto:', 'tel:'))]
    external_links = [link for link in links if link['href'].startswith(('http://', 'https://'))]
    
    if not internal_links:
        result['suggestions'].append('Add internal links to other pages on your site')
    
    if not external_links:
        result['suggestions'].append('Consider adding relevant external links to authoritative sources')
    
    # Readability baseline check (10 points)
    readability_score = 10
    sentences = re.split(r'[.!?]+', body_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if sentences:
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_sentence_length > 25:
            readability_score = 5
            result['issues'].append(f'Average sentence length too long ({avg_sentence_length:.1f} words)')
            result['suggestions'].append('Break up long sentences for better readability')
        elif avg_sentence_length < 8:
            readability_score = 7
            result['suggestions'].append('Consider combining very short sentences for better flow')
    
    score += readability_score
    
    # Duplication hints check (20 points)
    duplication_score = 20
    paragraphs = soup.find_all('p')
    if len(paragraphs) > 1:
        paragraph_texts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
        if len(paragraph_texts) != len(set(paragraph_texts)):
            duplication_score = 0
            result['issues'].append('Duplicate paragraphs detected')
            result['suggestions'].append('Remove or rewrite duplicate content')
    
    # Check for repetitive phrases
    if result['word_count'] > 100:
        words_lower = [word.lower() for word in words if len(word) > 3]
        word_freq = {}
        for word in words_lower:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        repeated_words = [word for word, count in word_freq.items() if count > result['word_count'] * 0.02]  # More than 2% frequency
        if repeated_words and not keyword_list:  # Only flag if no keywords provided
            duplication_score -= 10
            result['issues'].append(f'Repetitive words detected: {", ".join(repeated_words[:3])}')
            result['suggestions'].append('Vary your vocabulary to avoid repetitive content')
    
    score += max(0, duplication_score)
    
    # Check for proper text formatting
    bold_tags = soup.find_all(['b', 'strong'])
    italic_tags = soup.find_all(['i', 'em'])
    
    if not bold_tags and not italic_tags:
        result['suggestions'].append('Use bold/strong and italic/emphasis tags to highlight important content')
    
    # Check for lists
    lists = soup.find_all(['ul', 'ol'])
    if not lists and result['word_count'] > 500:
        result['suggestions'].append('Consider using bullet points or numbered lists to improve readability')
    

    # Determine status based on score
    if score >= 80:
        result['status'] = 'GOOD'
        result['status_icon'] = '🟢'
    elif score >= 60:
        result['status'] = 'FAIR'
        result['status_icon'] = '🟡'
    else:
        result['status'] = 'POOR'
        result['status_icon'] = '🔴'
    
    result['score'] = score
    
    # Add overall message if no issues found and score is good
    if not result['issues'] and score >= 80:
        result['suggestions'].append('Body content looks well-optimized')
    
    return result

if __name__ == "__main__":
    url = input("Enter URL to analyze body content: ")
    
    # Read keywords from test file and convert to list
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    keywords_file = os.path.join(script_dir, 'test_keywords.txt')
    
    keyword_list = []
    try:
        with open(keywords_file, 'r') as f:
            keyword_list = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        print("Warning: test_keywords.txt not found, proceeding without keywords")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("BODY CONTENT ANALYSIS")
            print("=" * 25)
            
            analysis = analyze_body_content_seo(response.text, keyword_list)
            
            print(f"\nWord count: {analysis['word_count']} words")
            print(f"Character count: {analysis['character_count']} characters")
            
            if keyword_list:
                print(f"Primary keyword: {keyword_list[0]}")
            
            if analysis['issues']:
                print("\nIssues:")
                for issue in analysis['issues']:
                    print(f"• {issue}")
            
            if analysis['suggestions']:
                print("\nSuggestions:")
                for suggestion in analysis['suggestions']:
                    print(f"• {suggestion}")
        else:
            print(f"Error: Could not fetch URL (Status: {response.status_code})")
    
    except Exception as e:
        print(f"Error: {e}")