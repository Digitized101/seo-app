#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import defaultdict

def test_webcrawler(base_url: str, max_pages: int = 5):
    """Test webcrawler and show URLs discovered with their source pages"""
    
    print(f"Testing URL discovery for: {base_url}")
    print(f"Max pages to crawl: {max_pages}")
    print("=" * 60)
    
    parsed_base = urlparse(base_url)
    domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
    
    visited_urls = set()
    url_sources = defaultdict(list)  # Track which page found each URL
    
    def crawl_page(url, source_page="Initial"):
        if url in visited_urls or len(visited_urls) >= max_pages:
            return []
        
        visited_urls.add(url)
        found_urls = []
        
        try:
            print(f"\nCrawling: {url}")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link['href']
                    absolute_url = urljoin(url, href)
                    parsed_url = urlparse(absolute_url)
                    
                    # Only internal links
                    if parsed_url.netloc == parsed_base.netloc:
                        clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                        if clean_url not in visited_urls:
                            found_urls.append(clean_url)
                            url_sources[clean_url].append(url)
                
                print(f"  Found {len(found_urls)} new URLs")
                return found_urls
            else:
                print(f"  Error: Status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"  Error: {e}")
            return []
    
    # Start crawling
    urls_to_crawl = [base_url]
    
    while urls_to_crawl and len(visited_urls) < max_pages:
        current_url = urls_to_crawl.pop(0)
        new_urls = crawl_page(current_url)
        urls_to_crawl.extend(new_urls)
    
    # Display results
    print("\n" + "=" * 60)
    print("CRAWLING RESULTS")
    print("=" * 60)
    
    print(f"\nTotal URLs discovered: {len(visited_urls)}")
    print(f"Total URLs crawled: {len(visited_urls)}")
    
    print(f"\nURL DISCOVERY MAP:")
    print("-" * 40)
    
    for i, url in enumerate(visited_urls, 1):
        print(f"\n{i}. {url}")
        if url in url_sources and url_sources[url]:
            print(f"   Found on: {url_sources[url][0]}")
            if len(url_sources[url]) > 1:
                print(f"   Also found on {len(url_sources[url])-1} other pages")
        else:
            print(f"   Source: Starting URL")
    
    # Show all discovered URLs with all their sources
    print(f"\n\nDETAILED SOURCE MAPPING:")
    print("-" * 40)
    
    all_discovered = set(visited_urls) | set(url_sources.keys())
    
    for url in sorted(all_discovered):
        print(f"\n• {url}")
        if url == base_url:
            print(f"  └─ Starting URL")
        elif url in url_sources:
            for source in url_sources[url]:
                print(f"  └─ Found on: {source}")
        
        if url not in visited_urls:
            print(f"  └─ Status: Not crawled (limit reached)")

if __name__ == "__main__":
    print("WEBCRAWLER URL DISCOVERY TEST")
    print("=" * 30)
    
    base_url = input("Enter website URL to test: ").strip()
    max_pages = int(input("Enter max pages to crawl (default 5): ") or "5")
    
    try:
        test_webcrawler(base_url, max_pages)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()