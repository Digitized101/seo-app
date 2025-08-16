import requests
from bs4 import BeautifulSoup
import os

def analyze_headings_seo(html: str, keyword_list: list = [], brand_name: str = "") -> dict:
    """
    Analyze HTML headings for SEO issues with 100-point scoring
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {
        'headings_count': {},
        'issues': [],
        'suggestions': [],
        'score': 0,
        'status': '',
        'status_icon': ''
    }
    
    score = 0
    
    # Separate lists for required vs optional suggestions
    required_suggestions = []
    optional_suggestions = []
    
    # Count each heading type
    for i in range(1, 7):  # h1 to h6
        headings = soup.find_all(f'h{i}')
        result['headings_count'][f'h{i}'] = len(headings)
    
    # Get all headings for analysis
    all_headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    # Check for missing headings
    if not all_headings:
        result['issues'].append('No headings found on page')
        required_suggestions.append('Add heading tags (h1-h6) to structure your content for better SEO')
        return result
    
    # H1 presence check (30 points)
    h1_tags = soup.find_all('h1')
    if len(h1_tags) == 1:
        score += 30
        required_suggestions.append('H1 tag properly implemented')
    elif len(h1_tags) == 0:
        result['issues'].append('Missing H1 tag')
        required_suggestions.append('Add exactly one H1 tag as the main page heading')
    else:
        score += 10  # Partial credit for having H1s, even if multiple
        result['issues'].append(f'Multiple H1 tags found ({len(h1_tags)} tags)')
        required_suggestions.append('Use only one H1 tag per page - convert others to H2 or lower')
    
    # Hierarchy check (30 points)
    hierarchy_score = 30
    heading_levels = []
    for heading in all_headings:
        level = int(heading.name[1])
        heading_levels.append(level)
    
    # Check heading order validation (H1 should come before H2s)
    if heading_levels and h1_tags:
        h1_position = None
        first_h2_position = None
        
        for i, level in enumerate(heading_levels):
            if level == 1 and h1_position is None:
                h1_position = i
            elif level == 2 and first_h2_position is None:
                first_h2_position = i
                break
        
        if h1_position is not None and first_h2_position is not None and h1_position > first_h2_position:
            hierarchy_score -= 15
            result['issues'].append('H1 tag appears after H2 tags in document order')
            required_suggestions.append('Place H1 tag before any H2 tags for proper document structure')
    
    # Check for skipped heading levels
    if heading_levels:
        for i in range(len(heading_levels) - 1):
            current_level = heading_levels[i]
            next_level = heading_levels[i + 1]
            if next_level > current_level + 1:
                hierarchy_score -= 15
                result['issues'].append(f'Heading hierarchy skipped from H{current_level} to H{next_level}')
                required_suggestions.append('Maintain proper heading hierarchy - don\'t skip heading levels (e.g., H1 → H2 → H3)')
                break
    
    score += max(0, hierarchy_score)
    
    # Check nested heading structure analysis
    if len(heading_levels) > 1:
        # Check for proper nesting - each level should have content under it
        level_counts = {}
        for level in heading_levels:
            level_counts[level] = level_counts.get(level, 0) + 1
        
        # Check if there are deeper levels without intermediate levels
        max_level = max(heading_levels)
        min_level = min(heading_levels)
        
        for level in range(min_level + 1, max_level + 1):
            if level not in level_counts and (level - 1) in level_counts:
                result['issues'].append(f'Heading structure has H{level-1} but jumps to H{level+1} without H{level}')
                required_suggestions.append('Ensure each heading level is used before jumping to deeper levels')
                break
        
        # Check for unbalanced nesting (too many deep levels without structure)
        if max_level > 4 and level_counts.get(2, 0) < 2:
            result['issues'].append('Deep heading levels (H5-H6) used without sufficient H2 structure')
            required_suggestions.append('Build proper content hierarchy with more H2 sections before using deeper heading levels')
    
    # Check for empty headings
    empty_headings = []
    for heading in all_headings:
        if not heading.get_text(strip=True):
            empty_headings.append(heading.name.upper())
    
    if empty_headings:
        result['issues'].append(f'Empty heading tags found: {", ".join(set(empty_headings))}')
        required_suggestions.append('Add descriptive text to all heading tags')
    
    # Brand name in H1 check
    if brand_name and h1_tags and len(h1_tags) == 1:
        h1_text = h1_tags[0].get_text(strip=True).lower()
        if brand_name.lower() in h1_text:
            result['issues'].append(f'Brand name "{brand_name}" found in H1 tag')
            required_suggestions.append('H1 should focus on primary keyword, not brand name')
    
    # Keyword use check (20 points) - use primary keyword (first in list)
    keyword_score = 0
    if keyword_list and len(keyword_list) > 0 and h1_tags and len(h1_tags) == 1:
        primary_keyword = ' '.join(keyword_list[0].strip().split())
        h1_text = h1_tags[0].get_text(strip=True).lower()
        
        if primary_keyword.lower() in h1_text:
            keyword_score += 15
            required_suggestions.append(f'Primary keyword "{primary_keyword}" found in H1 tag')
        else:
            result['issues'].append(f'Primary keyword "{primary_keyword}" not found in H1 tag')
            required_suggestions.append(f'Include primary keyword "{primary_keyword}" in H1 tag for better SEO')
        
        # Check for secondary keywords in other headings
        if len(keyword_list) > 2:
            secondary_keyword = ' '.join(keyword_list[2].strip().split())
            h2_to_h6_headings = soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6'])
            
            if h2_to_h6_headings:
                for heading in h2_to_h6_headings:
                    heading_text = heading.get_text(strip=True).lower()
                    if secondary_keyword.lower() in heading_text:
                        keyword_score += 5
                        break
    
    score += keyword_score
    
    # Check heading length (H1 should be concise) - only if H1 exists and has content
    if h1_tags and len(h1_tags) == 1:  # Only check if exactly one H1 exists
        h1_text = h1_tags[0].get_text(strip=True)
        h1_length = len(h1_text)
        if h1_length > 0:  # Only check length if H1 has content
            if h1_length > 70:
                result['issues'].append(f'H1 tag is too long ({h1_length} characters)')
                required_suggestions.append('Keep H1 tag under 70 characters for better readability')
            elif h1_length < 10:
                result['issues'].append(f'H1 tag is too short ({h1_length} characters)')
                required_suggestions.append('Make H1 tag more descriptive (10-70 characters recommended)')
    
    # Check for keyword stuffing in headings
    if keyword_list and len(keyword_list) > 0:
        primary_keyword = ' '.join(keyword_list[0].strip().split())
        keyword_count_in_headings = 0
        
        for heading in all_headings:
            heading_text = heading.get_text(strip=True).lower()
            keyword_count_in_headings += heading_text.count(primary_keyword.lower())
        
        if keyword_count_in_headings > 3:
            result['issues'].append(f'Primary keyword appears {keyword_count_in_headings} times in headings - possible over-optimization')
            required_suggestions.append('Use primary keyword naturally in headings - avoid excessive repetition')
    
    # Check for secondary keywords in H2-H6 headings
    if keyword_list and len(keyword_list) > 2:
        secondary_keyword = ' '.join(keyword_list[2].strip().split())
        h2_to_h6_headings = soup.find_all(['h2', 'h3', 'h4', 'h5', 'h6'])
        
        if h2_to_h6_headings:
            secondary_found = False
            for heading in h2_to_h6_headings:
                heading_text = heading.get_text(strip=True).lower()
                if secondary_keyword.lower() in heading_text:
                    secondary_found = True
                    break
            
            if not secondary_found:
                optional_suggestions.append(f'Consider including secondary keyword "{secondary_keyword}" in H2-H6 headings for better SEO coverage')
    
    # Check for special characters in headings
    problematic_chars = ['"', "'", '`', '<', '>', '&', '\n', '\r', '\t', '|', '#', '@', '$', '%', '^', '*']
    headings_with_special_chars = []
    for heading in all_headings:
        heading_text = heading.get_text(strip=True)
        if any(char in heading_text for char in problematic_chars):
            headings_with_special_chars.append(heading.name.upper())
    
    if headings_with_special_chars:
        result['issues'].append(f'Special characters found in headings: {", ".join(set(headings_with_special_chars))}')
        required_suggestions.append('Remove special characters from headings for better readability and SEO')
    
    # Check for all caps headings (excluding common acronyms)
    common_acronyms = {'HDPE', 'PVC', 'API', 'ISO', 'USA', 'UK', 'EU', 'CEO', 'CTO', 'SEO', 'HTML', 'CSS', 'JS', 'AI', 'ML', 'IT', 'HR', 'PR', 'ROI', 'KPI', 'FAQ', 'PDF', 'URL', 'HTTP', 'HTTPS', 'FTP', 'DNS', 'IP', 'TCP', 'UDP', 'SQL', 'SDK', 'IDE', 'OS', 'UI', 'UX', 'B2B', 'B2C', 'SaaS', 'CRM', 'ERP', 'CMS', 'LMS', 'AWS', 'GCP', 'IBM', 'AMD', 'GPU', 'CPU', 'RAM', 'SSD', 'HDD', 'USB', 'WiFi', 'GPS', 'SMS', 'MMS', 'VPN', 'SSL', 'TLS'}
    caps_headings = []
    for heading in all_headings:
        heading_text = heading.get_text(strip=True)
        if heading_text and heading_text.isupper() and len(heading_text) > 3:
            # Check if entire heading is a single acronym or contains non-acronym words
            words = heading_text.split()
            non_acronym_words = [word for word in words if word not in common_acronyms]
            if non_acronym_words:  # Only flag if there are non-acronym all-caps words
                caps_headings.append(heading.name.upper())
    
    if caps_headings:
        result['issues'].append(f'All caps headings found: {", ".join(set(caps_headings))}')
        required_suggestions.append('Use proper capitalization instead of all caps for better readability')
    
    # No duplicates check (20 points)
    duplicate_score = 20
    heading_texts = []
    for heading in all_headings:
        text = heading.get_text(strip=True).lower()
        if text:
            heading_texts.append(text)
    
    if len(heading_texts) != len(set(heading_texts)):
        duplicate_score = 0
        duplicates = [text for text in set(heading_texts) if heading_texts.count(text) > 1]
        result['issues'].append(f'Duplicate heading text found: {", ".join(duplicates[:3])}')
        required_suggestions.append('Make each heading unique to improve content structure and SEO')
    
    score += duplicate_score
    
    # Check for generic heading text
    generic_headings = ['welcome', 'about us', 'about', 'home', 'contact us', 'contact', 'services', 'products', 'introduction', 'overview', 'more info', 'click here', 'read more', 'learn more', 'get started']
    found_generic = []
    for heading in all_headings:
        heading_text = heading.get_text(strip=True).lower()
        if heading_text in generic_headings:
            found_generic.append(heading_text)
    
    if found_generic:
        result['issues'].append(f'Generic heading text found: {", ".join(set(found_generic))}')
        required_suggestions.append('Use specific, descriptive headings instead of generic terms for better SEO')
    
    # Check heading structure recommendations
    h2_count = result['headings_count']['h2']
    if h1_tags and h2_count == 0:
        optional_suggestions.append('Consider adding H2 tags to break up content into sections')
    
    # Check for too many headings
    total_headings = sum(result['headings_count'].values())
    if total_headings > 20:
        result['issues'].append(f'Too many headings ({total_headings} total)')
        required_suggestions.append('Reduce number of headings - focus on main content sections')
    
    # Check unbalanced heading distribution
    if total_headings > 3:
        h2_count = result['headings_count']['h2']
        h3_count = result['headings_count']['h3']
        
        # Check if there are too many H3s compared to H2s
        if h2_count > 0 and h3_count > h2_count * 4:
            result['issues'].append(f'Unbalanced heading distribution: {h3_count} H3 tags vs {h2_count} H2 tags')
            required_suggestions.append('Balance heading distribution - consider converting some H3 tags to H2 or restructuring content')
        
        # Check if most headings are at one level (excluding H1 since there should only be one)
        non_h1_counts = {k: v for k, v in result['headings_count'].items() if k != 'h1' and v > 0}
        if non_h1_counts:
            max_non_h1_count = max(non_h1_counts.values())
            non_h1_total = sum(non_h1_counts.values())
            
            if non_h1_total > 2 and max_non_h1_count > non_h1_total * 0.8:  # More than 80% at one level (excluding H1)
                dominant_level = [level for level, count in non_h1_counts.items() if count == max_non_h1_count][0]
                result['issues'].append(f'Heading distribution heavily skewed toward {dominant_level.upper()} tags ({max_non_h1_count} out of {non_h1_total} non-H1 headings)')
                required_suggestions.append('Diversify heading levels to create better content hierarchy')
    
    # Check content length vs heading ratio
    body_tag = soup.find('body')
    if body_tag:
        # Get all text content excluding headings
        body_text = body_tag.get_text(strip=True)
        heading_text = ' '.join([h.get_text(strip=True) for h in all_headings])
        content_text = body_text.replace(heading_text, '', 1)  # Remove heading text
        content_length = len(content_text.split())
        
        if content_length > 0 and total_headings > 0:
            words_per_heading = content_length / total_headings
            
            if words_per_heading < 50:
                result['issues'].append(f'Too many headings for content length ({words_per_heading:.0f} words per heading)')
                required_suggestions.append('Reduce number of headings or add more content between headings')
            elif words_per_heading > 300:
                result['issues'].append(f'Too few headings for content length ({words_per_heading:.0f} words per heading)')
                required_suggestions.append('Add more headings to break up long content sections')
    
    # Check heading density analysis
    if total_headings > 0 and body_tag:
        body_text = body_tag.get_text(strip=True)
        total_words = len(body_text.split())
        
        if total_words > 0:
            heading_density = (total_headings / total_words) * 100
            
            if heading_density > 5:  # More than 5% of content is headings
                result['issues'].append(f'Heading density too high ({heading_density:.1f}% of content)')
                required_suggestions.append('Reduce heading frequency - headings should be 2-4% of total content')
            elif heading_density < 1 and total_words > 500:  # Less than 1% for long content
                result['issues'].append(f'Heading density too low ({heading_density:.1f}% of content)')
                required_suggestions.append('Add more headings to improve content structure and readability')
    
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
        result['suggestions'] = ['Headings look well-optimized']
    
    return result

if __name__ == "__main__":
    url = input("Enter URL to analyze headings: ")
    
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
            print("HEADINGS ANALYSIS")
            print("=" * 20)
            
            analysis = analyze_headings_seo(response.text, keyword_list)
            
            # Display heading counts
            print("\nHeading Counts:")
            for heading_type, count in analysis['headings_count'].items():
                print(f"{heading_type.upper()}: {count}")
            
            if keyword_list:
                print(f"\nPrimary keyword: {keyword_list[0]}")
            
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