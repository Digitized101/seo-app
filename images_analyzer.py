import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

def analyze_images_seo(html: str, keyword_list: list = [], base_url: str = "", brand_name: str = "") -> dict:
    """
    Analyze HTML images for SEO issues with 100-point scoring
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {
        'issues': [],
        'suggestions': [],
        'images': [],
        'image_count': 0,
        'alt_text_count': 0,
        'missing_alt_count': 0,
        'missing_keywords_count': 0,
        'score': 0,
        'status': '',
        'status_icon': ''
    }
    
    score = 0
    
    # Find all images
    images = soup.find_all('img')
    result['image_count'] = len(images)
    
    if not images:
        result['issues'].append('No images found on page')
        result['suggestions'].append('Consider adding relevant images to enhance content and user experience')
        result['score'] = 100  # Perfect score if no images to optimize
        result['status'] = 'GOOD'
        result['status_icon'] = '🟢'
        return result
    

    
    # Alt coverage check (60 points)
    missing_alt = [img for img in images if not img.get('alt')]
    empty_alt = [img for img in images if img.get('alt') == '']
    good_alt = [img for img in images if img.get('alt') and len(img.get('alt').strip()) > 0]
    
    result['alt_text_count'] = len(good_alt)
    result['missing_alt_count'] = len(missing_alt) + len(empty_alt)
    
    # Calculate alt coverage score
    if len(images) > 0:
        alt_coverage = len(good_alt) / len(images)
        if alt_coverage >= 0.9:  # 90% or more have alt text
            score += 60
            result['suggestions'].append('Excellent alt text coverage')
        elif alt_coverage >= 0.7:  # 70-89% have alt text
            score += 45
            result['suggestions'].append('Good alt text coverage, room for improvement')
        elif alt_coverage >= 0.5:  # 50-69% have alt text
            score += 30
            result['issues'].append(f'{len(missing_alt) + len(empty_alt)} images missing proper alt text')
            result['suggestions'].append('Improve alt text coverage for better accessibility')
        else:  # Less than 50% have alt text
            score += 15
            result['issues'].append(f'{len(missing_alt) + len(empty_alt)} images missing proper alt text')
            result['suggestions'].append('Add alt attributes to all images for accessibility and SEO')
    
    if missing_alt:
        result['issues'].append(f'{len(missing_alt)} images missing alt attribute')
        result['suggestions'].append('Add alt attributes to all images for accessibility and SEO')
    
    if empty_alt:
        result['issues'].append(f'{len(empty_alt)} images have empty alt text')
        result['suggestions'].append('Provide descriptive alt text for images (or use alt="" for decorative images)')
    
    # Check for brand name in alt text (should be avoided)
    if brand_name and good_alt:
        images_with_brand = 0
        for img in good_alt:
            alt_text = img.get('alt', '').lower()
            if brand_name.lower() in alt_text:
                images_with_brand += 1
        
        if images_with_brand > 0:
            result['issues'].append(f'{images_with_brand} images have brand name in alt text')
            result['suggestions'].append('Remove brand name from alt text - focus on describing the image content')
    
    # Check for keywords in alt text (use primary keyword, not brand name)
    if keyword_list and len(keyword_list) > 0 and good_alt:
        primary_keyword = keyword_list[0].lower()  # Primary keyword is first in list
        images_with_keywords = 0
        
        for img in good_alt:
            alt_text = img.get('alt', '').lower()
            if primary_keyword in alt_text:
                images_with_keywords += 1
        
        result['missing_keywords_count'] = len(good_alt) - images_with_keywords
        
        if result['missing_keywords_count'] > 0:
            result['issues'].append(f'{result["missing_keywords_count"]} images missing keywords in alt text')
            result['suggestions'].append(f'Include relevant keywords like "{keyword_list[0]}" in alt text where appropriate')
    
    # Check alt text quality
    poor_alt = []
    for img in images:
        alt_text = img.get('alt', '')
        if alt_text:
            # Check for poor alt text patterns
            if (len(alt_text) < 3 or 
                alt_text.lower() in ['image', 'img', 'picture', 'photo'] or
                alt_text.lower().startswith(('image of', 'picture of', 'photo of')) or
                re.match(r'^(img|image|pic|photo)\d*$', alt_text.lower())):
                poor_alt.append(img)
    
    if poor_alt:
        result['issues'].append(f'{len(poor_alt)} images have poor quality alt text')
        result['suggestions'].append('Improve alt text to be more descriptive and specific')
    
    # Check for overly long alt text
    long_alt = [img for img in images if img.get('alt') and len(img.get('alt')) > 125]
    if long_alt:
        result['issues'].append(f'{len(long_alt)} images have alt text longer than 125 characters')
        result['suggestions'].append('Keep alt text concise (under 125 characters)')
    
    # Check for title attributes
    images_with_title = [img for img in images if img.get('title')]
    
    # Check for lazy loading
    lazy_images = [img for img in images if img.get('loading') == 'lazy']
    
    # Check for responsive images
    responsive_images = [img for img in images if img.get('srcset') or img.parent.name == 'picture']
    
    if not lazy_images and len(images) > 3:
        result['suggestions'].append('Consider adding loading="lazy" to images below the fold for better performance')
    
    if not responsive_images:
        result['suggestions'].append('Consider using srcset or picture elements for responsive images')
    
    # Filesize/compression hints check (40 points)
    compression_score = 0
    modern_formats = 0
    old_formats = 0
    
    for img in images:
        src = img.get('src', '')
        if src:
            if any(fmt in src.lower() for fmt in ['.webp', '.avif']):
                modern_formats += 1
            elif any(fmt in src.lower() for fmt in ['.jpg', '.jpeg', '.png', '.gif']):
                old_formats += 1
    
    # Modern format usage (15 points)
    if len(images) > 0:
        modern_ratio = modern_formats / len(images)
        if modern_ratio >= 0.8:
            compression_score += 15
        elif modern_ratio >= 0.5:
            compression_score += 10
        elif modern_ratio > 0:
            compression_score += 5
    
    # Lazy loading (15 points)
    if len(images) > 3:  # Only check if more than 3 images
        lazy_ratio = len(lazy_images) / max(1, len(images) - 3)  # Exclude first 3 images
        if lazy_ratio >= 0.8:
            compression_score += 15
        elif lazy_ratio >= 0.5:
            compression_score += 10
        elif lazy_ratio > 0:
            compression_score += 5
    else:
        compression_score += 15  # Full points if 3 or fewer images
    
    # Responsive images (10 points)
    if len(images) > 0:
        responsive_ratio = len(responsive_images) / len(images)
        if responsive_ratio >= 0.5:
            compression_score += 10
        elif responsive_ratio > 0:
            compression_score += 5
    
    score += compression_score
    
    if modern_formats == 0 and old_formats > 0:
        result['suggestions'].append('Consider using modern image formats (WebP, AVIF) for better compression')
    
    # Check for decorative images
    decorative_images = [img for img in images if img.get('alt') == '' and img.get('role') == 'presentation']
    
    # Check for images without dimensions
    images_without_dimensions = [img for img in images if not (img.get('width') and img.get('height'))]
    if len(images_without_dimensions) == len(images) and len(images) > 1:
        result['suggestions'].append('Consider adding width/height attributes to prevent layout shift')
    
    # Check for figure/figcaption usage
    figures = soup.find_all('figure')
    figures_with_images = [fig for fig in figures if fig.find('img')]
    if not figures_with_images and len(images) > 2:
        result['suggestions'].append('Consider using figure/figcaption elements for better semantic structure')
    
    # Store counts for display
    result['title_count'] = len(images_with_title)
    result['lazy_count'] = len(lazy_images)
    result['responsive_count'] = len(responsive_images)
    result['modern_format_count'] = modern_formats
    result['decorative_count'] = len(decorative_images)
    result['figure_count'] = len(figures_with_images)
    
    # Individual image analysis (analyze all but show only top 5)
    all_image_issues = []
    common_issues_count = {
        'Not responsive': 0,
        'Old image format': 0,
        'Missing dimensions': 0,
        'No alt text': 0,
        'Missing keywords in alt text': 0,
        'Missing lazy loading': 0,
        'Missing title attribute': 0,
        'Not in figure element': 0,
        'Poor quality alt text': 0
    }
    
    # Analyze all images to get complete statistics
    for i, img in enumerate(images, 1):
        src = img.get('src', '')
        if src:
            filename = src.split('/')[-1]
            if not filename or filename == src:
                filename = f'image-{i}'
        else:
            filename = f'image-{i}'
        
        image_issues = []
        has_issues = False
        
        # Check individual image issues
        if not img.get('alt'):
            image_issues.append('No alt text')
            common_issues_count['No alt text'] += 1
            has_issues = True
        elif img.get('alt') == '':
            if img.get('role') != 'presentation':
                image_issues.append('No alt text')
                common_issues_count['No alt text'] += 1
                has_issues = True
        else:
            alt_text = img.get('alt', '')
            if (len(alt_text) < 3 or 
                alt_text.lower() in ['image', 'img', 'picture', 'photo'] or
                alt_text.lower().startswith(('image of', 'picture of', 'photo of')) or
                re.match(r'^(img|image|pic|photo)\d*$', alt_text.lower())):
                image_issues.append('Poor quality alt text')
                common_issues_count['Poor quality alt text'] += 1
                has_issues = True
            
            # Check for brand name in alt text (flag as issue)
            if brand_name and brand_name.lower() in alt_text.lower():
                image_issues.append('Contains brand name in alt text')
                has_issues = True
            
            if keyword_list and len(keyword_list) > 0:
                primary_keyword = keyword_list[0].lower()  # Primary keyword is first in list
                if primary_keyword not in alt_text.lower():
                    image_issues.append('Missing keywords in alt text')
                    common_issues_count['Missing keywords in alt text'] += 1
                    has_issues = True
        
        # Check other attributes
        if not img.get('loading') == 'lazy' and i > 3:
            image_issues.append('Missing lazy loading')
            common_issues_count['Missing lazy loading'] += 1
            has_issues = True
        
        if not img.get('srcset') and img.parent.name != 'picture':
            image_issues.append('Not responsive')
            common_issues_count['Not responsive'] += 1
            has_issues = True
        
        if src:
            if not any(fmt in src.lower() for fmt in ['.webp', '.avif']):
                if any(fmt in src.lower() for fmt in ['.jpg', '.jpeg', '.png', '.gif']):
                    image_issues.append('Old image format')
                    common_issues_count['Old image format'] += 1
                    has_issues = True
        
        if not (img.get('width') and img.get('height')):
            image_issues.append('Missing dimensions')
            common_issues_count['Missing dimensions'] += 1
            has_issues = True
        
        if not img.get('title'):
            image_issues.append('Missing title attribute')
            common_issues_count['Missing title attribute'] += 1
            has_issues = True
        
        if not img.find_parent('figure'):
            image_issues.append('Not in figure element')
            common_issues_count['Not in figure element'] += 1
            has_issues = True
        
        # Store all image data
        all_image_issues.append({
            'filename': filename,
            'issues': image_issues,
            'has_issues': has_issues
        })
    
    # Add most common issues section
    common_issues_found = [(issue, count) for issue, count in common_issues_count.items() if count > 0]
    if common_issues_found:
        # Sort by frequency
        common_issues_found.sort(key=lambda x: x[1], reverse=True)
        result['images'].append('Most common issues found:')
        for issue, count in common_issues_found[:5]:  # Show top 5 most common issues
            result['images'].append(f'• {issue}: {count} images')

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
    
    # Add overall message if no issues found and score is good
    if not result['issues'] and score >= 80:
        result['suggestions'].append('Images look well-optimized')
    
    # Store common issues data for external access
    result['common_issues'] = common_issues_count
    
    return result

if __name__ == "__main__":
    url = input("Enter URL to analyze images: ")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("IMAGES ANALYSIS")
            print("=" * 20)
            
            # Read keywords from test file
            import os
            script_dir = os.path.dirname(os.path.abspath(__file__))
            keywords_file = os.path.join(script_dir, 'test_keywords.txt')
            
            keyword_list = []
            try:
                with open(keywords_file, 'r') as f:
                    keyword_list = [line.strip() for line in f.readlines() if line.strip()]
            except FileNotFoundError:
                pass
            
            analysis = analyze_images_seo(response.text, keyword_list, url)
            
            print(f"\nImage count: {analysis['image_count']} images")
            print(f"Images with alt text: {analysis['alt_text_count']}")
            if analysis.get('title_count', 0) > 0:
                print(f"Images with title attributes: {analysis['title_count']}")
            if analysis.get('lazy_count', 0) > 0:
                print(f"Images with lazy loading: {analysis['lazy_count']}")
            if analysis.get('responsive_count', 0) > 0:
                print(f"Responsive images: {analysis['responsive_count']}")
            if analysis.get('modern_format_count', 0) > 0:
                print(f"Images using modern formats: {analysis['modern_format_count']}")
            if analysis.get('decorative_count', 0) > 0:
                print(f"Decorative images properly marked: {analysis['decorative_count']}")
            if analysis.get('figure_count', 0) > 0:
                print(f"Images using figure/figcaption: {analysis['figure_count']}")
            
            if analysis['issues']:
                print("\nIssues:")
                for issue in analysis['issues']:
                    print(f"• {issue}")
            
            if analysis['suggestions']:
                print("\nSuggestions:")
                for suggestion in analysis['suggestions']:
                    print(f"• {suggestion}")
            
            if analysis['images']:
                print("\nImages:")
                for image in analysis['images']:
                    if image.startswith('...and'):
                        print(image)
                    else:
                        print(f"• {image}")
        else:
            print(f"Error: Could not fetch URL (Status: {response.status_code})")
    
    except Exception as e:
        print(f"Error: {e}")

# For backward compatibility when called without keyword_list
def analyze_images_seo_compat(html: str, base_url: str = "") -> dict:
    return analyze_images_seo(html, [], base_url)