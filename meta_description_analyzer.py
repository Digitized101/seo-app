import requests
from bs4 import BeautifulSoup
import os

def analyze_meta_description_seo(html: str, keyword_list: list = []) -> dict:
    """
    Analyze HTML meta description for SEO issues with 100-point scoring
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {
        'meta_description': '',
        'issues': [],
        'suggestions': [],
        'length': 0,
        'score': 0,
        'status': '',
        'status_icon': ''
    }
    
    score = 0
    
    # Separate lists for required vs optional suggestions
    required_suggestions = []
    optional_suggestions = []
    
    # Check for incorrect property attribute usage
    property_meta_desc = soup.find_all('meta', attrs={'property': 'description'})
    if property_meta_desc:
        result['issues'].append('Meta description using property="description" instead of name="description"')
        required_suggestions.append('Change property="description" to name="description" for proper SEO')
    
    # Check for multiple meta description tags
    all_meta_desc = soup.find_all('meta', attrs={'name': 'description'})
    if len(all_meta_desc) > 1:
        result['issues'].append(f'Multiple meta description tags found ({len(all_meta_desc)} tags)')
        required_suggestions.append('Remove duplicate meta description tags - only one should exist')
    
    # Check if meta description is in head section
    head_section = soup.find('head')
    if head_section:
        meta_in_head = head_section.find('meta', attrs={'name': 'description'})
        meta_in_body = soup.find('body')
        if meta_in_body:
            meta_in_body_check = meta_in_body.find('meta', attrs={'name': 'description'})
            if meta_in_body_check:
                result['issues'].append('Meta description found in body section instead of head')
                required_suggestions.append('Move meta description tag to the <head> section for proper SEO')
    
    # Get the first meta description for analysis
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    
    # Presence check (25 points)
    if not meta_desc or 'content' not in meta_desc.attrs or not meta_desc.get('content').strip():
        result['issues'].append('Missing meta description')
        required_suggestions.append('Add a meta description tag to improve search result snippets')
        result['meta_description'] = 'No meta description found'
        result['score'] = score
        result['status'] = 'POOR'
        result['status_icon'] = '🔴'
        result['suggestions'] = required_suggestions
        return result
    
    score += 25  # Meta description present
    
    # Extract meta description text
    desc_text = ' '.join(meta_desc.get('content').strip().split())  # Normalize whitespace
    result['meta_description'] = desc_text
    
    desc_length = len(desc_text)
    result['length'] = desc_length
    
    # Length check (20 points)
    if 150 <= desc_length <= 160:
        score += 20
        required_suggestions.append('Meta description length is optimal (150-160 characters)')
    elif 120 <= desc_length < 150:
        score += 15
        required_suggestions.append('Meta description could be slightly longer for better optimization')
    elif desc_length > 160:
        score += 10
        result['issues'].append(f'Meta description is too long ({desc_length} characters)')
        required_suggestions.append('Meta description should be between 150-160 characters to avoid truncation')
    elif desc_length == 0:
        result['issues'].append('Meta description is empty')
        required_suggestions.append('Add descriptive text to your meta description')
    else:
        result['issues'].append(f'Meta description is too short ({desc_length} characters)')
        required_suggestions.append('Meta description should be between 150-160 characters for optimal search visibility')
    
    # Uniqueness check (25 points)
    uniqueness_score = 25
    
    # Check for generic descriptions
    generic_phrases = ['welcome to our website', 'this is our website', 'home page', 'main page', 'default description']
    if any(generic in desc_text.lower() for generic in generic_phrases):
        uniqueness_score -= 15
        result['issues'].append('Meta description contains generic phrases')
        required_suggestions.append('Write a unique, specific meta description that describes the page content')
    
    # Check for duplicate words (excluding stop words)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
    words = desc_text.lower().split()
    meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
    
    if len(meaningful_words) != len(set(meaningful_words)):
        uniqueness_score -= 10
        word_counts = {}
        for word in meaningful_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        duplicated = [word for word, count in word_counts.items() if count > 1]
        result['issues'].append(f'Meta description contains duplicate meaningful words: {", ".join(duplicated)}')
        required_suggestions.append('Remove duplicate meaningful words to make description more concise')
    
    score += max(0, uniqueness_score)
    
    # Check for keyword stuffing
    if len(words) > 0:
        word_freq = {}
        for word in words:
            if len(word) > 3:  # Only check meaningful words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        repeated_words = [word for word, count in word_freq.items() if count > 2]
        if repeated_words:
            result['issues'].append(f'Possible keyword stuffing: "{", ".join(repeated_words)}" repeated multiple times')
            required_suggestions.append('Avoid repeating keywords excessively in meta description')
    
    # Check for generic descriptions
    generic_phrases = ['welcome to our website', 'this is our website', 'home page', 'main page', 'default description']
    if any(generic in desc_text.lower() for generic in generic_phrases):
        result['issues'].append('Meta description contains generic phrases')
        required_suggestions.append('Write a unique, specific meta description that describes the page content')
    
    # Check for call-to-action
    cta_words = ['learn more', 'discover', 'explore', 'find out', 'get started', 'contact us', 'call now', 'visit', 'shop now', 'buy now']
    if not any(cta in desc_text.lower() for cta in cta_words):
        optional_suggestions.append('Consider adding a call-to-action to encourage clicks (e.g., "Learn more", "Get started")')
    
    # Keyword alignment (30 points)
    keyword_score = 0
    if keyword_list and len(keyword_list) > 1:
        primary_keyword = ' '.join(keyword_list[0].strip().split())  # Primary keyword is first in list
        desc_lower = desc_text.lower()
        
        # Primary keyword check (20 points)
        if primary_keyword.lower() in desc_lower:
            keyword_score += 20
            required_suggestions.append(f'Primary keyword "{primary_keyword}" found in meta description')
        else:
            result['issues'].append(f'Primary keyword "{primary_keyword}" not found in meta description')
            required_suggestions.append(f'Include primary keyword "{primary_keyword}" in meta description for better relevance')
        
        # Secondary keywords check (10 points) - skip brand name and primary keyword
        secondary_found = 0
        for keyword in keyword_list[2:4]:  # Check keywords 3-4 (skip brand and primary)
            if keyword.lower() in desc_lower:
                secondary_found += 1
        
        if secondary_found > 0:
            keyword_score += min(10, secondary_found * 5)
            optional_suggestions.append(f'Secondary keywords found in meta description')
        
        # Check for keyword stuffing
        primary_count = desc_lower.count(primary_keyword.lower())
        if primary_count > 2:
            keyword_score -= 10
            result['issues'].append(f'Primary keyword "{primary_keyword}" appears {primary_count} times - possible over-optimization')
            required_suggestions.append('Use primary keyword naturally, ideally 1-2 times in meta description')
    
    score += max(0, keyword_score)
    
    # Check for special characters that may break display
    problematic_chars = ['"', "'", '`', '<', '>', '&', '\n', '\r', '\t']
    found_chars = [char for char in problematic_chars if char in desc_text]
    if found_chars:
        result['issues'].append(f'Special characters that may break display: {", ".join(repr(char) for char in found_chars)}')
        required_suggestions.append('Remove or properly encode special characters like quotes, brackets, and line breaks')
    
    # Check for non-printable characters
    non_printable = [char for char in desc_text if not char.isprintable() and char not in [' ', '\n', '\r', '\t']]
    if non_printable:
        result['issues'].append(f'Non-printable characters detected: {", ".join(repr(char) for char in set(non_printable))}')
        required_suggestions.append('Remove non-printable characters that may cause display issues')
    
    # Check for excessive punctuation
    punct_chars = '!?.,;:'
    punct_count = sum(desc_text.count(p) for p in punct_chars)
    if punct_count > len(desc_text.split()) * 0.3:  # More than 30% punctuation relative to words
        result['issues'].append(f'Excessive punctuation detected ({punct_count} punctuation marks)')
        required_suggestions.append('Reduce punctuation usage for better readability and professional appearance')
    
    # Check for all caps text (excluding common acronyms)
    common_acronyms = {'HDPE', 'PVC', 'API', 'ISO', 'USA', 'UK', 'EU', 'CEO', 'CTO', 'SEO', 'HTML', 'CSS', 'JS', 'AI', 'ML', 'IT', 'HR', 'PR', 'ROI', 'KPI', 'FAQ', 'PDF', 'URL', 'HTTP', 'HTTPS', 'FTP', 'DNS', 'IP', 'TCP', 'UDP', 'SQL', 'API', 'SDK', 'IDE', 'OS', 'UI', 'UX', 'B2B', 'B2C', 'SaaS', 'CRM', 'ERP', 'CMS', 'LMS', 'AWS', 'GCP', 'IBM', 'AMD', 'GPU', 'CPU', 'RAM', 'SSD', 'HDD', 'USB', 'WiFi', 'GPS', 'SMS', 'MMS', 'VPN', 'SSL', 'TLS'}
    words_caps = [word for word in desc_text.split() if word.isupper() and len(word) > 1 and word not in common_acronyms]
    if words_caps:
        result['issues'].append(f'All caps text detected: {", ".join(words_caps)}')
        required_suggestions.append('Avoid using all caps text as it appears unprofessional and may hurt readability')
    
    # Check for compelling language
    compelling_words = ['unique', 'exclusive', 'proven', 'expert', 'professional', 'quality', 'trusted', 'leading', 'award-winning']
    if not any(word in desc_text.lower() for word in compelling_words):
        optional_suggestions.append('Consider adding compelling adjectives to make description more attractive')
    
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
    
    # Combine suggestions with required first, then optional
    result['suggestions'] = required_suggestions + optional_suggestions
    result['score'] = score
    
    # Add overall message if no issues found and score is good
    if not result['issues'] and score >= 80:
        result['suggestions'] = ['Meta description looks well-optimized']
    
    return result

if __name__ == "__main__":
    url = input("Enter URL to analyze meta description: ")
    
    # Read keywords from test file
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
            print("META DESCRIPTION ANALYSIS")
            print("=" * 30)
            
            analysis = analyze_meta_description_seo(response.text, keyword_list)
            
            print(f"\nLength: {analysis['length']} characters")
            
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