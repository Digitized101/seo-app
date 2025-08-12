#!/usr/bin/env python3

import requests
import os
from dotenv import load_dotenv

load_dotenv()

class PageInsightsAnalyzer:
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_CLOUD_API_KEY')
        self.api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    
    def get_page_insights(self, url):
        """Get comprehensive PageSpeed Insights metrics for mobile and desktop"""
        if not self.api_key:
            return {
                'status': 'ERROR',
                'message': 'GOOGLE_CLOUD_API_KEY not found in environment variables'
            }
        
        results = {}
        
        # Get metrics for both mobile and desktop
        for strategy in ['MOBILE', 'DESKTOP']:
            params = {
                'url': url,
                'key': self.api_key,
                'category': ['PERFORMANCE'],
                'strategy': strategy
            }
            
            try:
                response = requests.get(self.api_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    lighthouse = data.get('lighthouseResult', {})
                    audits = lighthouse.get('audits', {})
                    categories = lighthouse.get('categories', {})
                    
                    # Extract all required metrics
                    metrics = {
                        'performance_score': int(categories.get('performance', {}).get('score', 0) * 100),
                        'lcp': self._extract_metric(audits, 'largest-contentful-paint'),
                        'fid': self._extract_metric(audits, 'max-potential-fid'),
                        'inp': self._extract_metric(audits, 'interaction-to-next-paint'),
                        'cls': self._extract_metric(audits, 'cumulative-layout-shift'),
                        'fcp': self._extract_metric(audits, 'first-contentful-paint'),
                        'ttfb': self._extract_metric(audits, 'server-response-time'),
                        'speed_index': self._extract_metric(audits, 'speed-index'),
                        'tbt': self._extract_metric(audits, 'total-blocking-time'),
                        'tti': self._extract_metric(audits, 'interactive'),
                        'server_response_time': self._extract_metric(audits, 'server-response-time')
                    }
                    
                    results[strategy.lower()] = {
                        'status': 'SUCCESS',
                        'metrics': metrics
                    }
                    
                elif response.status_code == 400:
                    results[strategy.lower()] = {
                        'status': 'ERROR',
                        'message': f'Bad request: {response.text[:100]}'
                    }
                elif response.status_code == 403:
                    results[strategy.lower()] = {
                        'status': 'ERROR',
                        'message': 'Invalid API key or quota exceeded'
                    }
                else:
                    results[strategy.lower()] = {
                        'status': 'ERROR',
                        'message': f'HTTP {response.status_code}: {response.text[:100]}'
                    }
                    
            except requests.exceptions.Timeout:
                results[strategy.lower()] = {
                    'status': 'ERROR',
                    'message': 'Request timeout - API took too long to respond'
                }
            except Exception as e:
                results[strategy.lower()] = {
                    'status': 'ERROR',
                    'message': f'Request failed: {str(e)}'
                }
        
        return results
    
    def _extract_metric(self, audits, metric_key):
        """Extract metric value and display value from audit data"""
        audit = audits.get(metric_key, {})
        
        return {
            'score': audit.get('score', 0),
            'numeric_value': audit.get('numericValue', 0),
            'display_value': audit.get('displayValue', 'N/A'),
            'unit': audit.get('numericUnit', ''),
            'title': audit.get('title', metric_key)
        }
    
    def format_insights_summary(self, insights_data):
        """Format insights data for easy reading"""
        if not insights_data or 'mobile' not in insights_data:
            return "PageSpeed Insights data not available"
        
        summary = []
        
        for device, data in insights_data.items():
            if data['status'] == 'SUCCESS':
                metrics = data['metrics']
                summary.append(f"{device.upper()}:")
                summary.append(f"  Performance Score: {metrics['performance_score']}/100")
                summary.append(f"  LCP: {metrics['lcp']['display_value']}")
                summary.append(f"  FID: {metrics['fid']['display_value']}")
                summary.append(f"  CLS: {metrics['cls']['display_value']}")
                summary.append(f"  FCP: {metrics['fcp']['display_value']}")
                summary.append(f"  TTFB: {metrics['ttfb']['display_value']}")
            else:
                summary.append(f"{device.upper()}: {data['message']}")
        
        return "\n".join(summary)

def analyze_page_insights(url):
    """
    Main function to analyze PageSpeed Insights
    Usage: result = analyze_page_insights(url)
    """
    analyzer = PageInsightsAnalyzer()
    return analyzer.get_page_insights(url)

# Example usage
if __name__ == "__main__":
    result = analyze_page_insights("https://example.com")
    
    analyzer = PageInsightsAnalyzer()
    summary = analyzer.format_insights_summary(result)
    print("PageSpeed Insights Analysis:")
    print("=" * 40)
    print(summary)