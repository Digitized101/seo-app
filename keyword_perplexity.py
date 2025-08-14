#!/usr/bin/env python3

import requests
import os
import json
import re
from urllib.parse import urlparse
from datetime import datetime
from bs4 import BeautifulSoup
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Manual .env loading
    try:
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    except FileNotFoundError:
        pass

class PerplexityKeywordAnalyzer:
    def __init__(self, api_key=None):
        """
        Initialize Perplexity AI keyword analyzer
        
        Args:
            api_key (str): Perplexity API key. If None, will try to get from environment variable PPLX_API_KEY
        """
        self.api_key = api_key or os.getenv('PPLX_API_KEY')
        if not self.api_key:
            raise ValueError("Perplexity API key is required. Set PPLX_API_KEY in .env file or pass api_key parameter.")
        
        # Validate API key format
        if not self.api_key.startswith('pplx-'):
            print(f"Warning: API key doesn't start with 'pplx-'. Current key: {self.api_key[:10]}...")
        
        print(f"Using API key: {self.api_key[:10]}...{self.api_key[-4:]}")
        
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def extract_current_keywords(self, website_content):
        """
        Extract keywords the site is currently optimizing for from existing SEO elements
        """
        if not website_content:
            return {'primary': [], 'secondary': []}
        
        try:
            # Re-fetch to get full HTML structure for keyword extraction
            response = requests.get(website_content['url'], timeout=15)
            if response.status_code != 200:
                return {'primary': [], 'secondary': []}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            current_keywords = {
                'primary': [],
                'secondary': []
            }
            
            # Extract from meta keywords tag
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords:
                keywords_content = meta_keywords.get('content', '')
                if keywords_content:
                    keywords_list = [kw.strip() for kw in keywords_content.split(',') if kw.strip()]
                    if keywords_list:
                        current_keywords['primary'].append(keywords_list[0])
                        current_keywords['secondary'].extend(keywords_list[1:])
            
            # Extract from title tag (usually contains primary keywords)
            title = soup.find('title')
            if title:
                title_text = title.get_text().lower()
                business_keywords = []
                common_terms = ['manufacturer', 'supplier', 'company', 'services', 'products', 'solutions']
                words = title_text.split()
                for i, word in enumerate(words):
                    if word in common_terms and i > 0:
                        potential_keyword = f"{words[i-1]} {word}"
                        business_keywords.append(potential_keyword)
                
                if business_keywords and not current_keywords['primary']:
                    current_keywords['primary'].extend(business_keywords[:1])
                    current_keywords['secondary'].extend(business_keywords[1:])
            
            # Extract from H1 tags (primary focus keywords)
            h1_tags = soup.find_all('h1')
            for h1 in h1_tags:
                h1_text = h1.get_text().strip().lower()
                if h1_text and len(h1_text.split()) <= 4:
                    if h1_text not in [kw.lower() for kw in current_keywords['primary']]:
                        current_keywords['secondary'].append(h1_text.title())
            
            # Extract from meta description (secondary keywords)
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                desc_content = meta_desc.get('content', '').lower()
                words = desc_content.split()
                word_freq = {}
                for word in words:
                    if len(word) > 3 and word.isalpha():
                        word_freq[word] = word_freq.get(word, 0) + 1
                
                frequent_terms = [word.title() for word, freq in word_freq.items() if freq > 1][:3]
                current_keywords['secondary'].extend(frequent_terms)
            
            # Clean up and deduplicate
            current_keywords['primary'] = list(dict.fromkeys(current_keywords['primary']))[:2]
            current_keywords['secondary'] = list(dict.fromkeys(current_keywords['secondary']))[:8]
            
            # Remove any secondary keywords that are in primary
            primary_lower = [kw.lower() for kw in current_keywords['primary']]
            current_keywords['secondary'] = [kw for kw in current_keywords['secondary'] 
                                           if kw.lower() not in primary_lower]
            
            return current_keywords
            
        except Exception as e:
            print(f"Error extracting current keywords: {e}")
            return {'primary': [], 'secondary': []}
    
    def fetch_website_content(self, url):
        """
        Fetch and extract text content from a website
        
        Args:
            url (str): Website URL to analyze
            
        Returns:
            dict: Contains title, meta description, and body text
        """
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            meta_description = meta_desc.get('content', '').strip() if meta_desc else ""
            
            # Extract body text (first 2000 characters to avoid token limits)
            body_text = soup.get_text()
            # Clean up whitespace
            body_text = ' '.join(body_text.split())[:2000]
            
            return {
                'title': title_text,
                'meta_description': meta_description,
                'body_text': body_text,
                'url': url
            }
            
        except Exception as e:
            print(f"Error fetching website content: {e}")
            return None
    
    def analyze_keywords_with_perplexity(self, website_content):
        """
        Use Perplexity AI to analyze website content and extract keywords with metrics
        
        Args:
            website_content (dict): Website content from fetch_website_content
            
        Returns:
            dict: Analysis results with brand name, keywords, search volume, and difficulty
        """
        if not website_content:
            return None
        
        # Create prompt for Perplexity AI
        prompt = f"""
        Analyze the following website content and provide SEO keyword analysis SPECIFICALLY for the Indian market:

        URL: {website_content['url']}
        Title: {website_content['title']}
        Meta Description: {website_content['meta_description']}
        Content: {website_content['body_text']}

        IMPORTANT: Focus ONLY on the Indian market. Consider:
        - Indian search behavior and language preferences (Hindi/English mix)
        - Local competition within India
        - Indian business terminology and regional variations
        - Search volumes from Google India specifically
        - Keywords that Indian customers would actually use
        - Current SERP ranking of this website for each keyword

        Please provide the following information in JSON format:
        1. Brand name (the main company/organization name)
        2. Primary keyword (most important keyword for this website in India)
        3. Secondary keywords (5-10 additional relevant keywords for Indian market)
        4. For each keyword, provide estimated metrics for India ONLY:
           - Monthly search volume in India (from Google India data)
           - Keyword difficulty for ranking in India (scale 1-100)
           - Current SERP ranking of {website_content['url']} for this keyword (1-100, or 'Not ranking' if beyond top 100)

        Include location-specific terms if relevant (city names, regional terms).

        Format the response as valid JSON with this structure:
        {{
            "brand_name": "Company Name",
            "primary_keyword": {{
                "keyword": "main keyword",
                "search_volume": 1000,
                "difficulty": 45,
                "current_ranking": 15
            }},
            "secondary_keywords": [
                {{
                    "keyword": "secondary keyword 1",
                    "search_volume": 500,
                    "difficulty": 30,
                    "current_ranking": 45
                }},
                ...
            ]
        }}
        """
        
        try:
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert SEO analyst. Provide accurate keyword analysis with realistic search volumes and difficulty scores based on current market data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.2
            }
            
            response = requests.post(self.base_url, json=payload, headers=self.headers)
            
            if response.status_code != 200:
                print(f"Perplexity API error: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Try to extract JSON from the response
            try:
                # Find JSON in the response (it might be wrapped in markdown code blocks)
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Try to find JSON without code blocks
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = content
                # Fix underscores in numbers (e.g., 1_300 -> 1300)
                json_str = re.sub(r'(\d+)_(\d+)', r'\1\2', json_str)
                # Fix commas in numbers (e.g., 2,400 -> 2400)
                json_str = re.sub(r'(\d+),(\d+)', r'\1\2', json_str)
                
                analysis = json.loads(json_str)
                return analysis
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                print(f"Raw response: {content}")
                return None
                
        except Exception as e:
            print(f"Error calling Perplexity API: {e}")
            return None
    
    def analyze_current_keywords_with_perplexity(self, current_keywords):
        """
        Use Perplexity AI to analyze current keywords and get their metrics
        
        Args:
            current_keywords (dict): Current keywords from extract_current_keywords
            
        Returns:
            dict: Current keywords with search volume and difficulty metrics
        """
        if not current_keywords or not (current_keywords['primary'] or current_keywords['secondary']):
            return {'primary': [], 'secondary': []}
        
        # Combine all current keywords for analysis
        all_current = current_keywords['primary'] + current_keywords['secondary']
        if not all_current:
            return {'primary': [], 'secondary': []}
        
        # Create prompt for analyzing current keywords
        keywords_str = '", "'.join(all_current)
        prompt = f"""
        Analyze the following keywords SPECIFICALLY for the Indian market:
        
        Keywords: ["{keywords_str}"]
        
        IMPORTANT: Provide metrics for India ONLY. Consider:
        - Search volumes from Google India specifically
        - Competition and difficulty within India
        - How Indians search for these terms (Hindi/English variations)
        - Regional preferences and local terminology
        - Current SERP ranking of the website for each keyword
        
        For each keyword, provide estimated metrics for the Indian market:
        - Monthly search volume in India (from Google India data)
        - Keyword difficulty for ranking in India (scale 1-100)
        - Current SERP ranking of the website for this keyword (1-100, or 'Not ranking' if beyond top 100)
        
        Format the response as valid JSON with this structure:
        {{
            "keywords": [
                {{
                    "keyword": "keyword 1",
                    "search_volume": 1000,
                    "difficulty": 45,
                    "current_ranking": 25
                }},
                {{
                    "keyword": "keyword 2", 
                    "search_volume": 500,
                    "difficulty": 30,
                    "current_ranking": "Not ranking"
                }}
            ]
        }}
        """
        
        try:
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert SEO analyst. Provide accurate keyword analysis with realistic search volumes and difficulty scores for the Indian market."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1500,
                "temperature": 0.2
            }
            
            response = requests.post(self.base_url, json=payload, headers=self.headers)
            
            if response.status_code != 200:
                print(f"Perplexity API error for current keywords: {response.status_code}")
                return {'primary': [], 'secondary': []}
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Parse JSON response
            try:
                json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = content
                
                # Fix number formatting issues
                json_str = re.sub(r'(\d+)_(\d+)', r'\1\2', json_str)
                json_str = re.sub(r'(\d+),(\d+)', r'\1\2', json_str)
                
                keyword_analysis = json.loads(json_str)
                analyzed_keywords = keyword_analysis.get('keywords', [])
                
                # Categorize back into primary and secondary with metrics
                analyzed_current = {'primary': [], 'secondary': []}
                
                for kw_data in analyzed_keywords:
                    keyword = kw_data.get('keyword', '')
                    if keyword in current_keywords['primary']:
                        analyzed_current['primary'].append(kw_data)
                    elif keyword in current_keywords['secondary']:
                        analyzed_current['secondary'].append(kw_data)
                
                return analyzed_current
                
            except json.JSONDecodeError as e:
                print(f"Error parsing current keywords JSON: {e}")
                return {'primary': [], 'secondary': []}
                
        except Exception as e:
            print(f"Error analyzing current keywords: {e}")
            return {'primary': [], 'secondary': []}
    
    def format_results_table(self, analysis, url, current_keywords_analyzed=None):
        """
        Format the analysis results into a readable table
        """
        if not analysis:
            return "No analysis results available."
        
        output = []
        output.append("=" * 80)
        output.append("PERPLEXITY AI KEYWORD ANALYSIS REPORT - INDIA MARKET")
        output.append(f"Target Market: India")
        output.append("=" * 80)
        output.append(f"URL: {url}")
        output.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("=" * 80)
        output.append("")
        
        # Brand Name
        brand_name = analysis.get('brand_name', 'Unknown')
        output.append(f"BRAND NAME: {brand_name}")
        output.append("-" * 40)
        output.append("")
        
        # Current Keywords Section with metrics
        if current_keywords_analyzed and (current_keywords_analyzed['primary'] or current_keywords_analyzed['secondary']):
            output.append("CURRENT KEYWORDS (What the site is optimizing for now):")
            output.append("=" * 65)
            
            if current_keywords_analyzed['primary']:
                output.append("Current Primary Keywords:")
                output.append("-" * 30)
                output.append(f"{'Keyword':<35} {'Search Volume':<18} {'Difficulty':<12} {'SERP Rank':<12}")
                output.append("-" * 80)
                for kw_data in current_keywords_analyzed['primary']:
                    keyword = kw_data.get('keyword', 'N/A')
                    volume = kw_data.get('search_volume', 'N/A')
                    difficulty = kw_data.get('difficulty', 'N/A')
                    ranking = kw_data.get('current_ranking', 'N/A')
                    
                    volume_str = f"{volume:,}/mo" if isinstance(volume, int) else str(volume)
                    difficulty_str = f"{difficulty}/100" if isinstance(difficulty, int) else str(difficulty)
                    ranking_str = f"#{ranking}" if isinstance(ranking, int) else str(ranking)
                    
                    output.append(f"{keyword:<35} {volume_str:<18} {difficulty_str:<12} {ranking_str:<12}")
                output.append("")
            
            if current_keywords_analyzed['secondary']:
                output.append("Current Secondary Keywords:")
                output.append("-" * 30)
                output.append(f"{'#':<4} {'Keyword':<30} {'Search Volume':<18} {'Difficulty':<12} {'SERP Rank':<12}")
                output.append("-" * 80)
                for i, kw_data in enumerate(current_keywords_analyzed['secondary'], 1):
                    keyword = kw_data.get('keyword', 'N/A')
                    volume = kw_data.get('search_volume', 'N/A')
                    difficulty = kw_data.get('difficulty', 'N/A')
                    ranking = kw_data.get('current_ranking', 'N/A')
                    
                    volume_str = f"{volume:,}/mo" if isinstance(volume, int) else str(volume)
                    difficulty_str = f"{difficulty}/100" if isinstance(difficulty, int) else str(difficulty)
                    ranking_str = f"#{ranking}" if isinstance(ranking, int) else str(ranking)
                    
                    output.append(f"{i:<4} {keyword:<30} {volume_str:<18} {difficulty_str:<12} {ranking_str:<12}")
                output.append("")
            
            output.append("=" * 65)
            output.append("")
        
        # AI Recommended Keywords Section
        output.append("AI RECOMMENDED KEYWORDS (What the site should target):")
        output.append("=" * 65)
        
        # Primary Keyword
        primary = analysis.get('primary_keyword', {})
        if primary:
            output.append("Recommended Primary Keyword:")
            output.append("-" * 35)
            output.append(f"Keyword: {primary.get('keyword', 'N/A')}")
            output.append(f"Search Volume: {primary.get('search_volume', 'N/A'):,}/month")
            output.append(f"Difficulty: {primary.get('difficulty', 'N/A')}/100")
            ranking = primary.get('current_ranking', 'N/A')
            ranking_str = f"#{ranking}" if isinstance(ranking, int) else str(ranking)
            output.append(f"Current SERP Ranking: {ranking_str}")
            output.append("")
        
        # Secondary Keywords
        secondary = analysis.get('secondary_keywords', [])
        if secondary:
            output.append("Recommended Secondary Keywords:")
            output.append("-" * 35)
            output.append(f"{'#':<4} {'Keyword':<35} {'Search Volume':<18} {'Difficulty':<12} {'SERP Rank':<12}")
            output.append("-" * 85)
            
            for i, kw in enumerate(secondary, 1):
                keyword = kw.get('keyword', 'N/A')
                volume = kw.get('search_volume', 'N/A')
                difficulty = kw.get('difficulty', 'N/A')
                ranking = kw.get('current_ranking', 'N/A')
                
                volume_str = f"{volume:,}/mo" if isinstance(volume, int) else str(volume)
                difficulty_str = f"{difficulty}/100" if isinstance(difficulty, int) else str(difficulty)
                ranking_str = f"#{ranking}" if isinstance(ranking, int) else str(ranking)
                
                output.append(f"{i:<4} {keyword:<35} {volume_str:<18} {difficulty_str:<12} {ranking_str:<12}")
        
        output.append("")
        output.append("=" * 80)
        output.append("Note: Search volumes and difficulty scores are estimates based on AI analysis")
        output.append("and should be verified with dedicated SEO tools for accuracy.")
        output.append("=" * 80)
        
        return "\n".join(output)       
    
    def save_results_to_file(self, formatted_results, url):
        """
        Save the formatted results to a file
        
        Args:
            formatted_results (str): Formatted table string
            url (str): Original URL for filename generation
            
        Returns:
            str: Path to saved file
        """
        try:
            # Create filename from URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace('www.', '').replace('.', '_')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"kwd_{domain}_{timestamp}.txt"
            
            # Save to current directory
            filepath = os.path.join(os.getcwd(), filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(formatted_results)
            
            return filepath
            
        except Exception as e:
            print(f"Error saving results to file: {e}")
            return None
    
    def analyze_url(self, url):
        """
        Complete analysis workflow for a URL
        """
        print(f"Fetching content from: {url}")
        website_content = self.fetch_website_content(url)
        
        if not website_content:
            print("Failed to fetch website content")
            return None
        
        print("Extracting current keywords...")
        current_keywords = self.extract_current_keywords(website_content)
        
        print("Analyzing current keywords with Perplexity AI...")
        current_keywords_analyzed = self.analyze_current_keywords_with_perplexity(current_keywords)
        
        print("Analyzing recommended keywords with Perplexity AI...")
        analysis = self.analyze_keywords_with_perplexity(website_content)
        
        if not analysis:
            print("Failed to analyze keywords")
            return None
        
        print("Formatting results...")
        formatted_results = self.format_results_table(analysis, url, current_keywords_analyzed)
        
        print("Saving results to file...")
        filepath = self.save_results_to_file(formatted_results, url)
        
        if filepath:
            print(f"Results saved to: {filepath}")
        
        # Also print to console
        print("\n" + formatted_results)
        
        return {
            'analysis': analysis,
            'current_keywords_analyzed': current_keywords_analyzed,
            'formatted_results': formatted_results,
            'file_path': filepath
        }

def main():
    """
    Main function for command-line usage
    """
    print("PERPLEXITY AI KEYWORD ANALYZER")
    print("=" * 35)
    
    # Check for API key
    api_key = os.getenv('PPLX_API_KEY')
    if not api_key:
        print("Error: PPLX_API_KEY environment variable not set.")
        print("Please set your Perplexity API key:")
        print("export PPLX_API_KEY='your-api-key-here'")
        return
    
    url = input("Enter website URL to analyze: ").strip()
    
    if not url:
        print("Error: URL is required")
        return
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        analyzer = PerplexityKeywordAnalyzer(api_key)
        result = analyzer.analyze_url(url)
        
        if result:
            print("\nAnalysis completed successfully!")
        else:
            print("\nAnalysis failed. Please check your API key and URL.")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()