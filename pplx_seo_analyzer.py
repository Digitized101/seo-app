#!/usr/bin/env python3

import requests
import os
import json
from urllib.parse import urlparse, urljoin, urlunparse
from datetime import datetime
from bs4 import BeautifulSoup
from keyword_perplexity import PerplexityKeywordAnalyzer
import re

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv('../.env')  # Load from parent directory
except ImportError:
    pass

# Google Drive API imports (commented out - not using anymore)
# try:
#     from googleapiclient.discovery import build
#     from googleapiclient.http import MediaFileUpload
#     from google.oauth2 import service_account
# except ImportError:
#     pass

class PerplexitySEOAnalyzer:
    def __init__(self, pplx_api_key=None, google_api_key=None):
        """Initialize with Perplexity and Google Cloud API keys"""
        self.pplx_api_key = pplx_api_key or os.getenv('PPLX_API_KEY')
        self.google_api_key = google_api_key or os.getenv('GOOGLE_CLOUD_API_KEY')
        print("here line 32")
        self.keyword_analyzer = PerplexityKeywordAnalyzer(self.pplx_api_key)
        print("here line 34")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def discover_urls(self, base_url, max_pages=50):
        """Discover all URLs from the domain"""
        print(f"Discovering URLs from {base_url}...")
        
        discovered_urls = set()
        to_crawl = [base_url]
        crawled = set()
        
        domain = urlparse(base_url).netloc
        
        while to_crawl and len(discovered_urls) < max_pages:
            url = to_crawl.pop(0)
            if url in crawled:
                continue
                
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    discovered_urls.add(url)
                    crawled.add(url)
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find all links
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        full_url = urljoin(url, href)
                        parsed = urlparse(full_url)
                        
                        # Only same domain, no fragments, no query params for crawling
                        if (parsed.netloc == domain and 
                            not parsed.fragment and 
                            full_url not in crawled and 
                            full_url not in to_crawl and
                            len(discovered_urls) < max_pages):
                            to_crawl.append(full_url)
                            
            except Exception as e:
                print(f"Error crawling {url}: {e}")
                continue
        
        print(f"Discovered {len(discovered_urls)} total URLs")
        return list(discovered_urls)
    
    def prioritize_urls(self, urls, base_url):
        """Prioritize URLs based on SEO importance and return top 5 with reasoning"""
        # First, count inbound links for all URLs
        inbound_links = self.count_inbound_links(urls, urlparse(base_url).netloc)
        
        url_scores = []
        
        for url in urls:
            path = urlparse(url).path.lower()
            score = 0
            reasons = []
            
            # Homepage gets highest priority
            if url == base_url or path in ['', '/']:
                score += 100
                reasons.append("Homepage - highest SEO value")
            
            # Important business pages
            if any(keyword in path for keyword in ['about', 'service', 'product', 'contact', 'pricing']):
                score += 80
                reasons.append("Key business page")
            
            # Blog/content pages
            if any(keyword in path for keyword in ['blog', 'news', 'article', 'post']):
                score += 70
                reasons.append("Content page - good for SEO")
            
            # Category/listing pages (shallow depth)
            if path.count('/') == 1 and path != '/':
                score += 60
                reasons.append("Category page - good structure")
            
            # Shorter URLs are generally better
            if len(path) < 20:
                score += 20
                reasons.append("Short URL - user friendly")
            
            # Penalize very deep pages
            depth = path.count('/')
            if depth > 3:
                score -= (depth - 3) * 10
                reasons.append(f"Deep page (depth {depth}) - lower priority")
            
            # Penalize query parameters
            if '?' in url:
                score -= 30
                reasons.append("Has query parameters - lower SEO value")
            
            # Bonus for pages that are linked by other pages (inbound links)
            inbound_count = inbound_links.get(url, 0)
            if inbound_count > 0:
                link_bonus = min(inbound_count * 5, 30)  # Max 30 points bonus
                score += link_bonus
                reasons.append(f"Linked by {inbound_count} other pages (+{link_bonus} points)")
            
            url_scores.append({
                'url': url,
                'score': score,
                'reasons': reasons,
                'path': path,
                'inbound_links': inbound_count
            })
        
        # Sort by score (highest first)
        sorted_urls = sorted(url_scores, key=lambda x: x['score'], reverse=True)
        
        # Show top 5 selection logic
        print("\n🎯 TOP 5 URL SELECTION LOGIC:")
        print("=" * 50)
        for i, url_data in enumerate(sorted_urls[:5], 1):
            print(f"{i}. {url_data['url']} (Score: {url_data['score']})")
            for reason in url_data['reasons']:
                print(f"   • {reason}")
            print()
        
        return [item['url'] for item in sorted_urls[:5]]
    
    def count_inbound_links(self, urls, domain):
        """Count how many pages link to each URL (inbound links)"""
        inbound_links = {url: 0 for url in urls}
        
        for source_url in urls:
            try:
                response = self.session.get(source_url, timeout=10)
                if response.status_code != 200:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(source_url, href)
                    parsed = urlparse(full_url)
                    
                    # Clean URL (remove fragments)
                    clean_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ''))
                    
                    # If this link points to one of our discovered URLs, count it
                    if clean_url in inbound_links and clean_url != source_url:
                        inbound_links[clean_url] += 1
                        
            except Exception:
                continue
        
        return inbound_links
    
    def extract_business_info(self, url):
        """Extract business information from homepage"""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return {}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text().lower()
            
            business_info = {
                'business_name': '',
                'website': url,
                'email': '',
                'phone': '',
                'address': '',
                'reviews_count': '',
                'rating': ''
            }
            
            # Extract business name from title or h1
            title = soup.find('title')
            if title:
                business_info['business_name'] = title.get_text().split('|')[0].split('-')[0].strip()
            
            # Extract email
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            if emails:
                business_info['email'] = emails[0]
            
            # Extract phone number
            phone_patterns = [
                r'\+91[\s-]?\d{10}',  # Indian format
                r'\(\d{3}\)[\s-]?\d{3}[\s-]?\d{4}',  # US format
                r'\d{3}[\s-]?\d{3}[\s-]?\d{4}',  # Simple format
                r'\d{10}'
            ]
            for pattern in phone_patterns:
                phones = re.findall(pattern, text)
                if phones:
                    business_info['phone'] = phones[0]
                    break
            
            # Extract address (look for common address indicators)
            address_indicators = ['address', 'location', 'office', 'headquarters']
            for indicator in address_indicators:
                if indicator in text:
                    # Find text around the indicator
                    start = text.find(indicator)
                    if start != -1:
                        snippet = text[start:start+200]
                        # Look for patterns that might be addresses
                        address_match = re.search(r'[\w\s,.-]{20,100}', snippet)
                        if address_match:
                            business_info['address'] = address_match.group().strip()[:100]
                            break
            
            # Extract reviews and rating from structured data or text
            # Look for schema.org structured data
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if 'aggregateRating' in data:
                            rating_data = data['aggregateRating']
                            business_info['rating'] = str(rating_data.get('ratingValue', ''))
                            business_info['reviews_count'] = str(rating_data.get('reviewCount', ''))
                        elif 'review' in data:
                            business_info['reviews_count'] = str(len(data['review']))
                except:
                    continue
            
            # Look for rating patterns in text
            if not business_info['rating']:
                rating_patterns = [
                    r'(\d\.\d)\s*(?:out of|/|★)\s*5',
                    r'(\d\.\d)\s*stars?',
                    r'rating:?\s*(\d\.\d)'
                ]
                for pattern in rating_patterns:
                    match = re.search(pattern, text)
                    if match:
                        business_info['rating'] = match.group(1)
                        break
            
            # Look for review count patterns
            if not business_info['reviews_count']:
                review_patterns = [
                    r'(\d+)\s*reviews?',
                    r'(\d+)\s*customer reviews?',
                    r'based on\s*(\d+)\s*reviews?'
                ]
                for pattern in review_patterns:
                    match = re.search(pattern, text)
                    if match:
                        business_info['reviews_count'] = match.group(1)
                        break
            
            return business_info
            
        except Exception as e:
            print(f"Error extracting business info: {e}")
            return {}
    
    def analyze_seo_elements(self, url, keywords):
        """Analyze SEO elements of a single page"""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return {'error': f'HTTP {response.status_code}'}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            analysis = {
                'url': url,
                'title': self.analyze_title(soup, keywords),
                'meta_description': self.analyze_meta_description(soup, keywords),
                'headings': self.analyze_headings(soup, keywords),
                'images': self.analyze_images(soup, keywords),
                'body_content': self.analyze_body_content(soup, keywords),
                'overall_score': 0
            }
            
            # Calculate overall score with critical issue detection
            scores = [analysis[key].get('score', 0) for key in ['title', 'meta_description', 'headings', 'images', 'body_content']]
            base_score = sum(scores) / len(scores) if scores else 0
            
            # Check for critical issues that should severely impact score
            critical_issues = self.detect_critical_issues(analysis)
            if critical_issues:
                # Apply severe penalty for critical issues
                penalty = min(len(critical_issues) * 15, 40)  # Max 40 point penalty
                analysis['overall_score'] = max(0, base_score - penalty)
                analysis['critical_issues'] = critical_issues
            else:
                analysis['overall_score'] = base_score
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_title(self, soup, keywords):
        """Analyze title tag"""
        title_tag = soup.find('title')
        if not title_tag:
            return {'score': 0, 'issues': ['Missing title tag'], 'suggestions': ['Add a title tag']}
        
        title = title_tag.get_text().strip()
        issues = []
        suggestions = []
        score = 50  # Base score
        
        # Length check
        if len(title) < 30:
            issues.append('Title too short (< 30 chars)')
            suggestions.append('Expand title to 50-60 characters')
        elif len(title) > 60:
            issues.append('Title too long (> 60 chars)')
            suggestions.append('Shorten title to under 60 characters')
        else:
            score += 20
        
        # Keyword presence
        title_lower = title.lower()
        primary_keywords = keywords[:3] if len(keywords) >= 3 else keywords
        keyword_found = any(kw.lower() in title_lower for kw in primary_keywords)
        
        if keyword_found:
            score += 30
        else:
            issues.append('No target keywords found in title')
            suggestions.append(f'Include keywords: {", ".join(primary_keywords[:2])}')
        
        return {
            'content': title,
            'length': len(title),
            'score': min(score, 100),
            'issues': issues,
            'suggestions': suggestions
        }
    
    def analyze_meta_description(self, soup, keywords):
        """Analyze meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            return {'score': 0, 'issues': ['Missing meta description'], 'suggestions': ['Add meta description']}
        
        description = meta_desc.get('content', '').strip()
        if not description:
            return {'score': 0, 'issues': ['Empty meta description'], 'suggestions': ['Add descriptive content']}
        
        issues = []
        suggestions = []
        score = 50
        
        # Length check
        if len(description) < 120:
            issues.append('Meta description too short (< 120 chars)')
            suggestions.append('Expand to 150-160 characters')
        elif len(description) > 160:
            issues.append('Meta description too long (> 160 chars)')
            suggestions.append('Shorten to under 160 characters')
        else:
            score += 25
        
        # Keyword presence
        desc_lower = description.lower()
        primary_keywords = keywords[:3] if len(keywords) >= 3 else keywords
        keyword_found = any(kw.lower() in desc_lower for kw in primary_keywords)
        
        if keyword_found:
            score += 25
        else:
            issues.append('No target keywords in meta description')
            suggestions.append(f'Include keywords: {", ".join(primary_keywords[:2])}')
        
        return {
            'content': description,
            'length': len(description),
            'score': min(score, 100),
            'issues': issues,
            'suggestions': suggestions
        }
    
    def analyze_headings(self, soup, keywords):
        """Analyze heading structure (H1, H2, etc.)"""
        headings = {}
        issues = []
        suggestions = []
        score = 50
        
        for i in range(1, 7):
            h_tags = soup.find_all(f'h{i}')
            headings[f'h{i}'] = [h.get_text().strip() for h in h_tags]
        
        # H1 analysis
        h1_tags = headings.get('h1', [])
        if not h1_tags:
            issues.append('Missing H1 tag')
            suggestions.append('Add an H1 tag with primary keyword')
            score -= 30
        elif len(h1_tags) > 1:
            issues.append(f'Multiple H1 tags ({len(h1_tags)})')
            suggestions.append('Use only one H1 tag per page')
            score -= 10
        else:
            score += 20
            # Check if H1 contains keywords
            h1_text = h1_tags[0].lower()
            primary_keywords = keywords[:2] if len(keywords) >= 2 else keywords
            if any(kw.lower() in h1_text for kw in primary_keywords):
                score += 15
            else:
                suggestions.append(f'Include keywords in H1: {", ".join(primary_keywords)}')
        
        # H2-H6 structure
        total_headings = sum(len(headings[f'h{i}']) for i in range(2, 7))
        if total_headings == 0:
            issues.append('No H2-H6 headings found')
            suggestions.append('Add H2-H3 headings for better structure')
        else:
            score += 15
        
        return {
            'headings': headings,
            'total_headings': sum(len(h) for h in headings.values()),
            'score': max(0, min(score, 100)),
            'issues': issues,
            'suggestions': suggestions
        }
    
    def analyze_images(self, soup, keywords):
        """Analyze images and alt text"""
        images = soup.find_all('img')
        issues = []
        suggestions = []
        score = 50
        
        if not images:
            return {
                'total_images': 0,
                'score': 100,  # No images is not necessarily bad
                'issues': [],
                'suggestions': []
            }
        
        missing_alt = 0
        empty_alt = 0
        keyword_alt = 0
        
        for img in images:
            alt = img.get('alt', '')
            if not img.has_attr('alt'):
                missing_alt += 1
            elif not alt.strip():
                empty_alt += 1
            else:
                # Check if alt contains keywords
                alt_lower = alt.lower()
                if any(kw.lower() in alt_lower for kw in keywords[:5]):
                    keyword_alt += 1
        
        total_images = len(images)
        
        # Scoring
        if missing_alt > 0:
            issues.append(f'{missing_alt} images missing alt attributes')
            suggestions.append('Add alt attributes to all images')
            score -= min(30, missing_alt * 5)
        
        if empty_alt > 0:
            issues.append(f'{empty_alt} images with empty alt text')
            suggestions.append('Add descriptive alt text')
            score -= min(20, empty_alt * 3)
        
        if keyword_alt == 0 and total_images > 0:
            suggestions.append('Include relevant keywords in some alt texts')
            score -= 10
        elif keyword_alt > 0:
            score += 20
        
        return {
            'total_images': total_images,
            'missing_alt': missing_alt,
            'empty_alt': empty_alt,
            'keyword_alt': keyword_alt,
            'score': max(0, min(score, 100)),
            'issues': issues,
            'suggestions': suggestions
        }
    
    def detect_critical_issues(self, analysis):
        """Detect critical SEO issues that should severely impact page score"""
        critical_issues = []
        
        # Critical title issues
        title_data = analysis.get('title', {})
        if isinstance(title_data, dict):
            if title_data.get('score', 0) == 0:  # Missing title
                critical_issues.append('Missing title tag')
            elif 'Missing title tag' in title_data.get('issues', []):
                critical_issues.append('Missing title tag')
            elif title_data.get('score', 0) < 30:  # Very poor title
                critical_issues.append('Severely inadequate title')
        
        # Critical meta description issues
        meta_data = analysis.get('meta_description', {})
        if isinstance(meta_data, dict):
            if meta_data.get('score', 0) == 0:  # Missing meta description
                critical_issues.append('Missing meta description')
        
        # Critical heading issues
        headings_data = analysis.get('headings', {})
        if isinstance(headings_data, dict):
            if 'Missing H1 tag' in headings_data.get('issues', []):
                critical_issues.append('Missing H1 tag')
            elif headings_data.get('score', 0) < 20:  # Very poor heading structure
                critical_issues.append('Poor heading structure')
        
        # Critical content issues
        content_data = analysis.get('body_content', {})
        if isinstance(content_data, dict):
            if content_data.get('word_count', 0) < 100:  # Extremely low content
                critical_issues.append('Insufficient content (< 100 words)')
            elif content_data.get('score', 0) < 20:  # Very poor content
                critical_issues.append('Poor content quality')
        
        return critical_issues
    
    def analyze_body_content(self, soup, keywords):
        """Analyze body content for keyword usage and quality"""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        words = text.split()
        word_count = len(words)
        
        issues = []
        suggestions = []
        score = 50
        
        # Word count analysis
        if word_count < 300:
            issues.append(f'Low word count ({word_count} words)')
            suggestions.append('Add more content (aim for 300+ words)')
            score -= 20
        elif word_count > 300:
            score += 20
        
        # Keyword density analysis
        text_lower = text.lower()
        keyword_mentions = {}
        
        for keyword in keywords[:5]:  # Check top 5 keywords
            mentions = text_lower.count(keyword.lower())
            if mentions > 0:
                density = (mentions / word_count) * 100
                keyword_mentions[keyword] = {'mentions': mentions, 'density': density}
                
                if 0.5 <= density <= 2.5:  # Good density range
                    score += 5
                elif density > 3:
                    issues.append(f'Keyword "{keyword}" overused ({density:.1f}% density)')
                    suggestions.append(f'Reduce usage of "{keyword}"')
        
        if not keyword_mentions:
            issues.append('No target keywords found in content')
            suggestions.append(f'Include keywords naturally: {", ".join(keywords[:3])}')
            score -= 30
        
        return {
            'word_count': word_count,
            'keyword_mentions': keyword_mentions,
            'score': max(0, min(score, 100)),
            'issues': issues,
            'suggestions': suggestions
        }
    
    def generate_report(self, base_url, max_pages=10):
        """Generate comprehensive SEO report"""
        try:
            print(f"Starting SEO analysis for {base_url}")
            
            # Step 1: Extract business information
            print("Extracting business information...")
            business_info = self.extract_business_info(base_url)
            
            # Step 2: Discover all URLs and prioritize top 5
            print("Discovering URLs...")
            all_urls = self.discover_urls(base_url, max_pages)
            if not all_urls:
                print("Error: No URLs discovered")
                return None
                
            urls = self.prioritize_urls(all_urls, base_url)
            if not urls:
                print("Error: No URLs prioritized")
                return None
            
            # Step 3: Try to load keywords from existing file first
            print("Checking for existing keyword analysis file...")
            existing_keywords = self.load_keywords_from_file(base_url)
            
            if existing_keywords:
                print("Using existing keyword analysis from file")
                current_keywords = existing_keywords['current_keywords']
                recommended_keywords = existing_keywords['recommended_keywords']
                
                # Extract keywords for SEO analysis
                keywords = []
                if current_keywords.get('primary'):
                    keywords.extend([kw['keyword'] if isinstance(kw, dict) else kw for kw in current_keywords['primary']])
                if current_keywords.get('secondary'):
                    keywords.extend([kw['keyword'] if isinstance(kw, dict) else kw for kw in current_keywords['secondary'][:5]])
                
                if not keywords:
                    if recommended_keywords.get('primary_keyword', {}).get('keyword'):
                        keywords.append(recommended_keywords['primary_keyword']['keyword'])
                    keywords.extend([kw.get('keyword', '') for kw in recommended_keywords.get('secondary_keywords', [])[:4] if kw.get('keyword')])
                
                seo_analysis = {
                    'keywords': keywords,
                    'current_keywords': current_keywords,
                    'recommended_keywords': recommended_keywords
                }
                keyword_reports = None
            else:
                # Step 3: Generate keyword analysis using keyword_perplexity module
                print("Performing keyword analysis with Perplexity AI...")
                keyword_result = self.keyword_analyzer.analyze_url(base_url)
                keyword_analysis = keyword_result.get('analysis') if keyword_result else None
                
                if not keyword_analysis:
                    print("Failed to generate keyword analysis, using fallback...")
                    keywords = ['SEO', 'Website', 'Analysis']
                    seo_analysis = None
                    keyword_reports = None
                else:
                    # Use current keywords from keyword_perplexity analysis for SEO work  
                    current_keywords_analyzed = keyword_result.get('current_keywords_analyzed', {}) if keyword_result else {}
                    current_keywords = {}
                    if current_keywords_analyzed.get('primary'):
                        current_keywords['primary'] = [kw.get('keyword', '') for kw in current_keywords_analyzed['primary']]
                    if current_keywords_analyzed.get('secondary'):
                        current_keywords['secondary'] = [kw.get('keyword', '') for kw in current_keywords_analyzed['secondary']]
                    
                    # Extract all current keywords (primary + secondary) for SEO analysis
                    keywords = []
                    if current_keywords.get('primary'):
                        keywords.extend(current_keywords['primary'])
                    if current_keywords.get('secondary'):
                        keywords.extend(current_keywords['secondary'][:5])  # Top 5 secondary
                    
                    # If no current keywords found, use recommended keywords as fallback
                    if not keywords:
                        primary_kw = keyword_analysis.get('primary_keyword', {})
                        secondary_kws = keyword_analysis.get('secondary_keywords', [])
                        
                        if primary_kw.get('keyword'):
                            keywords.append(primary_kw['keyword'])
                        keywords.extend([kw.get('keyword', '') for kw in secondary_kws[:4] if kw.get('keyword')])
                        print("   ⚠️ No current keywords found, using recommended keywords as fallback")
                    else:
                        print("   ✅ Using current keywords for SEO element analysis")
                    
                    # Use the formatted results from keyword_result
                    print("Using keyword analysis reports...")
                    keyword_reports = {
                        'html_content': self.generate_keyword_html_report(keyword_result),
                        'text_content': keyword_result.get('formatted_results', '')
                    } if keyword_result else None
                    
                    # Use keyword analysis as seo_analysis for the report
                    seo_analysis = {
                        'keywords': keywords,
                        'perplexity_analysis': keyword_analysis,
                        'keyword_reports': keyword_reports
                    }
            
            # Print detailed keyword analysis results
            if seo_analysis and 'perplexity_analysis' in seo_analysis:
                analysis = seo_analysis['perplexity_analysis']
                print("\n🎯 KEYWORD ANALYSIS RESULTS:")
                print("=" * 50)
                
                # Primary keyword
                primary_kw = analysis.get('primary_keyword', {})
                if primary_kw:
                    print(f"🔥 PRIMARY KEYWORD: {primary_kw.get('keyword', 'N/A')}")
                    print(f"   Search Volume: {primary_kw.get('search_volume', 'N/A')}/month")
                    print(f"   Difficulty: {primary_kw.get('difficulty', 'N/A')}/100")
                    print(f"   Current Rank: {primary_kw.get('current_rank', 'Not ranking')}")
                
                # Secondary keywords
                secondary_kws = analysis.get('secondary_keywords', [])
                if secondary_kws:
                    print(f"\n📋 SECONDARY KEYWORDS ({len(secondary_kws)} found):")
                    for i, kw in enumerate(secondary_kws[:5], 1):
                        print(f"   {i}. {kw.get('keyword', 'N/A')} (Vol: {kw.get('search_volume', 'N/A')}/mo, Diff: {kw.get('difficulty', 'N/A')}/100)")
                
                # Brand name
                brand_name = analysis.get('brand_name', business_info.get('business_name', 'Not found'))
                print(f"\n🏢 BRAND NAME: {brand_name}")
                
                print(f"\n📊 Using {len(keywords)} CURRENT keywords for SEO analysis: {', '.join(keywords[:5])}")
                
                # Show which keywords are being used
                current_kws = analysis.get('current_keywords', {})
                if current_kws.get('primary') or current_kws.get('secondary'):
                    print("\n🎯 CURRENT KEYWORDS DETECTED:")
                    if current_kws.get('primary'):
                        print(f"   Primary: {', '.join(current_kws['primary'])}")
                    if current_kws.get('secondary'):
                        print(f"   Secondary: {', '.join(current_kws['secondary'][:5])}")
                    # Don't print the success message here since it's printed above
                else:
                    # Don't print the fallback message here since it's printed above
                    pass
            else:
                print(f"Using fallback keywords for SEO analysis: {keywords[:5]}")
                print(f"Business: {business_info.get('business_name', 'Not found')}")
            
            # Step 4: Analyze each URL
            print(f"Analyzing {len(urls)} pages...")
            page_analyses = []
            
            for i, url in enumerate(urls, 1):
                try:
                    print(f"  Analyzing page {i}/{len(urls)}: {url}")
                    analysis = self.analyze_seo_elements(url, keywords)
                    
                    # Add PageSpeed Insights only for top priority page (first URL)
                    if i == 1 and self.google_api_key:
                        print(f"  Getting PageSpeed Insights for top priority page: {url}")
                        analysis['page_insights'] = self.get_pagespeed_insights(url)
                    
                    page_analyses.append(analysis)
                except Exception as e:
                    print(f"  Error analyzing {url}: {e}")
                    page_analyses.append({'url': url, 'error': str(e)})
            
            # Step 5: Generate summary
            try:
                summary = self.generate_summary(page_analyses)
                if 'error' in summary:
                    print(f"Error generating summary: {summary['error']}")
                    return None
            except Exception as e:
                print(f"Error in generate_summary: {e}")
                return None
        
            # Step 6: Compile final report
            try:
                report = {
                    'metadata': {
                        'base_url': base_url,
                        'analysis_date': datetime.now().isoformat(),
                        'pages_analyzed': len(page_analyses),
                        'keywords_used': keywords,
                        'keyword_analysis': seo_analysis if seo_analysis else keyword_analysis,
                    'keyword_reports': keyword_reports
                    },
                    'business_info': business_info,
                    'summary': summary,
                    'pages': page_analyses
                }
                
                print(f"Report compiled successfully with {len(page_analyses)} pages")
                return report
                
            except Exception as e:
                print(f"Error compiling final report: {e}")
                return None
                
        except Exception as e:
            print(f"Unexpected error in generate_report: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_advanced_seo_analysis(self, base_url, top_urls):
        """Get advanced SEO analysis from Perplexity AI"""
        try:
            urls_text = '\n'.join([f"- {url}" for url in top_urls])
            
            prompt = f"""
