import requests
import os
import glob
import re
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
from keyword_perplexity import PerplexityKeywordAnalyzer
# from page_insights import analyze_page_insights

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
        recommended_keywords = {'primary_keyword': {}, 'secondary_keywords': []}
        brand_name = 'Unknown Brand'
        
        lines = content.split('\n')
        in_current_primary = False
        in_current_secondary = False
        in_recommended_primary = False
        in_recommended_secondary = False
        
        for line in lines:
            line = line.strip()
            
            if 'BRAND NAME:' in line:
                brand_name = line.split('BRAND NAME:')[1].strip()
            elif 'Current Primary Keywords:' in line:
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
                if in_current_primary or in_current_secondary:
                    if in_current_secondary and re.match(r'^\d+\s+', line):
                        # Format for secondary: 1    Mosquito Net                   27,000/mo          52/100       Not ranking
                        match = re.match(r'^\d+\s+(.+?)\s+(\d+[,\d]*\/mo)\s+(\d+\/100)\s+(.+)$', line)
                    else:
                        # Format for primary: Wire Mesh                           22,000/mo          58/100       Not ranking
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
            'brand_name': brand_name,
            'current_keywords': current_keywords,
            'recommended_keywords': recommended_keywords,
            'file_path': latest_file
        }
        
    except Exception as e:
        print(f"Error reading keyword file: {e}")
        return None

def extract_keywords_with_perplexity(homepage_url: str) -> dict:
    """Extract keywords using Perplexity AI"""
    try:
        analyzer = PerplexityKeywordAnalyzer()
        result = analyzer.analyze_url(homepage_url)
        
        if not result or 'analysis' not in result:
            return None
        
        analysis = result['analysis']
        
        # Extract brand name
        brand_name = analysis.get('brand_name', 'Unknown Brand')
        
        # Extract current keywords
        current_keywords = result.get('current_keywords_analyzed', {'primary': [], 'secondary': []})
        
        # Extract recommended keywords
        recommended_keywords = {
            'primary_keyword': analysis.get('primary_keyword', {}),
            'secondary_keywords': analysis.get('secondary_keywords', [])
        }
        
        return {
            'brand_name': brand_name,
            'current_keywords': current_keywords,
            'recommended_keywords': recommended_keywords,
            'analysis': analysis
        }
        
    except Exception as e:
        print(f"Error extracting keywords with Perplexity: {e}")
        return None

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
        
        # Add page insights if requested (commented out for now)
        # if include_insights:
        #     print(f"  Getting PageSpeed Insights for {url}...")
        #     results['page_insights'] = analyze_page_insights(url)
        
        return results
        
    except Exception as e:
        return {'error': f'Error analyzing {url}: {str(e)}'}

