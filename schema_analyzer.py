import requests
from bs4 import BeautifulSoup
import json
import re

def analyze_schema_markup(html: str) -> dict:
    """
    Analyze HTML schema markup for SEO issues and provide suggestions
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {
        'issues': [],
        'suggestions': [],
        'schema_types': [],
        'score': 0,
        'status': '',
        'status_icon': ''
    }
    
    score_points = 0
    max_points = 8
    
    # Check for JSON-LD schema
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    microdata_elements = soup.find_all(attrs={"itemtype": True})
    rdfa_elements = soup.find_all(attrs={"typeof": True})
    
    # Schema presence check
    if not json_ld_scripts and not microdata_elements and not rdfa_elements:
        result['issues'].append('No schema markup found')
        result['suggestions'].append('Add structured data markup (JSON-LD recommended) for better search visibility')
        return result
    
    score_points += 3  # Basic presence - higher points for having any schema
    
    # Analyze JSON-LD schemas
    valid_schemas = []
    for script in json_ld_scripts:
        try:
            schema_data = json.loads(script.string)
            if isinstance(schema_data, list):
                for item in schema_data:
                    if '@type' in item:
                        valid_schemas.append(item)
            elif '@type' in schema_data:
                valid_schemas.append(schema_data)
            score_points += 1
        except (json.JSONDecodeError, TypeError):
            result['issues'].append('Invalid JSON-LD syntax found')
            result['suggestions'].append('Fix JSON syntax errors in structured data')
    
    # Analyze microdata
    for element in microdata_elements:
        itemtype = element.get('itemtype', '')
        if 'schema.org' in itemtype:
            schema_type = itemtype.split('/')[-1]
            result['schema_types'].append(f'Microdata: {schema_type}')
            score_points += 1
    
    # Check for common schema types
    schema_types_found = []
    for schema in valid_schemas:
        schema_type = schema.get('@type', '')
        if schema_type:
            result['schema_types'].append(f'JSON-LD: {schema_type}')
            schema_types_found.append(schema_type.lower())
    
    # Add microdata types to found list
    for element in microdata_elements:
        itemtype = element.get('itemtype', '')
        if 'schema.org' in itemtype:
            schema_type = itemtype.split('/')[-1].lower()
            schema_types_found.append(schema_type)
    
    # Organization/LocalBusiness schema check
    if any(t in schema_types_found for t in ['organization', 'localbusiness']):
        org_schema = next((s for s in valid_schemas if s.get('@type', '').lower() in ['organization', 'localbusiness']), None)
        if org_schema:
            required_org_fields = ['name', 'url']
            missing_fields = [field for field in required_org_fields if field not in org_schema]
            if missing_fields:
                result['issues'].append(f'Organization schema missing required fields: {", ".join(missing_fields)}')
                result['suggestions'].append('Add missing required fields to Organization schema')
            else:
                result['suggestions'].append('Organization schema has required fields (name, url)')
                score_points += 1
                
            # Check for contact info
            if 'telephone' not in org_schema and 'contactPoint' not in org_schema:
                result['suggestions'].append('Add contact information to Organization schema')
            else:
                result['suggestions'].append('Organization schema includes contact information')
        
    # Product schema check
    if 'product' in schema_types_found:
        product_schema = next((s for s in valid_schemas if s.get('@type', '').lower() == 'product'), None)
        if product_schema:
            required_product_fields = ['name', 'description']
            missing_fields = [field for field in required_product_fields if field not in product_schema]
            if missing_fields:
                result['issues'].append(f'Product schema missing fields: {", ".join(missing_fields)}')
                result['suggestions'].append('Add name and description to Product schema')
            else:
                result['suggestions'].append('Product schema has required fields (name, description)')
                score_points += 1
                
            # Check for price/offers
            if 'offers' not in product_schema and 'price' not in product_schema:
                result['suggestions'].append('Add pricing information to Product schema')
            else:
                result['suggestions'].append('Product schema includes pricing information')
    
    # Article schema check
    if 'article' in schema_types_found:
        article_schema = next((s for s in valid_schemas if s.get('@type', '').lower() == 'article'), None)
        if article_schema:
            required_article_fields = ['headline', 'author', 'datePublished']
            missing_fields = [field for field in required_article_fields if field not in article_schema]
            if missing_fields:
                result['issues'].append(f'Article schema missing fields: {", ".join(missing_fields)}')
                result['suggestions'].append('Add headline, author, and datePublished to Article schema')
            else:
                result['suggestions'].append('Article schema has required fields (headline, author, datePublished)')
                score_points += 1
                
            # Check for image
            if 'image' not in article_schema:
                result['suggestions'].append('Add image to Article schema for rich snippets')
            else:
                result['suggestions'].append('Article schema includes image for rich snippets')
    
    # BreadcrumbList check
    breadcrumb_nav = soup.find('nav', attrs={'aria-label': re.compile(r'breadcrumb', re.I)}) or soup.find(class_=re.compile(r'breadcrumb', re.I))
    if breadcrumb_nav and 'breadcrumblist' not in schema_types_found:
        result['suggestions'].append('Add BreadcrumbList schema to existing breadcrumb navigation')
    elif 'breadcrumblist' in schema_types_found:
        result['suggestions'].append('BreadcrumbList schema is implemented')
        score_points += 1
    
    # FAQ schema check
    faq_elements = soup.find_all(['details', 'div'], class_=re.compile(r'faq|question', re.I))
    if faq_elements and 'faqpage' not in schema_types_found:
        result['suggestions'].append('Add FAQ schema to existing Q&A content')
    elif 'faqpage' in schema_types_found:
        result['suggestions'].append('FAQ schema is implemented')
        score_points += 1
    
    # Review/Rating schema check
    rating_elements = soup.find_all(class_=re.compile(r'rating|star|review', re.I))
    if rating_elements and not any(t in schema_types_found for t in ['review', 'aggregaterating']):
        result['suggestions'].append('Add Review or AggregateRating schema to existing ratings')
    elif any(t in schema_types_found for t in ['review', 'aggregaterating']):
        result['suggestions'].append('Review/Rating schema is implemented')
        score_points += 1
    
    # Check for duplicate schemas
    schema_type_counts = {}
    for schema_type in result['schema_types']:
        clean_type = schema_type.split(': ')[1] if ': ' in schema_type else schema_type
        schema_type_counts[clean_type] = schema_type_counts.get(clean_type, 0) + 1
    
    duplicates = [t for t, count in schema_type_counts.items() if count > 1]
    if duplicates:
        result['issues'].append(f'Duplicate schema types found: {", ".join(duplicates)}')
        result['suggestions'].append('Remove duplicate schema markup to avoid conflicts')
        score_points -= 1
    
    # Check for required properties validation
    for schema in valid_schemas:
        schema_type = schema.get('@type', '').lower()
        
        # URL validation
        for key, value in schema.items():
            if 'url' in key.lower() and isinstance(value, str):
                if not value.startswith(('http://', 'https://')):
                    result['issues'].append(f'Invalid URL in {schema_type} schema: {key}')
                    result['suggestions'].append('Use absolute URLs in schema markup')
        
        # Date validation
        date_fields = ['datePublished', 'dateModified', 'startDate', 'endDate']
        for field in date_fields:
            if field in schema:
                date_value = schema[field]
                if not re.match(r'\d{4}-\d{2}-\d{2}', str(date_value)):
                    result['issues'].append(f'Invalid date format in {field}: {date_value}')
                    result['suggestions'].append('Use ISO 8601 date format (YYYY-MM-DD) in schema')
    
    # Image requirements check
    images_found = False
    for schema in valid_schemas:
        if 'image' in schema:
            if not images_found:
                result['suggestions'].append('Schema markup includes images for rich snippets')
                images_found = True
            score_points += 1
        elif schema.get('@type', '').lower() in ['article', 'product', 'organization']:
            result['suggestions'].append(f'Add image to {schema.get("@type", "")} schema for rich snippets')
    
    # Add points for having any valid schema
    if valid_schemas or microdata_elements:
        score_points += 1
    
    # Calculate final score
    score_percentage = (score_points / max_points) * 100
    result['score'] = int(score_percentage)
    
    if score_percentage >= 70:
        result['status'] = 'GOOD'
        result['status_icon'] = '🟢'
    elif score_percentage >= 40:
        result['status'] = 'FAIR'
        result['status_icon'] = '🟡'
    else:
        result['status'] = 'POOR'
        result['status_icon'] = '🔴'
    
    # Add basic issues if schema exists but is minimal
    if (valid_schemas or microdata_elements) and len(result['schema_types']) <= 1 and len([i for i in result['issues'] if i != 'Okay']) == 0:
        result['issues'].append('Limited schema markup implementation')
    
    # Add positive feedback for having schema
    if valid_schemas or microdata_elements:
        result['suggestions'].append('Schema markup is present on the page')
    
    # Overall suggestions based on score
    if result['status'] == 'GOOD':
        result['suggestions'].append('Schema markup is well-implemented for SEO')
    elif result['status'] == 'FAIR':
        result['suggestions'].append('Schema markup needs improvement - add missing required fields')
    else:
        result['suggestions'].append('Schema markup needs significant improvement or implementation')
    
    return result

if __name__ == "__main__":
    url = input("Enter URL to analyze schema markup: ")
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("SCHEMA MARKUP ANALYSIS")
            print("=" * 30)
            
            analysis = analyze_schema_markup(response.text)
            
            print(f"\nOverall Score: {analysis['score']}/100")
            print(f"Status: {analysis['status_icon']} {analysis['status']}")
            
            if analysis['schema_types']:
                print(f"\nSchema Types Found:")
                for schema_type in analysis['schema_types']:
                    print(f"• {schema_type}")
            
            if analysis['issues']:
                print("\nIssues:")
                for issue in analysis['issues']:
                    print(f"• {issue}")
            
            if analysis['suggestions']:
                print("\nSuggestions:")
                for suggestion in analysis['suggestions']:
                    print(f"• {suggestion}")
        else:
            print(f"Error: Could not fetch URL (Status: {response.status_code})")
    
    except Exception as e:
        print(f"Error: {e}")