Act as an advanced SEO specialist. For my website {base_url}, analyze only the top 5 traffic-driving pages:

{urls_text}

For each page, provide:
1. A full SEO audit covering on-page optimization, user engagement metrics
2. Top-performing organic keywords with current rankings and keyword gaps
3. Compare against top 3 competitor pages - content gaps, backlink strengths
4. Actionable improvements prioritized by impact

Return JSON format:
{{
    "keywords": ["primary", "secondary1", "secondary2"],
    "pages": [{{
        "url": "page_url",
        "seo_score": "score/100",
        "strengths": ["strength1", "strength2"],
        "weaknesses": ["weakness1", "weakness2"],
        "recommendations": [{{
            "action": "specific action",
            "priority": "high/medium/low",
            "impact": "expected impact"
        }}]
    }}],
    "technical_issues": [{{
        "issue": "description",
        "severity": "critical/high/medium/low",
        "fix": "solution"
    }}]
}}
"""
            
            payload = {
                "model": "sonar-pro",
                "messages": [
                    {"role": "system", "content": "You are an expert SEO specialist. Provide detailed, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 4000,
                "temperature": 0.2
            }
            
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.pplx_api_key}", "Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                return None
            
            content = response.json()['choices'][0]['message']['content']
            
            # Parse JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                json_str = json_match.group(0) if json_match else content
            
            return json.loads(json_str)
            
        except Exception as e:
            print(f"Error getting advanced SEO analysis: {e}")
            return None
    
    def generate_summary(self, page_analyses):
        """Generate summary statistics"""
        total_pages = len(page_analyses)
        pages_with_errors = sum(1 for p in page_analyses if 'error' in p)
        successful_pages = total_pages - pages_with_errors
        
        if successful_pages == 0:
            return {'error': 'No pages could be analyzed'}
        
        # Calculate average scores
        avg_scores = {}
        for element in ['title', 'meta_description', 'headings', 'images', 'body_content', 'overall_score']:
            scores = [p[element].get('score', 0) if element in p and isinstance(p[element], dict) 
                     else p.get(element, 0) for p in page_analyses if 'error' not in p]
            avg_scores[f'avg_{element}_score'] = sum(scores) / len(scores) if scores else 0
        
        # Count total issues
        total_issues = 0
        common_issues = {}
        
        for page in page_analyses:
            if 'error' in page:
                continue
            for element in ['title', 'meta_description', 'headings', 'images', 'body_content']:
                if element in page and isinstance(page[element], dict):
                    issues = page[element].get('issues', [])
                    total_issues += len(issues)
                    for issue in issues:
                        common_issues[issue] = common_issues.get(issue, 0) + 1
        
        return {
            'total_pages': total_pages,
            'successful_pages': successful_pages,
            'pages_with_errors': pages_with_errors,
            'total_issues': total_issues,
            'common_issues': dict(sorted(common_issues.items(), key=lambda x: x[1], reverse=True)[:10]),
            **avg_scores
        }
    
    def save_report(self, report, base_url):
        """Save report to Google Drive SEO/reports folder"""
        domain = urlparse(base_url).netloc.replace('www.', '').replace('.', '_')
        
        # Create reports directory locally
        reports_dir = './reports'
        os.makedirs(reports_dir, exist_ok=True)
        
        # Use domain name as filename
        json_filename = os.path.join(reports_dir, f"{domain}_seo_report.json")
        html_filename = os.path.join(reports_dir, f"{domain}_seo_report.html")
        
        # Save JSON report
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Generate and save HTML report with PageSpeed data
        html_content = self.generate_html_report(report)
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Also save the standalone keyword reports if available
        keyword_reports = report.get('keyword_reports')
        if keyword_reports:
            if keyword_reports.get('html_content'):
                keyword_html_file = os.path.join(reports_dir, f"{domain}_keyword_analysis.html")
                with open(keyword_html_file, 'w', encoding='utf-8') as f:
                    f.write(keyword_reports['html_content'])
                print(f"  Keyword HTML: {keyword_html_file}")
            
            if keyword_reports.get('text_content'):
                keyword_text_file = os.path.join(reports_dir, f"{domain}_keyword_analysis.txt")
                with open(keyword_text_file, 'w', encoding='utf-8') as f:
                    f.write(keyword_reports['text_content'])
                print(f"  Keyword Text: {keyword_text_file}")
        
        print(f"Reports saved locally:")
        print(f"  HTML: {html_filename}")
        print(f"  JSON: {json_filename}")
        
        # Google Drive upload disabled - not using anymore
        # print(f"Google Drive upload skipped - focusing on core SEO analysis first")
        
        return html_filename
    
    def get_pagespeed_insights(self, url):
        """Get PageSpeed Insights data using Google Cloud API"""
        if not self.google_api_key:
            return {'error': 'Google Cloud API key not provided'}
        
        try:
            # PageSpeed Insights API endpoint
            api_url = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
            
            results = {}
            
            # Get mobile and desktop scores
            for strategy in ['mobile', 'desktop']:
                params = {
                    'url': url,
                    'key': self.google_api_key,
                    'strategy': strategy,
                    'category': ['performance', 'accessibility', 'best-practices', 'seo']
                }
                
                response = requests.get(api_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    lighthouse_result = data.get('lighthouseResult', {})
                    categories = lighthouse_result.get('categories', {})
                    
                    results[strategy] = {
                        'performance': categories.get('performance', {}).get('score', 0) * 100,
                        'accessibility': categories.get('accessibility', {}).get('score', 0) * 100,
                        'best_practices': categories.get('best-practices', {}).get('score', 0) * 100,
                        'seo': categories.get('seo', {}).get('score', 0) * 100
                    }
                else:
                    results[strategy] = {'error': f'API error: {response.status_code}'}
            
            return results
            
        except Exception as e:
            return {'error': f'PageSpeed Insights error: {str(e)}'}
    
    def get_visual_indicator(self, score, threshold_good=80, threshold_ok=60):
        """Get visual indicator based on score with stricter thresholds"""
        if score >= threshold_good:
            return '✅', 'good'
        elif score >= threshold_ok:
            return '⚠️', 'warning'
        else:
            return '❌', 'error'
    
    def calculate_weighted_score(self, pages):
        """Calculate weighted overall score: top 2 pages (50%), next 2 (40%), last (10%)"""
        valid_pages = [p for p in pages if 'error' not in p and 'overall_score' in p]
        if not valid_pages:
            return 0
        
        weights = [0.25, 0.25, 0.2, 0.2, 0.1]  # Top 2: 50%, Next 2: 40%, Last: 10%
        weighted_score = 0
        
        for i, page in enumerate(valid_pages[:5]):
            weight = weights[i] if i < len(weights) else 0
            weighted_score += page['overall_score'] * weight
        
        return weighted_score
    
    def load_keywords_from_file(self, base_url):
        """Load keywords from existing kwd_<domain>_<timestamp> file"""
        import glob
        from urllib.parse import urlparse
        
        domain = urlparse(base_url).netloc.replace('www.', '')
        domain_parts = domain.split('.')
        domain_name = domain_parts[0]
        domain_ext = domain_parts[1] if len(domain_parts) > 1 else 'com'
        
        # Look for kwd_<domain>_<ext>_<timestamp> files
        pattern = f"kwd_{domain_name}_{domain_ext}_*.txt"
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
            recommended_keywords = {'primary_keyword': {}, 'secondary_keywords': []}
            
            lines = content.split('\n')
            section = None
            
            in_current_primary = False
            in_current_secondary = False
            in_recommended_primary = False
            in_recommended_secondary = False
            
            for line in lines:
                line = line.strip()
                
                if 'Current Primary Keywords:' in line:
                    in_current_primary = True
                    in_current_secondary = False
                    in_recommended_primary = False
                    in_recommended_secondary = False
                elif 'Current Secondary Keywords:' in line:
                    in_current_primary = False
                    in_current_secondary = True
                    in_recommended_primary = False
                    in_recommended_secondary = False
                elif 'Recommended Primary Keyword:' in line:
                    in_current_primary = False
                    in_current_secondary = False
                    in_recommended_primary = True
                    in_recommended_secondary = False
                elif 'Recommended Secondary Keywords:' in line:
                    in_current_primary = False
                    in_current_secondary = False
                    in_recommended_primary = False
                    in_recommended_secondary = True
                elif line and any([in_current_primary, in_current_secondary, in_recommended_primary, in_recommended_secondary]):
                    # Skip header lines
                    if 'Keyword' in line and 'Search Volume' in line:
                        continue
                    if line.startswith('-') or line.startswith('='):
                        continue
                    if line.startswith('#'):
                        continue
                    
                    # Parse keyword lines using regex to handle multi-word phrases
                    import re
                    
                    if in_current_primary or in_current_secondary:
                        # Format: Wire Mesh                           22,000/mo          58/100       Not ranking
                        # Use regex to extract: keyword, volume, difficulty, ranking
                        match = re.match(r'^(.+?)\s+(\d+[,\d]*\/mo)\s+(\d+\/100)\s+(.+)$', line)
                        if match:
                            keyword = match.group(1).strip()
                            volume = match.group(2)
                            difficulty = match.group(3)
                            rank = match.group(4).strip()
                            
                            kw_data = {
                                'keyword': keyword,
                                'search_volume': volume,
                                'difficulty': difficulty,
                                'serp_rank': rank
                            }
                            
                            if in_current_primary:
                                current_keywords['primary'].append(kw_data)
                            else:
                                current_keywords['secondary'].append(kw_data)
                    
                    elif in_recommended_primary:
                        if line.startswith('Keyword:'):
                            keyword = line.replace('Keyword:', '').strip()
                            recommended_keywords['primary_keyword']['keyword'] = keyword
                        elif line.startswith('Search Volume:'):
                            volume = line.replace('Search Volume:', '').strip()
                            recommended_keywords['primary_keyword']['search_volume'] = volume
                        elif line.startswith('Difficulty:'):
                            difficulty = line.replace('Difficulty:', '').strip()
                            recommended_keywords['primary_keyword']['difficulty'] = difficulty
                    
                    elif in_recommended_secondary:
                        # Format: 1    mosquito net manufacturer in Nagpur 350/mo             35/100       Not ranking
                        match = re.match(r'^\d+\s+(.+?)\s+(\d+[,\d]*\/mo)\s+(\d+\/100)\s+(.+)$', line)
                        if match:
                            keyword = match.group(1).strip()
                            volume = match.group(2)
                            difficulty = match.group(3)
                            rank = match.group(4).strip()
                            
                            recommended_keywords['secondary_keywords'].append({
                                'keyword': keyword,
                                'search_volume': volume,
                                'difficulty': difficulty,
                                'serp_rank': rank
                            })
            
            return {
                'current_keywords': current_keywords,
                'recommended_keywords': recommended_keywords
            }
            
        except Exception as e:
            print(f"Error reading keyword file: {e}")
            return None
    
    def generate_keyword_html_report(self, keyword_result):
        """Generate HTML report from keyword analysis result"""
        if not keyword_result:
            return "<p>No keyword analysis available</p>"
        
        text_content = keyword_result.get('formatted_results', '')
        if not text_content:
            return "<p>No keyword analysis results</p>"
        
        # Convert text report to HTML
        html_lines = []
        lines = text_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                html_lines.append('<br>')
            elif line.startswith('='):
                html_lines.append(f'<h2 style="color: #333; border-bottom: 2px solid #007bff; padding-bottom: 5px;">{line.replace("=", "").strip()}</h2>')
            elif line.startswith('-'):
                html_lines.append(f'<h3 style="color: #666; margin-top: 20px;">{line.replace("-", "").strip()}</h3>')
            elif 'Keyword' in line and 'Search Volume' in line:
                # Table header
                html_lines.append('<table style="width: 100%; border-collapse: collapse; margin: 10px 0;">')
                html_lines.append(f'<tr style="background: #f8f9fa; font-weight: bold;"><td style="padding: 8px; border: 1px solid #ddd;">{line}</td></tr>')
            elif line.count(' ') > 10 and any(char.isdigit() for char in line):
                # Table row
                html_lines.append(f'<tr><td style="padding: 8px; border: 1px solid #ddd; font-family: monospace;">{line}</td></tr>')
            elif line.startswith('#') and 'Keyword' in line:
                # Close previous table and start new one
                html_lines.append('</table>')
                html_lines.append('<table style="width: 100%; border-collapse: collapse; margin: 10px 0;">')
                html_lines.append(f'<tr style="background: #f8f9fa; font-weight: bold;"><td style="padding: 8px; border: 1px solid #ddd;">{line}</td></tr>')
            else:
                html_lines.append(f'<p style="margin: 5px 0;">{line}</p>')
        
        # Close any open table
        if '<table' in ''.join(html_lines[-10:]) and '</table>' not in ''.join(html_lines[-5:]):
            html_lines.append('</table>')
        
        return '\n'.join(html_lines)
    
    def generate_html_report(self, report):
        """Generate comprehensive HTML report with visual indicators"""
        metadata = report['metadata']
        summary = report['summary']
        pages = report['pages']
        
        # Get keyword analysis data
        keyword_analysis = metadata.get('keyword_analysis', {})
        if keyword_analysis and 'current_keywords' in keyword_analysis:
            # Using file-based keywords
            current_keywords = keyword_analysis.get('current_keywords', {})
            recommended_keywords = keyword_analysis.get('recommended_keywords', {})
        else:
            # Using perplexity analysis
            perplexity_analysis = keyword_analysis.get('perplexity_analysis', {}) if keyword_analysis else {}
            current_keywords = perplexity_analysis.get('current_keywords', {}) if perplexity_analysis else {}
            recommended_keywords = perplexity_analysis if perplexity_analysis else {}
        
        # Get business info first
        business_info = report.get('business_info', {})
        
        # Extract brand name from analysis or business info
        brand_name = 'Unknown Brand'
        if recommended_keywords:
            brand_name = recommended_keywords.get('brand_name', business_info.get('business_name', 'Unknown Brand'))
        elif business_info.get('business_name'):
            brand_name = business_info.get('business_name')
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SEO Analysis Report - {business_info.get('business_name', metadata['base_url'])}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #eee; }}
        .business-info {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; text-align: left; }}
        .business-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .business-item {{ margin: 10px 0; }}
        .business-label {{ font-weight: bold; color: #666; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }}
        .summary-card.good {{ border-left-color: #28a745; }}
        .summary-card.warning {{ border-left-color: #ffc107; }}
        .summary-card.error {{ border-left-color: #dc3545; }}
        .score {{ font-size: 2em; font-weight: bold; margin: 10px 0; }}
        .indicator {{ font-size: 1.5em; margin-right: 10px; }}
        .keywords-section {{ background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .keywords-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .keyword-list {{ background: white; padding: 15px; border-radius: 5px; }}
        .page-analysis {{ margin: 30px 0; padding: 20px; background: white; border: 1px solid #ddd; border-radius: 8px; }}
        .page-header {{ background: #f8f9fa; padding: 15px; margin: -20px -20px 20px -20px; border-radius: 8px 8px 0 0; }}
        .element-analysis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin: 15px 0; }}
        .element-card {{ border: 1px solid #ddd; border-radius: 5px; padding: 15px; }}
        .element-card.good {{ border-left: 4px solid #28a745; }}
        .element-card.warning {{ border-left: 4px solid #ffc107; }}
        .element-card.error {{ border-left: 4px solid #dc3545; }}
        .issues {{ color: #dc3545; margin: 10px 0; }}
        .suggestions {{ color: #007bff; margin: 10px 0; }}
        .url {{ color: #666; font-size: 0.9em; word-break: break-all; }}
        h1, h2, h3 {{ color: #333; }}
        .metric {{ display: inline-block; margin: 5px 10px 5px 0; padding: 5px 10px; background: #e9ecef; border-radius: 3px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 SEO Analysis Report</h1>
            <h2>{brand_name}</h2>
            <p><em>Business: {business_info.get('business_name', 'Not found')}</em></p>
            <div class="url">{metadata['base_url']}</div>
            <p>Analysis Date: {metadata['analysis_date']} | Pages Analyzed: {summary['successful_pages']}/{summary['total_pages']}</p>
        </div>
        
        <!-- Weighted Overall Score -->
        <div style="text-align: center; margin: 30px 0; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;">
            <h2 style="color: white; margin-bottom: 20px;">🏆 Overall Website SEO Score</h2>
            <div style="font-size: 4em; font-weight: bold; margin: 20px 0;">{self.calculate_weighted_score(pages):.0f}/100</div>
            <p style="opacity: 0.9; margin: 0;">Weighted by page priority: Top 2 pages (50%), Next 2 pages (40%), Last page (10%)</p>
        </div>
        
        <div class="business-info">
            <h2>📋 Business Information</h2>
            <div class="business-grid">
                <div>
                    <div class="business-item">
                        <span class="business-label">Business Name:</span> {business_info.get('business_name', 'Not found')}
                    </div>
                    <div class="business-item">
                        <span class="business-label">Brand Name:</span> <strong>{brand_name}</strong>
                    </div>
                    <div class="business-item">
                        <span class="business-label">Website:</span> <a href="{business_info.get('website', '')}" target="_blank">{business_info.get('website', 'Not found')}</a>
                    </div>
                    <div class="business-item">
                        <span class="business-label">Email:</span> {business_info.get('email', 'Not found')}
                    </div>
                </div>
                <div>
                    <div class="business-item">
                        <span class="business-label">Phone:</span> {business_info.get('phone', 'Not found')}
                    </div>
                    <div class="business-item">
                        <span class="business-label">Address:</span> {business_info.get('address', 'Not found')}
                    </div>
                    <div class="business-item">
                        <span class="business-label">Reviews:</span> {business_info.get('reviews_count', 'Not found')} reviews | Rating: {business_info.get('rating', 'Not found')}/5 ⭐
                    </div>
                </div>
            </div>
        </div>
"""
        
        # Overall Summary Section
        html += """
        <h2>📊 Overall Website Summary</h2>
        <div class="summary-grid">
"""
        
        # Architecture Score
        arch_score = summary.get('avg_overall_score_score', 0)
        indicator, status = self.get_visual_indicator(arch_score)
        html += f"""
            <div class="summary-card {status}">
                <div class="indicator">{indicator}</div>
                <div class="score">{arch_score:.0f}/100</div>
                <div>Website Architecture</div>
            </div>
"""
        
        # Individual element scores
        elements = [
            ('Title Tags', 'avg_title_score'),
            ('Meta Descriptions', 'avg_meta_description_score'),
            ('Headings', 'avg_headings_score'),
            ('Images', 'avg_images_score'),
            ('Body Content', 'avg_body_content_score')
        ]
        
        for element_name, score_key in elements:
            score = summary.get(score_key, 0)
            indicator, status = self.get_visual_indicator(score)
            html += f"""
            <div class="summary-card {status}">
                <div class="indicator">{indicator}</div>
                <div class="score">{score:.0f}/100</div>
                <div>{element_name}</div>
            </div>
"""
        
        # Total images count
        total_images = sum(p.get('images', {}).get('total_images', 0) for p in pages if 'error' not in p)
        html += f"""
            <div class="summary-card">
                <div class="indicator">🖼️</div>
                <div class="score">{total_images}</div>
                <div>Total Images</div>
            </div>
        """
        
        # PageSpeed Insights for top page
        top_page = next((p for p in pages if 'error' not in p and 'page_insights' in p), None)
        if top_page and 'page_insights' in top_page:
            insights = top_page['page_insights']
            if 'mobile' in insights and 'error' not in insights['mobile']:
                mobile_perf = insights['mobile'].get('performance', 0)
                indicator, status = self.get_visual_indicator(mobile_perf)
                html += f"""
            <div class="summary-card {status}">
                <div class="indicator">{indicator}</div>
                <div class="score">{mobile_perf:.0f}/100</div>
                <div>Mobile Performance</div>
            </div>
                """
        
        html += "</div>"
        
        # Keywords Section - Show only current keywords
        html += """
        <div class="keywords-section">
            <h2>🎯 Current Keywords Analysis</h2>
        """
        
        # Display current keywords in table format
        if current_keywords.get('primary') or current_keywords.get('secondary'):
            html += "<table style='width: 100%; border-collapse: collapse; font-size: 0.9em; margin: 20px 0;'>"
            html += "<tr style='background: #f8f9fa; font-weight: bold;'><th style='padding: 12px; border: 1px solid #ddd; text-align: left;'>Keyword</th><th style='padding: 12px; border: 1px solid #ddd; text-align: center;'>Volume</th><th style='padding: 12px; border: 1px solid #ddd; text-align: center;'>Difficulty</th><th style='padding: 12px; border: 1px solid #ddd; text-align: center;'>SERP Rank</th></tr>"
            
            # Primary keywords
            for kw in current_keywords.get('primary', []):
                if isinstance(kw, dict):
                    html += f"<tr style='background: #e8f5e8;'><td style='padding: 12px; border: 1px solid #ddd; font-weight: bold;'>🎯 {kw['keyword']}</td><td style='padding: 12px; border: 1px solid #ddd; text-align: center;'>{kw['search_volume']}</td><td style='padding: 12px; border: 1px solid #ddd; text-align: center;'>{kw['difficulty']}</td><td style='padding: 12px; border: 1px solid #ddd; text-align: center;'>{kw['serp_rank']}</td></tr>"
            
            # Secondary keywords
            for kw in current_keywords.get('secondary', [])[:8]:
                if isinstance(kw, dict):
                    html += f"<tr><td style='padding: 12px; border: 1px solid #ddd;'>📋 {kw['keyword']}</td><td style='padding: 12px; border: 1px solid #ddd; text-align: center;'>{kw['search_volume']}</td><td style='padding: 12px; border: 1px solid #ddd; text-align: center;'>{kw['difficulty']}</td><td style='padding: 12px; border: 1px solid #ddd; text-align: center;'>{kw['serp_rank']}</td></tr>"
            
            html += "</table>"
        else:
            html += "<p style='text-align: center; padding: 20px; color: #666;'>⚠️ No current keywords found</p>"
        html += "</div>"
        
        # Include detailed keyword analysis if available
        keyword_reports = report.get('keyword_reports')
        if keyword_reports and keyword_reports.get('html_content'):
            html += f"""
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3>📊 Detailed Keyword Analysis (Powered by Perplexity AI)</h3>
            <div style="background: white; padding: 15px; border-radius: 5px; margin-top: 15px;">
                {keyword_reports['html_content']}
            </div>
        </div>
            """
        
        # Page-by-Page Analysis
        html += "<h2>📄 Detailed Page Analysis</h2>"
        
        for i, page in enumerate(pages, 1):
            if 'error' in page:
                html += f"""
                <div class="page-analysis">
                    <div class="page-header">
                        <h3>❌ Page {i}: Error</h3>
                        <div class="url">{page.get('url', 'Unknown URL')}</div>
                    </div>
                    <p class="issues">Error: {page['error']}</p>
                </div>
                """
                continue
            
            overall_score = page.get('overall_score', 0)
            indicator, status = self.get_visual_indicator(overall_score)
            
            html += f"""
            <div class="page-analysis">
                <div class="page-header">
                    <h3>{indicator} Page {i}: Overall Score {overall_score:.0f}/100</h3>
                    <div class="url">{page['url']}</div>
                    {f'<div style="color: #dc3545; font-weight: bold; margin-top: 10px;">🚨 Critical Issues: {", ".join(page.get("critical_issues", []))}</div>' if page.get('critical_issues') else ''}
                </div>
                <div class="element-analysis">
            """
            
            # Analyze each element
            elements = ['title', 'meta_description', 'headings', 'images', 'body_content']
            for element in elements:
                if element not in page or not isinstance(page[element], dict):
                    continue
                
                data = page[element]
                score = data.get('score', 0)
                indicator, status = self.get_visual_indicator(score)
                
                html += f"""
                <div class="element-card {status}">
                    <h4>{indicator} {element.replace('_', ' ').title()} ({score:.0f}/100)</h4>
                """
                
                # Add specific metrics
                if element == 'title' and 'content' in data:
                    html += f"<div class='metric'>Length: {data.get('length', 0)} chars</div>"
                    html += f"<p><strong>Content:</strong> {data['content'][:100]}{'...' if len(data['content']) > 100 else ''}</p>"
                
                elif element == 'meta_description' and 'content' in data:
                    html += f"<div class='metric'>Length: {data.get('length', 0)} chars</div>"
                    html += f"<p><strong>Content:</strong> {data['content'][:150]}{'...' if len(data['content']) > 150 else ''}</p>"
                
                elif element == 'headings':
                    total_headings = data.get('total_headings', 0)
                    html += f"<div class='metric'>Total Headings: {total_headings}</div>"
                    h1_count = len(data.get('headings', {}).get('h1', []))
                    html += f"<div class='metric'>H1 Tags: {h1_count}</div>"
                
                elif element == 'images':
                    total_imgs = data.get('total_images', 0)
                    missing_alt = data.get('missing_alt', 0)
                    html += f"<div class='metric'>Total Images: {total_imgs}</div>"
                    html += f"<div class='metric'>Missing Alt: {missing_alt}</div>"
                
                elif element == 'body_content':
                    word_count = data.get('word_count', 0)
                    html += f"<div class='metric'>Word Count: {word_count}</div>"
                
                # Add issues and suggestions
                issues = data.get('issues', [])
                suggestions = data.get('suggestions', [])
                
                if issues:
                    html += "<div class='issues'><strong>Issues:</strong><ul>"
                    for issue in issues:
                        html += f"<li>❌ {issue}</li>"
                    html += "</ul></div>"
                
                if suggestions:
                    html += "<div class='suggestions'><strong>Suggestions:</strong><ul>"
                    for suggestion in suggestions:
                        html += f"<li>💡 {suggestion}</li>"
                    html += "</ul></div>"
                
                html += "</div>"
            
            # Add PageSpeed Insights if available
            if 'page_insights' in page and 'error' not in page['page_insights']:
                insights = page['page_insights']
                html += """
                <div class="element-card">
                    <h4>🚀 PageSpeed Insights</h4>
                """
                
                for device in ['mobile', 'desktop']:
                    if device in insights and 'error' not in insights[device]:
                        data = insights[device]
                        html += f"<h5>{device.title()}:</h5>"
                        for metric, score in data.items():
                            if isinstance(score, (int, float)):
                                indicator, status = self.get_visual_indicator(score)
                                html += f"<div class='metric'>{indicator} {metric.replace('_', ' ').title()}: {score:.0f}/100</div>"
                
                html += "</div>"
            
            html += "</div></div>"
        
        # Common Issues Summary
        if summary.get('common_issues'):
            html += """
            <h2>⚠️ Most Common Issues</h2>
            <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <ul>
            """
            for issue, count in list(summary['common_issues'].items())[:10]:
                html += f"<li><strong>{issue}</strong> - Found on {count} page(s)</li>"
            html += "</ul></div>"
        
        # Add recommended keywords section at bottom
        if recommended_keywords.get('primary_keyword') or recommended_keywords.get('secondary_keywords'):
            html += """
        <div style="background: #e8f5e8; padding: 25px; border-radius: 10px; margin: 30px 0; border-left: 5px solid #28a745;">
            <h2 style="color: #155724; margin-bottom: 20px;">💡 AI Recommended Keywords (Perplexity Analysis)</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
            """
            
            primary_kw = recommended_keywords.get('primary_keyword', {})
            if primary_kw.get('keyword'):
                html += f"""
                <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #c3e6cb;">
                    <h3 style="color: #155724; margin-top: 0;">🎯 Primary Keyword</h3>
                    <div style="font-size: 1.2em; font-weight: bold; color: #333; margin: 10px 0;">{primary_kw['keyword']}</div>
                    <div style="color: #666; margin: 5px 0;">📊 Search Volume: {primary_kw.get('search_volume', 'N/A')}/month</div>
                    <div style="color: #666; margin: 5px 0;">⚡ Difficulty: {primary_kw.get('difficulty', 'N/A')}/100</div>
                    <div style="color: #666; margin: 5px 0;">📈 Current Rank: {primary_kw.get('current_rank', 'Not ranking')}</div>
                </div>
                """
            
            secondary_kws = recommended_keywords.get('secondary_keywords', [])
            if secondary_kws:
                html += """
                <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #c3e6cb;">
                    <h3 style="color: #155724; margin-top: 0;">📋 Secondary Keywords</h3>
                """
                for i, kw in enumerate(secondary_kws[:5], 1):
                    if kw.get('keyword'):
                        html += f"""
                    <div style="margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                        <div style="font-weight: bold; color: #333;">{i}. {kw['keyword']}</div>
                        <div style="font-size: 0.9em; color: #666; margin-top: 5px;">
                            📊 Vol: {kw.get('search_volume', 'N/A')}/mo | ⚡ Diff: {kw.get('difficulty', 'N/A')}/100
                        </div>
                    </div>
                        """
                html += "</div>"
            
            html += "</div></div>"
        
        html += """
        <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666;">
            <p>Generated by Perplexity SEO Analyzer | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    # Google Drive upload methods commented out - not using anymore
    # def upload_to_drive(self, html_file, json_file):
    #     """Upload files to Google Drive using service account"""
    #     try:
    #         # Build the Drive service using service account
    #         service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service-account-key.json')
    #         if not os.path.exists(service_account_file):
    #             print(f"Service account file not found: {service_account_file}")
    #             return
    #         
    #         credentials = service_account.Credentials.from_service_account_file(
    #             service_account_file,
    #             scopes=['https://www.googleapis.com/auth/drive.file']
    #         )
    #         service = build('drive', 'v3', credentials=credentials)
    #         
    #         # Create SEO folder if it doesn't exist
    #         folder_id = self.get_or_create_folder(service, 'SEO')
    #         reports_folder_id = self.get_or_create_folder(service, 'reports', folder_id)
    #         
    #         # Upload HTML file
    #         html_metadata = {
    #             'name': os.path.basename(html_file),
    #             'parents': [reports_folder_id]
    #         }
    #         html_media = MediaFileUpload(html_file, mimetype='text/html')
    #         html_result = service.files().create(body=html_metadata, media_body=html_media).execute()
    #         
    #         # Upload JSON file
    #         json_metadata = {
    #             'name': os.path.basename(json_file),
    #             'parents': [reports_folder_id]
    #         }
    #         json_media = MediaFileUpload(json_file, mimetype='application/json')
    #         json_result = service.files().create(body=json_metadata, media_body=json_media).execute()
    #         
    #         print(f"✅ Files uploaded to Google Drive:")
    #         print(f"  HTML: https://drive.google.com/file/d/{html_result['id']}/view")
    #         print(f"  JSON: https://drive.google.com/file/d/{json_result['id']}/view")
    #         
    #     except Exception as e:
    #         raise Exception(f"Drive upload failed: {e}")
    # 
    # def get_or_create_folder(self, service, folder_name, parent_id=None):
    #     """Get existing folder or create new one"""
    #     query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    #     if parent_id:
    #         query += f" and '{parent_id}' in parents"
    #     
    #     results = service.files().list(q=query).execute()
    #     folders = results.get('files', [])
    #     
    #     if folders:
    #         return folders[0]['id']
    #     
    #     # Create folder
    #     folder_metadata = {
    #         'name': folder_name,
    #         'mimeType': 'application/vnd.google-apps.folder'
    #     }
    #     if parent_id:
    #         folder_metadata['parents'] = [parent_id]
    #     
    #     folder = service.files().create(body=folder_metadata).execute()
    #     return folder['id']

def main():
    """Main function for command-line usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pplx_seo_analyzer.py <website_url> [max_pages]")
        print("Required environment variables: PPLX_API_KEY, GOOGLE_CLOUD_API_KEY")
        sys.exit(1)
    
    url = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Check for required API keys
    pplx_key = os.getenv('PPLX_API_KEY')
    google_key = os.getenv('GOOGLE_CLOUD_API_KEY')
    
    if not pplx_key:
        print("Error: PPLX_API_KEY environment variable not set")
        sys.exit(1)
    
    if not google_key:
        print("Warning: GOOGLE_CLOUD_API_KEY not set. PageSpeed Insights will be skipped.")
    
    try:
        analyzer = PerplexitySEOAnalyzer(pplx_key, google_key)
        report = analyzer.generate_report(url, max_pages)
        
        print("\n" + "="*80)
        print("SEO ANALYSIS COMPLETE")
        print("="*80)
        if not report:
            print("Error: Failed to generate report")
            sys.exit(1)
            
        print(f"Base URL: {report['metadata']['base_url']}")
        print(f"Pages Analyzed: {report['summary']['successful_pages']}/{report['summary']['total_pages']}")
        print(f"Total Issues Found: {report['summary']['total_issues']}")
        print(f"Average Overall Score: {report['summary']['avg_overall_score_score']:.1f}/100")
        
        print("\nAverage Scores:")
        print(f"  Title Tags: {report['summary']['avg_title_score']:.1f}/100")
        print(f"  Meta Descriptions: {report['summary']['avg_meta_description_score']:.1f}/100")
        print(f"  Headings: {report['summary']['avg_headings_score']:.1f}/100")
        print(f"  Images: {report['summary']['avg_images_score']:.1f}/100")
        print(f"  Body Content: {report['summary']['avg_body_content_score']:.1f}/100")
        
        print("\nTop Issues:")
        for issue, count in list(report['summary']['common_issues'].items())[:5]:
            print(f"  - {issue}: {count} pages")
        
        # Save the report to reports folder
        html_file = analyzer.save_report(report, url)
        
        print(f"\n📄 Detailed HTML report generated with visual indicators!")
        print(f"🏢 Business information extracted and included")
        print(f"📁 Reports saved locally to: {html_file}")
        if google_key:
            print(f"🚀 PageSpeed Insights included for top priority page")
        else:
            print(f"⚠️ PageSpeed Insights skipped (no Google Cloud API key)")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()