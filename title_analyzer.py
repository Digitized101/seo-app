import requests
from bs4 import BeautifulSoup
import os

# Load modifiers once at module level
script_dir = os.path.dirname(os.path.abspath(__file__))
modifiers_file = os.path.join(script_dir, 'modifiers.txt')

MODIFIERS = []
try:
    with open(modifiers_file, 'r') as f:
        MODIFIERS = [line.strip().lower() for line in f.readlines() if line.strip()]
except FileNotFoundError:
    pass

def analyze_title_seo(html: str, brand_name: str = "", keyword_list: list = [], is_homepage: bool = False) -> dict:
    """
    Analyze HTML title tag for SEO issues and provide suggestions
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {
        'title': '',
        'issues': [],
        'suggestions': [],
        'length': 0
    }
    
    # Check for multiple title tags
    all_title_tags = soup.find_all('title')
    if len(all_title_tags) > 1:
        result['issues'].append(f'Multiple title tags found ({len(all_title_tags)} tags)')
        result['suggestions'].append('Remove duplicate title tags - only one should exist')
    
    # Check if title tag is in head section
    head_section = soup.find('head')
    if head_section:
        title_in_head = head_section.find('title')
        title_in_body = soup.find('body')
        if title_in_body:
            title_in_body_check = title_in_body.find('title')
            if title_in_body_check:
                result['issues'].append('Title tag found in body section instead of head')
                result['suggestions'].append('Move title tag to the <head> section for proper SEO')
    
    # Get the first title tag for analysis
    title_tag = soup.find('title')
    
    # Check for missing title tag entirely
    if not title_tag:
        result['issues'].append('Missing title tag')
        result['suggestions'].append('Add a descriptive title tag to your HTML')
        result['title'] = 'No title found'
        return result
    
    # Check for missing content in title tag
    if not title_tag.string:
        result['issues'].append('Title tag has no content')
        result['suggestions'].append('Add descriptive text to your title tag')
        result['title'] = 'No title content found'
        return result
    
    # Extract title text
    title_text = ' '.join(title_tag.string.strip().split())  # Normalize whitespace
    result['title'] = title_text
    
    title_length = len(title_text)
    result['length'] = title_length
    
    # Check title length
    if title_length == 0:
        result['issues'].append('Title tag is empty')
        result['suggestions'].append('Add descriptive text to your title tag')
    elif title_length < 30:
        result['issues'].append(f'Title is too short ({title_length} characters)')
        result['suggestions'].append('Title should be between 50-60 characters for better SEO')
    elif title_length > 60:
        result['issues'].append(f'Title is too long ({title_length} characters)')
        result['suggestions'].append('Title should be between 50-60 characters to avoid truncation in search results')
    else:
        result['suggestions'].append('Title length is optimal (50-60 characters)')
    
    # Check for duplicate words (excluding stop words)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
    words = title_text.lower().split()
    meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
    
    if len(meaningful_words) != len(set(meaningful_words)):
        # Find which meaningful words are duplicated
        word_counts = {}
        for word in meaningful_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        duplicated = [word for word, count in word_counts.items() if count > 1]
        
        result['issues'].append(f'Title contains duplicate meaningful words: {", ".join(duplicated)}')
        result['suggestions'].append('Remove duplicate meaningful words to make title more concise')
    
    # Check for common SEO issues
    if title_text.isupper():
        result['issues'].append('Title is in all caps')
        result['suggestions'].append('Use proper capitalization instead of all caps')
    
    if title_text.count('|') > 2 or title_text.count('-') > 2:
        result['issues'].append('Too many separators in title')
        result['suggestions'].append('Limit separators (| or -) to 1-2 for better readability')
    
    # Check for keyword stuffing indicators
    if len(words) > 0:
        word_freq = {}
        for word in words:
            if len(word) > 3:  # Only check meaningful words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        repeated_words = [word for word, count in word_freq.items() if count > 2]
        if repeated_words:
            result['issues'].append(f'Possible keyword stuffing: "{", ".join(repeated_words)}" repeated multiple times')
            result['suggestions'].append('Avoid repeating keywords excessively in title')
    
    # Check for generic titles
    generic_words = ['welcome', 'home', 'page', 'website', 'site', 'untitled']
    if any(generic in title_text.lower() for generic in generic_words):
        result['issues'].append('Title contains generic words')
        result['suggestions'].append('Use specific, descriptive words instead of generic terms')
    
    # Check for special characters that may break display
    problematic_chars = ['"', "'", '`', '<', '>', '&', '\n', '\r', '\t']
    found_chars = [char for char in problematic_chars if char in title_text]
    if found_chars:
        result['issues'].append(f'Special characters that may break display: {", ".join(repr(char) for char in found_chars)}')
        result['suggestions'].append('Remove or properly encode special characters like quotes, brackets, and line breaks')
    
    # Check for non-printable characters
    non_printable = [char for char in title_text if not char.isprintable() and char not in [' ', '\n', '\r', '\t']]
    if non_printable:
        result['issues'].append(f'Non-printable characters detected: {", ".join(repr(char) for char in set(non_printable))}')
        result['suggestions'].append('Remove non-printable characters that may cause display issues')
    
    # Check for excessive punctuation
    punct_chars = '!?.,;:'
    punct_count = sum(title_text.count(p) for p in punct_chars)
    if punct_count > len(title_text.split()) * 0.3:  # More than 30% punctuation relative to words
        result['issues'].append(f'Excessive punctuation detected ({punct_count} punctuation marks)')
        result['suggestions'].append('Reduce punctuation usage for better readability and professional appearance')
    
    # Check for brand name and primary keyword placement
    if brand_name and brand_name.lower() not in title_text.lower():
        result['issues'].append('Brand name not found in title')
        result['suggestions'].append(f'Include brand name "{brand_name}" in title for brand recognition')
    

    
    # Check for primary keyword and placement based on page type
    if keyword_list and len(keyword_list) > 0:
        primary_keyword = ' '.join(keyword_list[0].strip().split())  # Primary keyword is first in list
        title_lower = title_text.lower()
        
        if primary_keyword.lower() not in title_lower:
            result['issues'].append(f'Primary keyword "{primary_keyword}" not found in title')
            result['suggestions'].append(f'Include primary keyword "{primary_keyword}" in title for better SEO')
        else:
            # Check placement based on page type
            if is_homepage:
                # Homepage: Brand Name | Primary Keyword
                if brand_name and '|' in title_text:
                    parts = [part.strip() for part in title_text.split('|')]
                    if len(parts) >= 2:
                        if brand_name.lower() not in parts[0].lower():
                            result['issues'].append('Brand name should come before separator (|) on homepage')
                            result['suggestions'].append(f'Use format: "{brand_name} | {primary_keyword}" for homepage title')
                        elif primary_keyword.lower() not in parts[1].lower():
                            result['issues'].append('Primary keyword should come after separator (|) on homepage')
                            result['suggestions'].append(f'Use format: "{brand_name} | {primary_keyword}" for homepage title')
                else:
                    result['suggestions'].append(f'Consider using format: "{brand_name} | {primary_keyword}" for homepage title')
            else:
                # Other pages: Primary Keyword first, then brand name
                title_words = title_lower.split()
                primary_words = primary_keyword.lower().split()
                
                # Find where primary keyword starts in title
                keyword_position = -1
                for i in range(len(title_words) - len(primary_words) + 1):
                    if title_words[i:i+len(primary_words)] == primary_words:
                        keyword_position = i
                        break
                
                if keyword_position > 0:
                    # Check if words before primary keyword are modifiers
                    words_before = title_words[:keyword_position]
                    non_modifier_words = [word for word in words_before if word not in MODIFIERS]
                    
                    if non_modifier_words:
                        result['issues'].append(f'Primary keyword "{primary_keyword}" should be front-loaded')
                        result['suggestions'].append('Move primary keyword to the front of title (after modifiers) for better SEO')
        
        # Check for any keywords
        keywords_to_check = keyword_list
        keywords_found = [kw for kw in keywords_to_check if kw.lower() in title_lower]
        if not keywords_found:
            result['issues'].append('No target keywords found in title')
            result['suggestions'].append('Include relevant keywords from your keyword list in the title')
        elif len(keywords_found) == 1:
            result['suggestions'].append('Consider adding secondary keywords to improve relevance')
    
    # Check for modifiers
    if MODIFIERS:
        title_words = title_text.lower().split()
        modifiers_found = [word for word in title_words if word in MODIFIERS]
        
        if not modifiers_found:
            result['suggestions'].append('Consider adding modifier words (best, top, professional, etc.) to make title more compelling')
    
    # Calculate title score
    score = 0
    
    # Title present (20 points)
    if title_text:
        score += 20
    
    # Correct length (15 points) - 50-60 characters
    if 50 <= title_length <= 60:
        score += 15
    
    # Uniqueness (25 points) - no duplicate meaningful words
    if len(meaningful_words) == len(set(meaningful_words)):
        score += 25
    
    # Keyword alignment (25 points) - primary keyword present
    if keyword_list and len(keyword_list) > 0 and keyword_list[0].lower() in title_lower:
        score += 25
    
    # No truncation risk (15 points) - length <= 60
    if title_length <= 60:
        score += 15
    
    # Determine status
    if score >= 80:
        status = 'GOOD'
        status_icon = '✅'
    elif score >= 60:
        status = 'FAIR'
        status_icon = '⚠️'
    else:
        status = 'POOR'
        status_icon = '🔴'
    
    result['score'] = score
    result['status'] = status
    result['status_icon'] = status_icon
    
    # Add overall message if no issues found
    if not result['issues']:
        result['suggestions'].append('Title looks well-optimized')
    
    return result

if __name__ == "__main__":
    url = input("Enter URL to analyze title: ")
    brand_name = input("Enter brand name (optional): ")
    
    # Read keywords from test file
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    keywords_file = os.path.join(script_dir, 'test_keywords.txt')
    
    try:
        with open(keywords_file, 'r') as f:
            keyword_list = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        keyword_list = []
        print("Warning: test_keywords.txt not found, proceeding without keywords")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("TITLE ANALYSIS")
            print("=" * 20)
            
            analysis = analyze_title_seo(response.text, brand_name, keyword_list)
            
            print(f"\nTitle: {analysis['title']}")
            print(f"Length: {len(analysis['title'])} characters")
            
            if keyword_list:
                print(f"Primary keyword: {keyword_list[0]}")
            if brand_name:
                print(f"Brand name: {brand_name}")
            
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