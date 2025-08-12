import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def analyze_website_architecture(base_url: str, max_pages: int = 10) -> dict:
    """
    Analyze website architecture for SEO issues with 100-point scoring
    """
    result = {
        'pages_crawled': 0,
        'crawlability': {},
        'indexability': {},
        'site_structure': {},
        'url_analysis': {},
        'issues': [],
        'suggestions': [],
        'score': 0,
        'status': '',
        'status_icon': ''
    }
    
    score = 0
    
    # Parse base URL
    parsed_base = urlparse(base_url)
    domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
    
    # Check robots.txt
    robots_url = urljoin(domain, '/robots.txt')
    robots_found = False
    crawling_allowed = True
    
    try:
        robots_response = requests.get(robots_url, timeout=10)
        if robots_response.status_code == 200:
            robots_found = True
            # Check if crawling is allowed for the base URL
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            crawling_allowed = rp.can_fetch('*', base_url)
    except:
        pass
    
    result['crawlability'] = {
        'robots_txt': 'Found' if robots_found else 'Not Found',
        'crawling_allowed': 'Yes' if crawling_allowed else 'No',
        'status': 'PASS' if robots_found and crawling_allowed else 'FAIL'
    }
    
    # Check sitemap.xml
    sitemap_url = urljoin(domain, '/sitemap.xml')
    sitemap_found = False
    sitemap_urls = 0
    
    try:
        sitemap_response = requests.get(sitemap_url, timeout=10)
        if sitemap_response.status_code == 200:
            sitemap_found = True
            try:
                root = ET.fromstring(sitemap_response.content)
                # Handle different sitemap formats
                if root.tag.endswith('sitemapindex'):
                    # Sitemap index file
                    sitemap_urls = len(root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'))
                else:
                    # Regular sitemap
                    sitemap_urls = len(root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'))
            except:
                sitemap_urls = 0
    except:
        pass
    
    # Sitemap coverage check (25 points)
    sitemap_score = 0
    if sitemap_found:
        if sitemap_urls > 0:
            sitemap_score = 25
            result['suggestions'].append('Sitemap.xml found with URLs')
        else:
            sitemap_score = 10
            result['issues'].append('Sitemap.xml is empty or invalid')
            result['suggestions'].append('Ensure your sitemap contains valid URLs and follows XML sitemap protocol')
    else:
        result['issues'].append('Sitemap.xml not found')
        result['suggestions'].append('Create and submit an XML sitemap to help search engines discover your pages')
    
    score += sitemap_score
    
    result['indexability'] = {
        'sitemap_xml': 'Found' if sitemap_found else 'Not Found',
        'urls_in_sitemap': sitemap_urls,
        'status': 'PASS' if sitemap_found else 'FAIL'
    }
    
    # Thread-safe data structures
    visited_urls = set()
    visited_lock = threading.Lock()
    url_depths = {}
    depths_lock = threading.Lock()
    broken_links = 0
    redirects = 0
    links_lock = threading.Lock()
    
    def crawl_single_page(url, depth):
        nonlocal broken_links, redirects
        
        with visited_lock:
            if url in visited_urls or len(visited_urls) >= max_pages:
                return []
            visited_urls.add(url)
        
        try:
            response = requests.get(url, timeout=10, allow_redirects=True)
            
            # Check for redirects
            if len(response.history) > 0:
                with links_lock:
                    redirects += 1
            
            if response.status_code == 200:
                with depths_lock:
                    url_depths[url] = depth
                    result['pages_crawled'] += 1
                
                # Parse HTML to find internal links
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a', href=True)
                
                new_urls = []
                for link in links:
                    href = link['href']
                    absolute_url = urljoin(url, href)
                    parsed_url = urlparse(absolute_url)
                    
                    # Only follow internal links
                    if parsed_url.netloc == parsed_base.netloc:
                        # Remove fragments and query parameters for structure analysis
                        clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                        with visited_lock:
                            if clean_url not in visited_urls and len(visited_urls) < max_pages:
                                new_urls.append((clean_url, depth + 1))
                
                return new_urls
            else:
                with links_lock:
                    broken_links += 1
                return []
                
        except:
            with links_lock:
                broken_links += 1
            return []
    
    # Crawl website structure using ThreadPoolExecutor
    url_queue = deque([(base_url, 0)])
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        while url_queue and len(visited_urls) < max_pages:
            # Submit up to 2 URLs for parallel processing
            futures = []
            batch_size = min(2, len(url_queue))
            
            for _ in range(batch_size):
                if url_queue and len(visited_urls) < max_pages:
                    current_url, depth = url_queue.popleft()
                    future = executor.submit(crawl_single_page, current_url, depth)
                    futures.append(future)
            
            # Process completed futures and add new URLs to queue
            for future in as_completed(futures):
                new_urls = future.result()
                for new_url, new_depth in new_urls:
                    if len(visited_urls) < max_pages:
                        url_queue.append((new_url, new_depth))
    
    # Internal link depth distribution check (25 points)
    depth_score = 0
    if url_depths:
        max_depth = max(url_depths.values())
        depth_distribution = defaultdict(int)
        for depth in url_depths.values():
            depth_distribution[depth] += 1
        
        # Calculate flat structure percentage
        pages_at_depth_1_or_less = sum(count for depth, count in depth_distribution.items() if depth <= 1)
        flat_structure_percent = (pages_at_depth_1_or_less / len(url_depths)) * 100
        
        # Score based on depth distribution
        if max_depth <= 3:
            depth_score += 15
        elif max_depth <= 4:
            depth_score += 10
        else:
            depth_score += 5
            result['issues'].append(f'Site has deep page structure (max depth: {max_depth} clicks)')
            result['suggestions'].append('Reduce page depth - important pages should be reachable within 3 clicks')
        
        # Score based on flat structure
        if flat_structure_percent >= 80:
            depth_score += 10
        elif flat_structure_percent >= 60:
            depth_score += 7
        else:
            depth_score += 3
            result['issues'].append(f'Site structure is not flat enough ({flat_structure_percent:.1f}% at depth ≤1)')
            result['suggestions'].append('Improve site architecture by moving important pages closer to homepage')
        
        result['site_structure'] = {
            'max_depth': f'{max_depth} clicks',
            'flat_structure': f'{flat_structure_percent:.1f}%',
            'depth_distribution': dict(depth_distribution)
        }
    
    score += depth_score
    
    # URL Analysis
    total_urls = len(visited_urls)
    deep_pages = sum(1 for depth in url_depths.values() if depth > 3)
    
    # Orphan rate check (20 points) - pages with no internal links pointing to them
    orphan_score = 20
    if deep_pages > 0:
        orphan_rate = (deep_pages / total_urls) * 100 if total_urls > 0 else 0
        if orphan_rate <= 10:
            orphan_score = 20
        elif orphan_rate <= 20:
            orphan_score = 15
        elif orphan_rate <= 30:
            orphan_score = 10
        else:
            orphan_score = 5
            result['issues'].append(f'{deep_pages} pages are more than 3 clicks deep')
            result['suggestions'].append('Restructure navigation to make deep pages more accessible')
    
    score += orphan_score
    
    # Analyze URL quality
    keyword_urls = 0
    clean_urls = 0
    
    for url in visited_urls:
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        # Check for clean URLs (no query parameters, descriptive paths)
        if not parsed.query and not path.endswith('.php') and not path.endswith('.asp'):
            clean_urls += 1
        
        # Check for keyword-friendly URLs (contains words, not just numbers/IDs)
        if re.search(r'[a-zA-Z]{3,}', path):
            keyword_urls += 1
    
    # URL hygiene check (15 points)
    url_hygiene_score = 0
    if total_urls > 0:
        clean_url_ratio = clean_urls / total_urls
        keyword_url_ratio = keyword_urls / total_urls
        
        # Clean URLs (7 points)
        if clean_url_ratio >= 0.9:
            url_hygiene_score += 7
        elif clean_url_ratio >= 0.7:
            url_hygiene_score += 5
        else:
            url_hygiene_score += 2
            result['issues'].append(f'Only {clean_urls}/{total_urls} URLs are clean')
            result['suggestions'].append('Remove unnecessary query parameters and use clean URL structure')
        
        # Keyword-friendly URLs (8 points)
        if keyword_url_ratio >= 0.8:
            url_hygiene_score += 8
        elif keyword_url_ratio >= 0.6:
            url_hygiene_score += 5
        else:
            url_hygiene_score += 2
            result['issues'].append(f'Only {keyword_urls}/{total_urls} URLs are keyword-friendly')
            result['suggestions'].append('Use descriptive, keyword-rich URLs instead of generic IDs or numbers')
    
    score += url_hygiene_score
    
    # Backlink profile summary check (15 points) - based on internal linking
    backlink_score = 0
    if broken_links == 0:
        backlink_score += 8
    elif broken_links <= 2:
        backlink_score += 5
    else:
        backlink_score += 2
        result['issues'].append(f'{broken_links} broken internal links found')
        result['suggestions'].append('Fix broken internal links to improve user experience and crawlability')
    
    # Redirect management
    if redirects <= total_urls * 0.1:  # Less than 10% redirects
        backlink_score += 7
    elif redirects <= total_urls * 0.2:  # Less than 20% redirects
        backlink_score += 4
    else:
        backlink_score += 1
        result['issues'].append(f'High number of redirects ({redirects})')
        result['suggestions'].append('Minimize redirects to improve page load speed and crawl efficiency')
    
    score += backlink_score
    
    result['url_analysis'] = {
        'total_urls': total_urls,
        'broken_links': broken_links,
        'redirects': redirects,
        'deep_pages': deep_pages,
        'keyword_urls': keyword_urls,
        'clean_urls': clean_urls
    }
    
    # Generate additional issues and suggestions
    if not robots_found:
        result['issues'].append('Robots.txt file not found')
        result['suggestions'].append('Create a robots.txt file to guide search engine crawlers')
    
    if not crawling_allowed:
        result['issues'].append('Crawling is blocked by robots.txt')
        result['suggestions'].append('Review robots.txt to ensure important pages are crawlable')
    
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
    
    # Add positive feedback if no major issues and good score
    if not result['issues'] and score >= 80:
        result['suggestions'].append('Website architecture looks well-optimized for SEO')
    
    return result

if __name__ == "__main__":
    url = input("Enter website URL to analyze: ")
    max_pages = int(input("Enter max pages to crawl (default 10): ") or "10")
    
    try:
        print("WEBSITE ARCHITECTURE ANALYSIS")
        print("=" * 35)
        print("Crawling website... This may take a moment.")
        
        analysis = analyze_website_architecture(url, max_pages)
        
        print(f"\nPages Crawled: {analysis['pages_crawled']}")
        
        print(f"\nCrawlability:")
        crawl = analysis['crawlability']
        print(f"  Robots.txt: {crawl['robots_txt']}")
        print(f"  Crawling Allowed: {crawl['crawling_allowed']}")
        print(f"  Status: {crawl['status']}")
        
        print(f"\nIndexability:")
        index = analysis['indexability']
        print(f"  Sitemap.xml: {index['sitemap_xml']}")
        print(f"  URLs in Sitemap: {index['urls_in_sitemap']}")
        print(f"  Status: {index['status']}")
        
        if analysis['site_structure']:
            print(f"\nSite Structure:")
            struct = analysis['site_structure']
            print(f"  Max Depth: {struct['max_depth']}")
            print(f"  Flat Structure: {struct['flat_structure']}")
            print(f"  Depth Distribution: {struct['depth_distribution']}")
        
        print(f"\nURL Analysis:")
        url_analysis = analysis['url_analysis']
        print(f"  Total URLs: {url_analysis['total_urls']}")
        print(f"  Broken Links: {url_analysis['broken_links']}")
        print(f"  Redirects: {url_analysis['redirects']}")
        print(f"  Deep Pages (>3 clicks): {url_analysis['deep_pages']}")
        print(f"  Keyword URLs: {url_analysis['keyword_urls']}")
        print(f"  Clean URLs: {url_analysis['clean_urls']}")
        
        if analysis['issues']:
            print("\nIssues:")
            for issue in analysis['issues']:
                print(f"• {issue}")
        
        if analysis['suggestions']:
            print("\nSuggestions:")
            for suggestion in analysis['suggestions']:
                print(f"• {suggestion}")
                
    except Exception as e:
        print(f"Error: {e}")