def generate_seo_report(base_url: str, num_pages: int = 5, use_ai_keywords: bool = False, user_brand_name: str = None) -> dict:
    """Generate comprehensive SEO report for a website"""
    
    # Check for existing keyword file first
    print("Checking for existing keyword analysis file...")
    existing_keywords = load_keywords_from_file(base_url)
    
    if existing_keywords:
        print("Using existing keyword analysis from file")
        brand_name = existing_keywords['brand_name']
        current_keywords = existing_keywords['current_keywords']
        recommended_keywords = existing_keywords['recommended_keywords']
        keywords_file = existing_keywords['file_path']
        
        # Create keyword list for analysis (current primary first, then secondary)
        keyword_list = []
        # Add primary keywords first
        if current_keywords.get('primary'):
            keyword_list.extend([kw['keyword'] if isinstance(kw, dict) else kw for kw in current_keywords['primary']])
        # Then add secondary keywords
        if current_keywords.get('secondary'):
            keyword_list.extend([kw['keyword'] if isinstance(kw, dict) else kw for kw in current_keywords['secondary'][:5]])
        
        # If no current keywords, use recommended as fallback
        if not keyword_list:
            if recommended_keywords.get('primary_keyword', {}).get('keyword'):
                keyword_list.append(recommended_keywords['primary_keyword']['keyword'])
            keyword_list.extend([kw.get('keyword', '') for kw in recommended_keywords.get('secondary_keywords', [])[:4] if kw.get('keyword')])
        
        primary_keyword = keyword_list[0] if keyword_list else "SEO"
        secondary_keywords = keyword_list[1:] if len(keyword_list) > 1 else []
        
        print(f"DEBUG - Full keyword_list: {keyword_list}")
        print(f"DEBUG - Primary keyword: {primary_keyword}")
        print(f"DEBUG - Secondary keywords: {secondary_keywords}")
        
    else:
        # Extract keywords using Perplexity AI
        print("Extracting keywords using Perplexity AI...")
        keyword_data = extract_keywords_with_perplexity(base_url)
        
        if not keyword_data:
            print("Failed to extract keywords, using fallback...")
            brand_name = user_brand_name or "Brand"
            primary_keyword = "SEO"
            secondary_keywords = ["Website", "Analysis"]
            keyword_list = [primary_keyword] + secondary_keywords
            keywords_file = None
        else:
            brand_name = keyword_data['brand_name']
            current_keywords = keyword_data['current_keywords']
            recommended_keywords = keyword_data['recommended_keywords']
            
            # Create keyword list for analysis (current primary first, then secondary)
            keyword_list = []
            # Add primary keywords first
            if current_keywords.get('primary'):
                keyword_list.extend([kw['keyword'] if isinstance(kw, dict) else kw for kw in current_keywords['primary']])
            # Then add secondary keywords
            if current_keywords.get('secondary'):
                keyword_list.extend([kw['keyword'] if isinstance(kw, dict) else kw for kw in current_keywords['secondary'][:5]])
            
            # If no current keywords, use recommended as fallback
            if not keyword_list:
                if recommended_keywords.get('primary_keyword', {}).get('keyword'):
                    keyword_list.append(recommended_keywords['primary_keyword']['keyword'])
                keyword_list.extend([kw.get('keyword', '') for kw in recommended_keywords.get('secondary_keywords', [])[:4] if kw.get('keyword')])
            
            primary_keyword = keyword_list[0] if keyword_list else "SEO"
            secondary_keywords = keyword_list[1:] if len(keyword_list) > 1 else []
            keywords_file = None
            
            print(f"DEBUG - Full keyword_list: {keyword_list}")
            print(f"DEBUG - Primary keyword: {primary_keyword}")
            print(f"DEBUG - Secondary keywords: {secondary_keywords}")
    
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
        # Run page insights only for top 1 page when AI keywords are enabled (commented out for now)
        # include_insights = use_ai_keywords and i <= 1
        include_insights = False
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
        # 'page_insights_summary': {'mobile': [], 'desktop': []}
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
                
                # Track page insights data (commented out for now)
                # if analyzer_name == 'page_insights' and isinstance(analysis, dict):
                #     for device in ['mobile', 'desktop']:
                #         if device in analysis and analysis[device].get('status') == 'SUCCESS':
                #             metrics = analysis[device]['metrics']
                #             summary['page_insights_summary'][device].append(metrics['performance_score'])
    
    # Calculate schema score distribution (legacy)
    if summary['schema_scores']:
        schema_counts = {'good': 0, 'fair': 0, 'poor': 0}
        for score in summary['schema_scores']:
            if score in schema_counts:
                schema_counts[score] += 1
        summary['schema_distribution'] = schema_counts
    
    return summary

