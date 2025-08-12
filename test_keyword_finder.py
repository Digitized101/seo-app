#!/usr/bin/env python3

import requests
from keyword_finder import find_keywords_from_html

def test_keyword_comparison():
    """Test and compare keyword_finder and keyword_generator"""
    
    while True:
        url = input("\nEnter URL to compare keyword extraction (or 'quit' to exit): ").strip()
        
        if url.lower() == 'quit':
            break
        
        if not url:
            continue
        
        # Add http:// if not present
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        print(f"\nFetching content from: {url}")
        
        try:
            # Fetch HTML content
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code}")
                continue
            
            print("\n" + "="*80)
            print("KEYWORD EXTRACTION COMPARISON")
            print("="*80)
            
            # Test keyword_finder
            print("\n[1] KEYWORD_FINDER RESULTS (Frequency-weighted):")
            print("-" * 50)
            
            finder_result = find_keywords_from_html(response.content, url)
            print(f"Total keywords: {finder_result['total_count']}")
            print(f"File saved: {finder_result['file_path']}")
            print("\nTop 20 keywords with frequency scores:")
            
            for i, (keyword, score) in enumerate(finder_result['weighted_keywords'][:20], 1):
                print(f"{i:2d}. {keyword:<25} (score: {score})")
            
            # Test keyword_generator if it exists
            print("\n[2] KEYWORD_GENERATOR RESULTS (AI-generated):")
            print("-" * 50)
            
            try:
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from keyword_generator import generate_keywords_from_html
                
                generator_result = generate_keywords_from_html(response.content, url)
                
                print(f"Total keywords: {len(generator_result.get('keywords', []))}")
                print("\nAI-generated keywords:")
                
                for i, keyword in enumerate(generator_result.get('keywords', [])[:20], 1):
                    print(f"{i:2d}. {keyword}")
                    
            except ImportError as ie:
                print(f"Import error: {ie} - install with: pip install openai")
            except Exception as e:
                print(f"Error with keyword_generator: {e}")
            
            print("\n" + "="*80)
            
        except requests.RequestException as e:
            print(f"Error fetching URL: {e}")
        except Exception as e:
            print(f"Error processing keywords: {e}")

if __name__ == "__main__":
    print("Keyword Extraction Comparison Tool")
    print("-" * 40)
    test_keyword_comparison()