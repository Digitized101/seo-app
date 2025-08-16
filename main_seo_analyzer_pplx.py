import requests
import os
from urllib.parse import urlparse
from datetime import datetime

# Import all analyzers
from webcrawler import crawl_website
from website_architecture_analyzer import analyze_website_architecture
from schema_analyzer import analyze_schema_markup
from title_analyzer import analyze_title_seo
from meta_description_analyzer import analyze_meta_description_seo
from headings_analyzer import analyze_headings_seo
from body_content_analyzer import analyze_body_content_seo
from images_analyzer import analyze_images_seo
from keyword_finder import KeywordFinder
from keyword_generator import generate_keywords_from_html
from page_insights import analyze_page_insights

def extract_and_save_keywords(homepage_url: str, use_ai: bool = False, user_brand_name: str = None) -> tuple:
    """Extract keywords from homepage and save to file"""
    try:
        response = requests.get(homepage_url, timeout=15)
        if response.status_code != 200:
            return [], None
        
        if use_ai:
            # Use AI-powered keyword generator
            result = generate_keywords_from_html(response.content, homepage_url)
            keywords = result.get('keywords', [])
            method = result.get('method', 'AI')
            print(f"Using {method} keyword extraction...")
        else:
            # Use frequency-based keyword finder
            finder = KeywordFinder()
            keywords = finder.extract_keywords(response.text)
            method = 'frequency-based'
            print(f"Using {method} keyword extraction...")
        
        # Create filename from URL
        parsed_url = urlparse(homepage_url)
        domain = parsed_url.netloc.replace('www.', '').replace('.', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"keywords_{domain}_{timestamp}.txt"
        
        # Save keywords to file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(script_dir, filename)
        
        # Update brand name if user provided one
        if user_brand_name and user_brand_name.strip():
            keywords[0] = user_brand_name.strip()
            print(f"Updated brand name to: {user_brand_name}")
        
        with open(filepath, 'w') as f:
            f.write(f"Keywords extracted from: {homepage_url}\n")
            f.write(f"Extraction method: {method}\n")
            f.write(f"Extraction date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total keywords found: {len(keywords)}\n")
            f.write("-" * 50 + "\n")
            for i, keyword in enumerate(keywords, 1):
                if i == 1:
                    f.write(f"{keyword} (BRAND NAME)\n")
                elif i == 2:
                    f.write(f"{keyword} (PRIMARY KEYWORD)\n")
                else:
                    f.write(f"{keyword}\n")
        
        return keywords, filepath
        
    except Exception as e:
        print(f"Error extracting keywords: {e}")
        return [], None

def analyze_single_page(url: str, brand_name: str, keyword_list: list, include_insights: bool = False, base_url: str = "") -> dict:
    """Analyze a single page with all SEO analyzers"""
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return {'error': f'Failed to fetch URL (Status: {response.status_code})'}
        
        html = response.text
        
        # Determine if this is homepage
        from webcrawler import normalize_url
        is_homepage = normalize_url(url) == normalize_url(base_url) if base_url else False
        
        # Run all analyzers
        results = {
            'url': url,
            'title': analyze_title_seo(html, brand_name, keyword_list, is_homepage),
            'meta_description': analyze_meta_description_seo(html, keyword_list),
            'headings': analyze_headings_seo(html, keyword_list, brand_name),
            'body_content': analyze_body_content_seo(html, keyword_list, brand_name),
            'images': analyze_images_seo(html, keyword_list, url, brand_name),
            'schema': analyze_schema_markup(html)
        }
        
        # Add page insights if requested
        if include_insights:
            print(f"  Getting PageSpeed Insights for {url}...")
            results['page_insights'] = analyze_page_insights(url)
        
        return results
        
    except Exception as e:
        return {'error': f'Error analyzing {url}: {str(e)}'}

def generate_seo_report(base_url: str, num_pages: int = 5, use_ai_keywords: bool = False, user_brand_name: str = None) -> dict:
    """Generate comprehensive SEO report for a website"""
    
    print("Extracting keywords from homepage...")
    keyword_list, keywords_file = extract_and_save_keywords(base_url, use_ai_keywords, user_brand_name)
    if not keyword_list:
        print("Failed to extract keywords, using fallback...")
        keyword_list = ["SEO", "Website", "Analysis"]  # Fallback keywords
        keywords_file = None
        brand_name = "Brand"
        primary_keyword = "SEO"
        secondary_keywords = ["Website", "Analysis"]
    else:
        # Parse keywords: 1st line = brand name, 2nd line = primary keyword, rest = secondary
        brand_name = keyword_list[0] if len(keyword_list) > 0 else "Brand"
        primary_keyword = keyword_list[1] if len(keyword_list) > 1 else "Keyword"
        secondary_keywords = keyword_list[2:] if len(keyword_list) > 2 else []
        
        print(f"Brand Name: {brand_name}")
        print(f"Primary Keyword: {primary_keyword}")
        print(f"Secondary Keywords: {', '.join(secondary_keywords[:5])}{'...' if len(secondary_keywords) > 5 else ''}")
    
    print("Getting top-level URLs...")
    try:
        pages_data, _ = crawl_website(base_url, num_pages)
        top_urls = [page['url'] for page in pages_data[:num_pages]]
        if not top_urls:
            top_urls = [base_url]  # Fallback to base URL
            pages_data = [{'url': base_url, 'type': 'HOMEPAGE'}]
    except:
        top_urls = [base_url]  # Fallback to base URL
        pages_data = [{'url': base_url, 'type': 'HOMEPAGE'}]
    
    print(f"Found {len(top_urls)} URLs to analyze")
    
    # Website architecture analysis
    print("Analyzing website architecture...")
    architecture_analysis = analyze_website_architecture(base_url, num_pages)
    
    # Analyze each page
    page_analyses = []
    for i, url in enumerate(top_urls, 1):
        print(f"Analyzing page {i}/{len(top_urls)}: {url}")
        # Run page insights only for top 1 page when AI keywords are enabled
        include_insights = use_ai_keywords and i <= 1
        page_analysis = analyze_single_page(url, brand_name, keyword_list, include_insights, base_url)
        page_analyses.append(page_analysis)
    
    # Compile report
    report = {
        'metadata': {
            'base_url': base_url,
            'brand_name': brand_name,
            'primary_keyword': primary_keyword,
            'secondary_keywords': secondary_keywords,
            'pages_analyzed': len(page_analyses),
            'keywords': keyword_list,
            'keywords_file': keywords_file,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'num_pages_requested': num_pages
        },
        'architecture': architecture_analysis,
        'pages': page_analyses,
        'all_pages_data': pages_data,
        'summary': generate_summary(architecture_analysis, page_analyses)
    }
    
    return report

def generate_summary(architecture: dict, pages: list) -> dict:
    """Generate summary statistics from all analyses"""
    summary = {
        'total_issues': 0,
        'total_suggestions': 0,
        'schema_scores': [],
        'common_issues': {},
        'pages_with_errors': 0,
        'all_scores': [],
        'page_insights_summary': {'mobile': [], 'desktop': []}
    }
    
    # Count architecture issues
    summary['total_issues'] += len(architecture.get('issues', []))
    summary['total_suggestions'] += len(architecture.get('suggestions', []))
    
    # Add architecture score
    if 'score' in architecture:
        summary['all_scores'].append(architecture['score'])
    
    # Analyze page-level data
    for page in pages:
        if 'error' in page:
            summary['pages_with_errors'] += 1
            continue
            
        # Count issues and suggestions from each analyzer
        for analyzer_name, analysis in page.items():
            if analyzer_name == 'url':
                continue
                
            if isinstance(analysis, dict):
                issues = analysis.get('issues', [])
                suggestions = analysis.get('suggestions', [])
                
                summary['total_issues'] += len(issues)
                summary['total_suggestions'] += len(suggestions)
                
                # Track all scores
                if 'score' in analysis:
                    summary['all_scores'].append(analysis['score'])
                
                # Track schema scores (legacy)
                if analyzer_name == 'schema' and 'score' in analysis:
                    score = analysis['score']
                    if isinstance(score, (int, float)):
                        if score >= 70:
                            summary['schema_scores'].append('good')
                        elif score >= 40:
                            summary['schema_scores'].append('fair')
                        else:
                            summary['schema_scores'].append('poor')
                    else:
                        summary['schema_scores'].append(score)
                
                # Track common issues
                for issue in issues:
                    if issue not in summary['common_issues']:
                        summary['common_issues'][issue] = 0
                    summary['common_issues'][issue] += 1
                
                # Track page insights data
                if analyzer_name == 'page_insights' and isinstance(analysis, dict):
                    for device in ['mobile', 'desktop']:
                        if device in analysis and analysis[device].get('status') == 'SUCCESS':
                            metrics = analysis[device]['metrics']
                            summary['page_insights_summary'][device].append(metrics['performance_score'])
    
    # Calculate schema score distribution (legacy)
    if summary['schema_scores']:
        schema_counts = {'good': 0, 'fair': 0, 'poor': 0}
        for score in summary['schema_scores']:
            if score in schema_counts:
                schema_counts[score] += 1
        summary['schema_distribution'] = schema_counts
    
    return summary

def print_report(report: dict):
    """Print formatted SEO report"""
    print("\n" + "="*60)
    print("COMPREHENSIVE SEO ANALYSIS REPORT")
    print("="*60)
    
    # Metadata
    meta = report['metadata']
    print(f"\nWebsite: {meta['base_url']}")
    print(f"Brand: {meta['brand_name']}")
    print(f"Pages Analyzed: {meta['pages_analyzed']}")
    print(f"Analysis Date: {meta['analysis_date']}")
    
    # Summary at the top
    print(f"\n{'='*40}")
    print("SUMMARY")
    print("="*40)
    
    summary = report['summary']
    print(f"Total Issues Found: {summary['total_issues']}")
    print(f"Total Suggestions: {summary['total_suggestions']}")
    print(f"Pages with Errors: {summary['pages_with_errors']}")
    
    # Calculate weighted scores with strict homepage requirements
    weighted_score = 0
    total_weight = 0
    score_breakdown = {}
    homepage_failed = False
    
    # Architecture score (10% weight)
    arch = report['architecture']
    if 'score' in arch:
        weighted_score += arch['score'] * 0.1
        total_weight += 0.1
        score_breakdown['Architecture'] = arch['score']
    
    # Page-level scores with weighted importance
    for i, page in enumerate(report['pages']):
        if 'error' not in page:
            # Determine page weight
            if i == 0:  # Homepage
                page_weight = 0.5
            elif i <= 2:  # Next 2 pages
                page_weight = 0.2
            elif i <= 10:  # Next 8 pages
                page_weight = 0.1
            else:
                page_weight = 0.05
            
            # Calculate page score with critical component checks
            page_scores = []
            critical_failed = False
            
            for analyzer_name in ['title', 'meta_description', 'headings', 'body_content', 'images', 'schema']:
                if analyzer_name in page and 'score' in page[analyzer_name]:
                    score = page[analyzer_name]['score']
                    if isinstance(score, (int, float)):
                        page_scores.append(score)
                        if analyzer_name not in score_breakdown:
                            score_breakdown[analyzer_name] = []
                        score_breakdown[analyzer_name].append(score)
                        
                        # Check critical components (Title, Meta Description, H1)
                        if analyzer_name in ['title', 'meta_description', 'headings'] and score < 40:
                            critical_failed = True
            
            # Add page insights scores
            if 'page_insights' in page:
                insights = page['page_insights']
                for device in ['mobile', 'desktop']:
                    if device in insights and insights[device].get('status') == 'SUCCESS':
                        score = insights[device]['metrics']['performance_score']
                        page_scores.append(score)
                        key = f'page_insights_{device}'
                        if key not in score_breakdown:
                            score_breakdown[key] = []
                        score_breakdown[key].append(score)
            
            if page_scores:
                avg_page_score = sum(page_scores) / len(page_scores)
                
                # Apply critical failure penalty
                if critical_failed:
                    avg_page_score = min(avg_page_score, 30)  # Cap at 30 if critical components fail
                
                # Check homepage failure
                if i == 0 and (avg_page_score < 50 or critical_failed):
                    homepage_failed = True
                
                weighted_score += avg_page_score * page_weight
                total_weight += page_weight
    
    # Calculate final score
    if total_weight > 0:
        avg_score = weighted_score / total_weight
        
        # Apply homepage failure penalty
        if homepage_failed:
            avg_score = min(avg_score, 35)  # Cap overall score at 35 if homepage fails
        
        print(f"\nOverall SEO Score: {avg_score:.1f}/100")
        if homepage_failed:
            print(f"⚠️  Homepage critical issues detected - overall score capped")
        
        print(f"\nScore Breakdown:")
        for component, scores in score_breakdown.items():
            if isinstance(scores, list):
                avg_component_score = sum(scores) / len(scores)
                print(f"  {component.replace('_', ' ').title()}: {avg_component_score:.1f}/100")
            else:
                print(f"  {component.replace('_', ' ').title()}: {scores}/100")
    
    if summary.get('schema_distribution'):
        print(f"\nSchema Score Distribution:")
        for score, count in summary['schema_distribution'].items():
            print(f"  {score.title()}: {count} pages")
    
    if summary['common_issues']:
        print(f"\nMost Common Issues:")
        sorted_issues = sorted(summary['common_issues'].items(), key=lambda x: x[1], reverse=True)
        for issue, count in sorted_issues[:5]:
            print(f"  • {issue} ({count} occurrences)")
    
    # Page Insights Summary
    insights_summary = summary.get('page_insights_summary', {})
    if insights_summary['mobile'] or insights_summary['desktop']:
        print(f"\nPageSpeed Insights Summary:")
        for device in ['mobile', 'desktop']:
            scores = insights_summary[device]
            if scores:
                avg_score = sum(scores) / len(scores)
                print(f"  {device.title()} Performance: {avg_score:.1f}/100 (avg of {len(scores)} pages)")
    
    # Keywords section
    if meta.get('primary_keyword'):
        print(f"\nKeywords Used for Analysis:")
        print(f"Primary Keyword: {meta['primary_keyword']}")
        if meta.get('secondary_keywords'):
            print(f"Secondary Keywords: {', '.join(meta['secondary_keywords'][:4])}")
        if len(meta.get('keywords', [])) > 5:
            print(f"Total Keywords Extracted: {len(meta['keywords'])}")
    
    if meta.get('keywords_file'):
        print(f"Keywords File: {os.path.basename(meta['keywords_file'])}")
        

        # Copy text from keyword file as is
        try:
            with open(meta['keywords_file'], 'r') as f:
                print()
                print(f.read())
        except:
            # Fallback to listing keywords if file read fails
            if meta['keywords']:
                print()
                for i, keyword in enumerate(meta['keywords'], 1):
                    if i == 1:
                        print(f"{i}. {keyword} (BRAND NAME)")
                    elif i == 2:
                        print(f"{i}. {keyword} (PRIMARY KEYWORD)")
                    else:
                        print(f"{i}. {keyword}")
    
    # Architecture Analysis
    print(f"\n{'='*40}")
    print("WEBSITE ARCHITECTURE")
    print("="*40)
    
    arch = report['architecture']
    print(f"Pages Crawled: {arch['pages_crawled']}")
    
    # Architecture Score
    if 'score' in arch:
        print(f"\nArchitecture Score: {arch['score']}/100")
        print(f"Status: {arch['status_icon']} {arch['status']}")
    
    print(f"\nCrawlability:")
    crawl = arch['crawlability']
    print(f"  Robots.txt: {crawl['robots_txt']}")
    print(f"  Crawling Allowed: {crawl['crawling_allowed']}")
    print(f"  Status: {crawl['status']}")
    
    print(f"\nIndexability:")
    index = arch['indexability']
    print(f"  Sitemap.xml: {index['sitemap_xml']}")
    print(f"  URLs in Sitemap: {index['urls_in_sitemap']}")
    print(f"  Status: {index['status']}")
    
    if arch['site_structure']:
        print(f"\nSite Structure:")
        struct = arch['site_structure']
        print(f"  Max Depth: {struct['max_depth']}")
        print(f"  Flat Structure: {struct['flat_structure']}")
        print(f"  Depth Distribution: {struct['depth_distribution']}")
    
    print(f"\nURL Analysis:")
    url_analysis = arch['url_analysis']
    print(f"  Total URLs: {url_analysis['total_urls']}")
    print(f"  Broken Links: {url_analysis['broken_links']}")
    print(f"  Redirects: {url_analysis['redirects']}")
    print(f"  Deep Pages (>3 clicks): {url_analysis['deep_pages']}")
    print(f"  Keyword URLs: {url_analysis['keyword_urls']}")
    print(f"  Clean URLs: {url_analysis['clean_urls']}")
    
    # Architecture Issues and Suggestions
    if arch.get('issues'):
        print(f"\nIssues:")
        for issue in arch['issues']:
            print(f"❌ {issue}")
    
    if arch.get('suggestions'):
        print(f"\nSuggestions:")
        for suggestion in arch['suggestions']:
            print(f"• {suggestion}")
    
    # URLs to be analyzed
    print(f"\n{'='*40}")
    print("URLS TO BE ANALYZED")
    print("="*40)
    
    all_pages = report['all_pages_data']
    num_requested = report['metadata']['num_pages_requested']
    
    print(f"{len(all_pages)} total urls found")
    print()
    
    for i, page_data in enumerate(all_pages[:num_requested], 1):
        tag = page_data.get('type', 'Page')
        backlinks = page_data.get('backlinks', 0)
        priority = page_data.get('priority', 0)
        print(f"{i}. [{tag}] {page_data['url']} ({backlinks} internal links, priority: {priority})")
    
    if len(all_pages) > num_requested:
        remaining = len(all_pages) - num_requested
        print(f"\n{remaining} more URLs found but not analyzed for SEO.")
    
    # Page-by-page analysis
    print(f"\n{'='*40}")
    print("PAGE-BY-PAGE ANALYSIS")
    print("="*40)
    
    for i, page in enumerate(report['pages'], 1):
        if 'error' in page:
            print(f"\nPage {i}: ERROR - {page['error']}")
            continue
            
        # Find page data for this URL to get type and backlinks
        page_data = next((p for p in all_pages if p['url'] == page['url']), {})
        page_type = page_data.get('type', 'OTHER')
        backlinks = page_data.get('backlinks', 0)
        
        print(f"\nPage {i}: {page['url']}")
        print(f"Page Type: {page_type} | Internal Links: {backlinks}")
        print("-" * 50)
        
        # Title Analysis
        title = page['title']
        print(f"\n📝 1. Title Tag Analysis:")
        print(f"Title: {title['title']}")
        print(f"Length: {title['length']} characters")
        
        # Title Score
        if 'score' in title:
            print(f"\nTitle Score: {title['score']}/100")
            print(f"Status: {title['status_icon']} {title['status']}")
        
        if title['issues']:
            print("\nIssues:")
            for issue in title['issues']:
                print(f"❌ {issue}")
        if title['suggestions']:
            print("\nSuggestions:")
            for suggestion in title['suggestions']:
                print(f"• {suggestion}")
        
        # Meta Description
        meta_desc = page['meta_description']
        print(f"\n📄 2. Meta Description Analysis:")
        print(f"Length: {meta_desc['length']} characters")
        
        # Meta Description Score
        if 'score' in meta_desc:
            print(f"\nMeta Description Score: {meta_desc['score']}/100")
            print(f"Status: {meta_desc['status_icon']} {meta_desc['status']}")
        
        if meta_desc['issues']:
            print("\nIssues:")
            for issue in meta_desc['issues']:
                print(f"❌ {issue}")
        if meta_desc['suggestions']:
            print("\nSuggestions:")
            for suggestion in meta_desc['suggestions']:
                print(f"• {suggestion}")
        
        # Headings
        headings = page['headings']
        heading_counts = headings['headings_count']
        print(f"\n🏷️ 3. Headings Analysis:")
        print(f"H1:{heading_counts['h1']}")
        print(f"H2:{heading_counts['h2']}")
        print(f"H3:{heading_counts['h3']}")
        
        # Headings Score
        if 'score' in headings:
            print(f"\nHeadings Score: {headings['score']}/100")
            print(f"Status: {headings['status_icon']} {headings['status']}")
        
        if headings['issues']:
            print("\nIssues:")
            for issue in headings['issues'][:3]:  # Show first 3 issues
                print(f"❌ {issue}")
        if headings['suggestions']:
            print("\nSuggestions:")
            for suggestion in headings['suggestions'][:3]:  # Show first 3 suggestions
                print(f"• {suggestion}")
        
        # Body Content
        body = page['body_content']
        print(f"\n📖 4. Body Content Analysis:")
        print(f"{body['word_count']} words, {body['character_count']} characters")
        
        # Body Content Score
        if 'score' in body:
            print(f"\nBody Content Score: {body['score']}/100")
            print(f"Status: {body['status_icon']} {body['status']}")
        
        if body['issues']:
            print("\nIssues:")
            for issue in body['issues'][:3]:  # Show first 3 issues
                print(f"❌ {issue}")
        if body['suggestions']:
            print("\nSuggestions:")
            for suggestion in body['suggestions'][:3]:  # Show first 3 suggestions
                print(f"• {suggestion}")
        
        # Images
        images = page['images']
        print(f"\n🖼️ 5. Images Analysis:")
        print(f"{images['image_count']} total, {images['alt_text_count']} with alt text")
        
        # Images Score
        if 'score' in images:
            print(f"\nImages Score: {images['score']}/100")
            print(f"Status: {images['status_icon']} {images['status']}")
        
        # Show individual images with new format
        if images['images']:
            print(f"\nImages:")
            for image in images['images']:
                print(image)
        
        # Show general issues and suggestions
        if images['issues']:
            print(f"\nGeneral Issues:")
            for issue in images['issues'][:3]:  # Show first 3 issues
                print(f"❌ {issue}")
        if images['suggestions']:
            print(f"\nSuggestions:")
            for suggestion in images['suggestions'][:3]:  # Show first 3 suggestions
                print(f"• {suggestion}")
        
        # Schema
        schema = page['schema']
        print(f"\n🔗 6. Schema Markup Analysis:")
        if 'score' in schema:
            print(f"Schema Score: {schema['score']}/100")
            if 'status_icon' in schema and 'status' in schema:
                print(f"Status: {schema['status_icon']} {schema['status']}")
        if schema.get('schema_types'):
            print(f"Schema Types: {', '.join(schema['schema_types'][:3])}")
        if schema['issues']:
            print("\nIssues:")
            for issue in schema['issues'][:3]:  # Show first 3 issues
                print(f"❌ {issue}")
        if schema['suggestions']:
            print("\nSuggestions:")
            for suggestion in schema['suggestions'][:3]:  # Show first 3 suggestions
                print(f"• {suggestion}")
        
        # Page Insights (if available)
        if 'page_insights' in page:
            insights = page['page_insights']
            print(f"\n⚡ 7. PageSpeed Insights:")
            
            for device in ['mobile', 'desktop']:
                if device in insights:
                    device_data = insights[device]
                    print(f"\n{device.upper()}:")
                    
                    if device_data['status'] == 'SUCCESS':
                        metrics = device_data['metrics']
                        score = metrics['performance_score']
                        
                        if score >= 90:
                            status_icon = '🟢'
                            status = 'GOOD'
                        elif score >= 50:
                            status_icon = '🟡'
                            status = 'NEEDS IMPROVEMENT'
                        else:
                            status_icon = '🔴'
                            status = 'POOR'
                        
                        print(f"Performance Score: {score}/100")
                        print(f"Status: {status_icon} {status}")
                        print(f"LCP: {metrics['lcp']['display_value']}")
                        print(f"FID: {metrics['fid']['display_value']}")
                        print(f"CLS: {metrics['cls']['display_value']}")
                        print(f"FCP: {metrics['fcp']['display_value']}")
                        print(f"TTFB: {metrics['ttfb']['display_value']}")
                    else:
                        print(f"Error: {device_data['message']}")
    


def read_websites_file(filename: str = "input_data/websites.txt") -> list:
    """Read websites from input file"""
    websites = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(',')
                url = parts[0].strip()
                
                # Default values
                num_pages = 5
                use_ai = True  # Default to YES for AI keywords
                
                # Parse num_pages if provided
                if len(parts) > 1 and parts[1].strip():
                    try:
                        num_pages = int(parts[1].strip())
                    except ValueError:
                        pass
                
                # Parse AI flag if provided
                if len(parts) > 2 and parts[2].strip():
                    ai_flag = parts[2].strip().lower()
                    use_ai = ai_flag == 'y'
                
                websites.append({
                    'url': url,
                    'num_pages': num_pages,
                    'use_ai': use_ai
                })
    
    except FileNotFoundError:
        print(f"Error: {filename} not found")
        return []
    
    return websites

if __name__ == "__main__":
    print("COMPREHENSIVE SEO ANALYZER - BATCH MODE")
    print("=" * 40)
    
    websites = read_websites_file("input_data/websites.txt")
    if not websites:
        print("No websites found in websites.txt")
        exit(1)
    
    print(f"Found {len(websites)} websites to analyze")
    
    # Create reports directory
    reports_dir = os.path.join(os.getcwd(), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    for i, site in enumerate(websites, 1):
        print(f"\n{'='*60}")
        print(f"ANALYZING WEBSITE {i}/{len(websites)}: {site['url']}")
        print(f"Pages: {site['num_pages']}, AI Keywords: {'Yes' if site['use_ai'] else 'No'}")
        print("="*60)
        
        try:
            report = generate_seo_report(site['url'], site['num_pages'], site['use_ai'])
            print_report(report)
            
            # Auto-save report
            domain = urlparse(site['url']).netloc.replace('www.', '').replace('.', '_')
            filename = f"seo_report_{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join(reports_dir, filename)
            
            with open(filepath, 'w') as f:
                import sys
                original_stdout = sys.stdout
                sys.stdout = f
                print_report(report)
                sys.stdout = original_stdout
            
            print(f"\nReport saved to: {filepath}")
            
        except Exception as e:
            print(f"Error analyzing {site['url']}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nCompleted analysis of {len(websites)} websites")
    print(f"Reports saved in: {reports_dir}")