def generate_html_report(report: dict) -> str:
    """Generate HTML report with overall score, current keywords, and recommended keywords"""
    meta = report['metadata']
    summary = report['summary']
    pages = report['pages']
    
    # Calculate overall weighted score (same logic as print_report)
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
    for i, page in enumerate(pages):
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
            
            if page_scores:
                avg_page_score = sum(page_scores) / len(page_scores)
                
                # Apply critical failure penalty
                if critical_failed:
                    avg_page_score = min(avg_page_score, 30)  # Cap at 30 if critical components fail
                
                # Cap page score at 50 if any component is below 50
                if any(score < 50 for score in page_scores):
                    avg_page_score = min(avg_page_score, 49)
                
                # Check homepage failure
                if i == 0 and (avg_page_score < 50 or critical_failed):
                    homepage_failed = True
                
                weighted_score += avg_page_score * page_weight
                total_weight += page_weight
    
    # Calculate final score
    if total_weight > 0:
        overall_score = weighted_score / total_weight
        
        # Apply homepage failure penalty
        if homepage_failed:
            overall_score = min(overall_score, 35)  # Cap overall score at 35 if homepage fails
    else:
        overall_score = 0
    
    # Calculate average scores for breakdown
    avg_breakdown = {}
    for component, scores in score_breakdown.items():
        if isinstance(scores, list):
            avg_breakdown[component] = sum(scores) / len(scores)
        else:
            avg_breakdown[component] = scores
    
    # Get keywords data
    existing_keywords = load_keywords_from_file(meta['base_url'])
    current_keywords = existing_keywords.get('current_keywords', {}) if existing_keywords else {}
    recommended_keywords = existing_keywords.get('recommended_keywords', {}) if existing_keywords else {}
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SEO Report - {meta['brand_name']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #eee; }}
        .score-section {{ text-align: center; margin: 30px 0; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white; }}
        .breakdown-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
        .breakdown-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }}
        .breakdown-card.good {{ border-left-color: #28a745; }}
        .breakdown-card.warning {{ border-left-color: #ffc107; }}
        .breakdown-card.error {{ border-left-color: #dc3545; }}
        .breakdown-score {{ font-size: 2em; font-weight: bold; margin: 10px 0; }}
        .breakdown-indicator {{ font-size: 1.5em; margin-right: 10px; }}
        .keywords-section {{ background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .recommended-section {{ background: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .page-section {{ margin: 30px 0; padding: 20px; background: white; border: 1px solid #ddd; border-radius: 8px; page-break-before: always; }}
        .page-header {{ background: #f8f9fa; padding: 15px; margin: -20px -20px 20px -20px; border-radius: 8px 8px 0 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 12px; border: 1px solid #ddd; text-align: left; }}
        th {{ background: #f8f9fa; font-weight: bold; }}
        .analyzer-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin: 15px 0; }}
        .analyzer-card {{ border: 1px solid #ddd; border-radius: 5px; padding: 15px; }}
        .good {{ border-left: 4px solid #28a745; }}
        .warning {{ border-left: 4px solid #ffc107; }}
        .error {{ border-left: 4px solid #dc3545; }}
        .issues {{ color: #dc3545; margin: 10px 0; }}
        .suggestions {{ color: #007bff; margin: 10px 0; }}
        @media print {{ .page-section {{ page-break-before: always; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 SEO Analysis Report</h1>
            <h2>{meta['brand_name']}</h2>
            <p><strong>Website:</strong> {meta['base_url']}</p>
            <p><strong>Analysis Date:</strong> {meta['analysis_date']} | <strong>Pages Analyzed:</strong> {meta['pages_analyzed']}</p>
        </div>
        
        <div class="score-section">
            <h2>🏆 Overall Website SEO Score</h2>
            <div style="font-size: 4em; font-weight: bold; margin: 20px 0;">{overall_score:.1f}/100</div>
            <p>Weighted by page priority: Homepage (50%), Next 2 pages (40%), Remaining (10%)</p>
            {f'<p style="color: #ffeb3b; font-weight: bold;">⚠️ Homepage critical issues detected - overall score capped</p>' if homepage_failed else ''}
        </div>
        
        <div class="breakdown-grid">
    """
    
    # Add breakdown tiles
    breakdown_items = [
        ('Architecture', avg_breakdown.get('Architecture', 0)),
        ('Title Tags', avg_breakdown.get('title', 0)),
        ('Meta Descriptions', avg_breakdown.get('meta_description', 0)),
        ('Headings', avg_breakdown.get('headings', 0)),
        ('Body Content', avg_breakdown.get('body_content', 0)),
        ('Images', avg_breakdown.get('images', 0)),
        ('Schema Markup', avg_breakdown.get('schema', 0))
    ]
    
    for item_name, score in breakdown_items:
        if score > 0:  # Only show if we have data
            if score >= 80:
                indicator = '✅'
                status = 'good'
            elif score >= 60:
                indicator = '⚠️'
                status = 'warning'
            else:
                indicator = '❌'
                status = 'error'
            
            html += f"""
            <div class="breakdown-card {status}">
                <div class="breakdown-indicator">{indicator}</div>
                <div class="breakdown-score">{score:.0f}/100</div>
                <div>{item_name}</div>
            </div>
            """
    
    html += "</div>"

    
    # Current Keywords Section
    if current_keywords.get('primary') or current_keywords.get('secondary'):
        html += """
        <div class="keywords-section">
            <h2>🎯 Current Keywords (What the site is optimizing for now)</h2>
            <table>
                <tr><th>Keyword</th><th>Search Volume</th><th>Difficulty</th><th>SERP Rank</th></tr>
        """
        
        # Primary keywords
        for kw in current_keywords.get('primary', []):
            html += f"<tr style='background: #e8f5e8;'><td><strong>🎯 {kw['keyword']}</strong></td><td>{kw['search_volume']}</td><td>{kw['difficulty']}</td><td>{kw['serp_rank']}</td></tr>"
        
        # Secondary keywords
        for kw in current_keywords.get('secondary', [])[:8]:
            html += f"<tr><td>📋 {kw['keyword']}</td><td>{kw['search_volume']}</td><td>{kw['difficulty']}</td><td>{kw['serp_rank']}</td></tr>"
        
        html += "</table></div>"
    
    # Page Analysis Sections
    for i, page in enumerate(pages, 1):
        if 'error' in page:
            html += f"""
            <div class="page-section">
                <div class="page-header">
                    <h3>❌ Page {i}: Error</h3>
                    <p>{page.get('url', 'Unknown URL')}</p>
                </div>
                <p class="issues">Error: {page['error']}</p>
            </div>
            """
            continue
        
        # Calculate page score
        page_scores = [page[key].get('score', 0) for key in ['title', 'meta_description', 'headings', 'body_content', 'images', 'schema'] if key in page and isinstance(page[key], dict)]
        page_score = sum(page_scores) / len(page_scores) if page_scores else 0
        
        html += f"""
        <div class="page-section">
            <div class="page-header">
                <h3>📄 Page {i}: {page['url']}</h3>
                <p><strong>Overall Page Score:</strong> {page_score:.0f}/100</p>
            </div>
            <div class="analyzer-grid">
        """
        
        # Analyze each element
        elements = [('title', 'Title Tag'), ('meta_description', 'Meta Description'), ('headings', 'Headings'), ('body_content', 'Body Content'), ('images', 'Images'), ('schema', 'Schema Markup')]
        
        for element_key, element_name in elements:
            if element_key not in page or not isinstance(page[element_key], dict):
                continue
            
            data = page[element_key]
            score = data.get('score', 0)
            status_class = 'good' if score >= 80 else ('warning' if score >= 60 else 'error')
            
            html += f"""
            <div class="analyzer-card {status_class}">
                <h4>{element_name} ({score:.0f}/100)</h4>
            """
            
            # Add specific content
            if element_key == 'title' and 'title' in data:
                html += f"<p><strong>Title:</strong> {data['title'][:100]}{'...' if len(data['title']) > 100 else ''}</p>"
                html += f"<p><strong>Length:</strong> {data.get('length', 0)} characters</p>"
            elif element_key == 'meta_description' and 'length' in data:
                html += f"<p><strong>Length:</strong> {data['length']} characters</p>"
            elif element_key == 'headings' and 'headings_count' in data:
                counts = data['headings_count']
                html += f"<p><strong>H1:</strong> {counts.get('h1', 0)}, <strong>H2:</strong> {counts.get('h2', 0)}, <strong>H3:</strong> {counts.get('h3', 0)}</p>"
            elif element_key == 'body_content' and 'word_count' in data:
                html += f"<p><strong>Word Count:</strong> {data['word_count']}</p>"
            elif element_key == 'images' and 'image_count' in data:
                html += f"<p><strong>Images:</strong> {data['image_count']} total, {data.get('alt_text_count', 0)} with alt text</p>"
            
            # Add issues and suggestions
            issues = data.get('issues', [])
            suggestions = data.get('suggestions', [])
            
            if issues:
                html += "<div class='issues'><strong>Issues:</strong><ul>"
                for issue in issues[:3]:
                    html += f"<li>❌ {issue}</li>"
                html += "</ul></div>"
            
            if suggestions:
                html += "<div class='suggestions'><strong>Suggestions:</strong><ul>"
                for suggestion in suggestions[:3]:
                    html += f"<li>💡 {suggestion}</li>"
                html += "</ul></div>"
            
            html += "</div>"
        
        html += "</div></div>"
    
    # Recommended Keywords Section at bottom
    if recommended_keywords.get('primary_keyword') or recommended_keywords.get('secondary_keywords'):
        html += """
        <div class="recommended-section">
            <h2>💡 AI Recommended Keywords (What the site should target)</h2>
        """
        
        primary_kw = recommended_keywords.get('primary_keyword', {})
        if primary_kw.get('keyword'):
            html += f"""
            <h3>🎯 Recommended Primary Keyword</h3>
            <table>
                <tr><th>Keyword</th><th>Search Volume</th><th>Difficulty</th><th>Current Rank</th></tr>
                <tr><td><strong>{primary_kw['keyword']}</strong></td><td>{primary_kw.get('search_volume', 'N/A')}</td><td>{primary_kw.get('difficulty', 'N/A')}</td><td>{primary_kw.get('current_rank', 'Not ranking')}</td></tr>
            </table>
            """
        
        secondary_kws = recommended_keywords.get('secondary_keywords', [])
        if secondary_kws:
            html += """
            <h3>📋 Recommended Secondary Keywords</h3>
            <table>
                <tr><th>Keyword</th><th>Search Volume</th><th>Difficulty</th><th>Current Rank</th></tr>
            """
            for kw in secondary_kws[:10]:
                html += f"<tr><td>{kw.get('keyword', 'N/A')}</td><td>{kw.get('search_volume', 'N/A')}</td><td>{kw.get('difficulty', 'N/A')}</td><td>{kw.get('serp_rank', 'Not ranking')}</td></tr>"
            html += "</table>"
        
        html += "</div>"
    
    html += """
        <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666;">
            <p>Generated by SEO Analyzer | Report Date: {}</p>
        </div>
    </div>
</body>
</html>
    """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    return html

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
            
            # Add page insights scores (commented out for now)
            # if 'page_insights' in page:
            #     insights = page['page_insights']
            #     for device in ['mobile', 'desktop']:
            #         if device in insights and insights[device].get('status') == 'SUCCESS':
            #             score = insights[device]['metrics']['performance_score']
            #             page_scores.append(score)
            #             key = f'page_insights_{device}'
            #             if key not in score_breakdown:
            #                 score_breakdown[key] = []
            #             score_breakdown[key].append(score)
            
            if page_scores:
                avg_page_score = sum(page_scores) / len(page_scores)
                
                # Apply critical failure penalty
                if critical_failed:
                    avg_page_score = min(avg_page_score, 30)  # Cap at 30 if critical components fail
                
                # Cap page score at 50 if any component is below 50
                if any(score < 50 for score in page_scores):
                    avg_page_score = min(avg_page_score, 49)
                
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
    
    # Page Insights Summary (commented out for now)
    # insights_summary = summary.get('page_insights_summary', {})
    # if insights_summary['mobile'] or insights_summary['desktop']:
    #     print(f"\nPageSpeed Insights Summary:")
    #     for device in ['mobile', 'desktop']:
    #         scores = insights_summary[device]
    #         if scores:
    #             avg_score = sum(scores) / len(scores)
    #             print(f"  {device.title()} Performance: {avg_score:.1f}/100 (avg of {len(scores)} pages)")
    
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
        
        # Page Insights (if available) - commented out for now
        # if 'page_insights' in page:
        #     insights = page['page_insights']
        #     print(f"\n⚡ 7. PageSpeed Insights:")
        #     
        #     for device in ['mobile', 'desktop']:
        #         if device in insights:
        #             device_data = insights[device]
        #             print(f"\n{device.upper()}:")
        #             
        #             if device_data['status'] == 'SUCCESS':
        #                 metrics = device_data['metrics']
        #                 score = metrics['performance_score']
        #                 
        #                 if score >= 90:
        #                     status_icon = '🟢'
        #                     status = 'GOOD'
        #                 elif score >= 50:
        #                     status_icon = '🟡'
        #                     status = 'NEEDS IMPROVEMENT'
        #                 else:
        #                     status_icon = '🔴'
        #                     status = 'POOR'
        #                 
        #                 print(f"Performance Score: {score}/100")
        #                 print(f"Status: {status_icon} {status}")
        #                 print(f"LCP: {metrics['lcp']['display_value']}")
        #                 print(f"FID: {metrics['fid']['display_value']}")
        #                 print(f"CLS: {metrics['cls']['display_value']}")
        #                 print(f"FCP: {metrics['fcp']['display_value']}")
        #                 print(f"TTFB: {metrics['ttfb']['display_value']}")
        #             else:
        #                 print(f"Error: {device_data['message']}")
    


def read_websites_file(filename: str = "data/input_data/websites.txt") -> list:
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
                
                # Parse AI flag if provided (page insights disabled for now)
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
    
    websites = read_websites_file("data/input_data/websites.txt")
    if not websites:
        print("No websites found in websites.txt")
        exit(1)
    
    print(f"Found {len(websites)} websites to analyze")
    
    # Create reports directory
    reports_dir = os.path.join(os.getcwd(), 'data', 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    for i, site in enumerate(websites, 1):
        print(f"\n{'='*60}")
        print(f"ANALYZING WEBSITE {i}/{len(websites)}: {site['url']}")
        print(f"Pages: {site['num_pages']}, AI Keywords: {'Yes' if site['use_ai'] else 'No'}")
        print("="*60)
        
        try:
            report = generate_seo_report(site['url'], site['num_pages'], site['use_ai'])
            print_report(report)
            
            # Auto-save HTML report
            domain = urlparse(site['url']).netloc.replace('www.', '').replace('.', '_')
            filename = f"seo_report_{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            filepath = os.path.join(reports_dir, filename)
            
            html_content = generate_html_report(report)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"\nHTML Report saved to: {filepath}")
            
        except Exception as e:
            print(f"Error analyzing {site['url']}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nCompleted analysis of {len(websites)} websites")
    print(f"Reports saved in: {reports_dir}")