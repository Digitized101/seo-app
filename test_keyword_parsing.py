import os
import glob
import re
from urllib.parse import urlparse

def load_keywords_from_file(base_url: str) -> dict:
    """Load keywords from existing kwd_<domain>_<ext>_<timestamp> file"""
    domain = urlparse(base_url).netloc.replace('www.', '')
    domain_parts = domain.split('.')
    domain_name = domain_parts[0]
    domain_ext = domain_parts[1] if len(domain_parts) > 1 else 'com'
    
    # Look for kwd_<domain>_<ext>_<timestamp> files in data/input_data folder
    input_data_dir = os.path.join('data', 'input_data')
    pattern = os.path.join(input_data_dir, f"kwd_{domain_name}_{domain_ext}_*.txt")
    files = glob.glob(pattern)
    
    if not files:
        return None
    
    # Get the most recent file
    latest_file = max(files, key=os.path.getctime)
    print(f"Found existing keyword file: {latest_file}")
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the content to extract keywords
        current_keywords = {'primary': [], 'secondary': []}
        
        lines = content.split('\n')
        in_current_primary = False
        in_current_secondary = False
        
        for line in lines:
            line = line.strip()
            
            if 'Current Primary Keywords:' in line:
                in_current_primary = True
                in_current_secondary = False
                print("DEBUG: Found Current Primary Keywords section")
            elif 'Current Secondary Keywords:' in line:
                in_current_primary = False
                in_current_secondary = True
                print("DEBUG: Found Current Secondary Keywords section")
            elif 'Recommended Primary Keyword:' in line:
                in_current_primary = False
                in_current_secondary = False
            elif line and any([in_current_primary, in_current_secondary]):
                # Skip header lines
                if 'Keyword' in line and 'Search Volume' in line:
                    continue
                if line.startswith('-') or line.startswith('='):
                    continue
                if line.startswith('#'):
                    continue
                
                print(f"DEBUG: Processing line: '{line}'")
                
                # Parse keyword lines using regex to handle multi-word phrases
                if in_current_primary or in_current_secondary:
                    if in_current_secondary and re.match(r'^\d+\s+', line):
                        # Format for secondary: 1    Mosquito Net                   27,000/mo          52/100       Not ranking
                        match = re.match(r'^\d+\s+(.+?)\s+(\d+[,\d]*/mo)\s+(\d+/100)\s+(.+)$', line)
                        print(f"DEBUG: Secondary keyword regex match: {match}")
                    else:
                        # Format for primary: Wire Mesh                           22,000/mo          58/100       Not ranking
                        match = re.match(r'^(.+?)\s+(\d+[,\d]*/mo)\s+(\d+/100)\s+(.+)$', line)
                        print(f"DEBUG: Primary keyword regex match: {match}")
                    
                    if match:
                        keyword = match.group(1).strip()
                        volume = match.group(2)
                        difficulty = match.group(3)
                        rank = match.group(4).strip()
                        
                        print(f"DEBUG: Extracted keyword: '{keyword}', volume: {volume}")
                        
                        kw_data = {
                            'keyword': keyword,
                            'search_volume': volume,
                            'difficulty': difficulty,
                            'serp_rank': rank
                        }
                        
                        if in_current_primary:
                            current_keywords['primary'].append(kw_data)
                            print(f"DEBUG: Added to primary: {keyword}")
                        else:
                            current_keywords['secondary'].append(kw_data)
                            print(f"DEBUG: Added to secondary: {keyword}")
        
        print(f"DEBUG: Final current_keywords: {current_keywords}")
        
        # Create keyword list for analysis (current primary first, then secondary)
        keyword_list = []
        # Add primary keywords first
        if current_keywords.get('primary'):
            keyword_list.extend([kw['keyword'] if isinstance(kw, dict) else kw for kw in current_keywords['primary']])
        # Then add secondary keywords
        if current_keywords.get('secondary'):
            keyword_list.extend([kw['keyword'] if isinstance(kw, dict) else kw for kw in current_keywords['secondary'][:5]])
        
        primary_keyword = keyword_list[0] if keyword_list else "SEO"
        secondary_keywords = keyword_list[1:] if len(keyword_list) > 1 else []
        
        print(f"DEBUG - Full keyword_list: {keyword_list}")
        print(f"DEBUG - Primary keyword: {primary_keyword}")
        print(f"DEBUG - Secondary keywords: {secondary_keywords}")
        
        return {
            'current_keywords': current_keywords,
            'keyword_list': keyword_list,
            'primary_keyword': primary_keyword,
            'secondary_keywords': secondary_keywords
        }
        
    except Exception as e:
        print(f"Error reading keyword file: {e}")
        return None

if __name__ == "__main__":
    base_url = "https://bbjaliwala.com"
    result = load_keywords_from_file(base_url)
    if result:
        print("\nFINAL RESULTS:")
        print(f"Primary keyword: {result['primary_keyword']}")
        print(f"Secondary keywords: {result['secondary_keywords']}")
    else:
        print("No keywords found")