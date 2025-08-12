import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Set, List

def normalize_url(url: str) -> str:
    """Normalize URL to handle duplicates like homepage variations"""
    # Remove fragment
    url = url.split('#')[0]
    
    # Parse URL
    parsed = urlparse(url)
    
    # Normalize path
    path = parsed.path.rstrip('/')
    
    # Handle homepage variations
    if path in ['', '/index.html', '/index.htm', '/index.php', '/default.html', '/default.htm']:
        path = ''
    
    # Reconstruct URL
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    
    return normalized

def is_seo_relevant_url(url: str) -> bool:
    """Check if URL is relevant for SEO analysis"""
    url_lower = url.lower()
    
    # Skip file extensions that aren't HTML pages
    skip_extensions = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.css', '.js', '.xml', '.txt', '.zip', '.doc', '.docx', '.xls', '.xlsx', '.mp4', '.mp3', '.avi', '.mov')
    if any(url_lower.endswith(ext) for ext in skip_extensions):
        return False
    
    # Skip common non-SEO paths
    skip_paths = ('/admin', '/wp-admin', '/login', '/register', '/cart', '/checkout', '/account', '/api/', '/ajax', '/feed', '/rss', '/sitemap')
    if any(path in url_lower for path in skip_paths):
        return False
    
    # Skip query parameters that indicate dynamic/session content
    if '?' in url and any(param in url_lower for param in ['session', 'token', 'auth', 'login', 'logout']):
        return False
    
    return True

def get_seo_priority(url: str, base_url: str, backlinks: int = 0) -> int:
    """Return SEO priority score (higher = more important)"""
    url_lower = url.lower()
    base_domain = urlparse(base_url).netloc
    
    # Homepage gets highest priority - use normalized URLs
    url_normalized = normalize_url(url)
    base_normalized = normalize_url(base_url)
    
    # Check if it's homepage
    if url_normalized == base_normalized:
        return 1000 + backlinks
    
    # Top-level important pages
    top_level_keywords = ['about', 'contact', 'testimonial', 'review', 'service', 'product', 'portfolio', 'team', 'career', 'job']
    if any(keyword in url_lower for keyword in top_level_keywords):
        return 900 + backlinks
    
    # Second-level pages (collections, categories)
    second_level_keywords = ['category', 'collection', 'gallery', 'blog', 'news', 'case-stud', 'project']
    if any(keyword in url_lower for keyword in second_level_keywords):
        return 80 + backlinks
    
    # Count URL depth (fewer slashes = higher priority)
    path_depth = len([p for p in urlparse(url).path.split('/') if p])
    base_score = 40
    if path_depth <= 1:
        base_score = 70
    elif path_depth == 2:
        base_score = 60
    elif path_depth == 3:
        base_score = 50
    
    return base_score + backlinks

def classify_page_type(url: str, base_url: str) -> str:
    """Classify page type based on URL"""
    url_lower = url.lower()
    
    # Check if it's homepage using normalized URLs
    if normalize_url(url) == normalize_url(base_url):
        return 'HOMEPAGE'
    elif 'contact' in url_lower:
        return 'CONTACT'
    elif 'about' in url_lower:
        return 'ABOUT'
    elif any(word in url_lower for word in ['testimonial', 'review']):
        return 'TESTIMONIALS'
    elif any(word in url_lower for word in ['service', 'services']):
        return 'SERVICES'
    elif any(word in url_lower for word in ['product', 'products']):
        return 'PRODUCTS'
    elif any(word in url_lower for word in ['portfolio', 'gallery']):
        return 'PORTFOLIO'
    elif any(word in url_lower for word in ['team', 'staff']):
        return 'TEAM'
    elif any(word in url_lower for word in ['career', 'job']):
        return 'CAREERS'
    elif any(word in url_lower for word in ['blog', 'news']):
        return 'BLOG'
    elif any(word in url_lower for word in ['category', 'collection']):
        return 'CATEGORY'
    else:
        return 'OTHER'

def crawl_website(base_url: str, max_pages: int) -> List[dict]:
    """
    Crawl a website and return all found page URLs with metadata
    """
    visited = set()
    to_visit = [base_url.rstrip('/')]
    found_urls = []
    backlink_count = {}  # Track how many pages link to each URL
    backlink_sources = {}  # Track which pages link to each URL
    
    # Get domain to stay within same site
    base_domain = urlparse(base_url).netloc
    
    while to_visit and len(found_urls) < max_pages:
        current_url = to_visit.pop(0)
        
        if current_url in visited:
            continue
            
        try:
            response = requests.get(current_url, timeout=5)
            if response.status_code != 200:
                visited.add(current_url)
                continue
                
            visited.add(current_url)
            found_urls.append(current_url)
            print(f"Crawled {len(found_urls)}/{max_pages} (Queue: {len(to_visit)}): {current_url}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            links_found = 0
            links_added = 0
            
            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(current_url, href)
                links_found += 1
                
                # Only include URLs from same domain
                if urlparse(full_url).netloc == base_domain:
                    # Normalize URL to handle duplicates
                    clean_url = normalize_url(full_url)
                    
                    # Skip if same as current URL
                    if clean_url == current_url:
                        continue
                    
                    # Count backlinks and track sources
                    if clean_url not in backlink_count:
                        backlink_count[clean_url] = 0
                        backlink_sources[clean_url] = []
                    backlink_count[clean_url] += 1
                    backlink_sources[clean_url].append(current_url)
                    
                    # Add to queue if not visited and passes SEO filter
                    if clean_url not in visited and clean_url not in to_visit and is_seo_relevant_url(clean_url):
                        to_visit.append(clean_url)
                        links_added += 1
            
            print(f"  Found {links_found} links, added {links_added} to queue")
                        
        except requests.exceptions.Timeout:
            print(f"Timeout crawling {current_url} - skipping")
            visited.add(current_url)
            continue
        except Exception as e:
            print(f"Error crawling {current_url}: {str(e)[:50]}...")
            visited.add(current_url)
            continue
    
    # Create structured data with metadata for ALL discovered URLs
    all_discovered_urls = set(found_urls + list(backlink_count.keys()))
    url_data = []
    
    for url in all_discovered_urls:
        backlinks = backlink_count.get(url, 0)
        url_data.append({
            'url': url,
            'type': classify_page_type(url, base_url),
            'priority': get_seo_priority(url, base_url, backlinks),
            'backlinks': backlinks,
            'backlink_sources': backlink_sources.get(url, [])
        })
    
    # Sort by SEO priority
    url_data.sort(key=lambda x: x['priority'], reverse=True)
    return url_data, len(visited)

def show_backlinks_for_url(pages_data, target_url):
    """Show which URLs link to a specific target URL"""
    for page in pages_data:
        if page['url'] == target_url:
            print(f"\nBacklinks to {target_url}:")
            for i, source in enumerate(page['backlink_sources'], 1):
                print(f"{i}. {source}")
            return
    print(f"URL {target_url} not found in crawled data")

if __name__ == "__main__":
    test_url = input("Enter URL to crawl: ")
    max_pages = int(input("Enter maximum number of pages to crawl: "))
    pages, visited_count = crawl_website(test_url, max_pages)
    
    print(f"\nCrawling complete! Found {len(pages)} pages (Visited: {visited_count} total):")
    for i, page_data in enumerate(pages, 1):
        print(f"{i}. {page_data['url']} ({page_data['type']}) - {page_data['backlinks']} backlinks")
    
    # Example: Show backlinks for a specific URL
    # show_backlinks_for_url(pages, "https://www.tuflex.co.in/polymer-nets-knitted-fabrics.html")