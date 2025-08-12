#!/usr/bin/env python3

import re
from collections import Counter
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os

class KeywordFinder:
    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
            'his', 'her', 'its', 'our', 'their', 'from', 'up', 'about', 'into', 'over', 'after'
        }
    
    def extract_keywords(self, html_content):
        """Extract SEO keywords from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract text from different elements with weights
        keyword_scores = Counter()
        phrase_scores = Counter()
        
        # Title (highest weight)
        title = soup.find('title')
        if title:
            text = title.get_text()
            words = self._clean_text(text)
            phrases = self._extract_phrases(text)
            for word in words:
                keyword_scores[word] += 10
            for phrase in phrases:
                phrase_scores[phrase] += 15
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            text = meta_desc.get('content', '')
            words = self._clean_text(text)
            phrases = self._extract_phrases(text)
            for word in words:
                keyword_scores[word] += 8
            for phrase in phrases:
                phrase_scores[phrase] += 12
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            text = meta_keywords.get('content', '')
            words = self._clean_text(text)
            phrases = self._extract_phrases(text)
            for word in words:
                keyword_scores[word] += 7
            for phrase in phrases:
                phrase_scores[phrase] += 10
        
        # H1 tags
        for h1 in soup.find_all('h1'):
            text = h1.get_text()
            words = self._clean_text(text)
            phrases = self._extract_phrases(text)
            for word in words:
                keyword_scores[word] += 6
            for phrase in phrases:
                phrase_scores[phrase] += 9
        
        # H2 tags
        for h2 in soup.find_all('h2'):
            text = h2.get_text()
            words = self._clean_text(text)
            phrases = self._extract_phrases(text)
            for word in words:
                keyword_scores[word] += 4
            for phrase in phrases:
                phrase_scores[phrase] += 6
        
        # H3 tags
        for h3 in soup.find_all('h3'):
            text = h3.get_text()
            words = self._clean_text(text)
            phrases = self._extract_phrases(text)
            for word in words:
                keyword_scores[word] += 3
            for phrase in phrases:
                phrase_scores[phrase] += 4
        
        # Alt text
        for img in soup.find_all('img'):
            text = img.get('alt', '')
            words = self._clean_text(text)
            phrases = self._extract_phrases(text)
            for word in words:
                keyword_scores[word] += 2
            for phrase in phrases:
                phrase_scores[phrase] += 3
        
        # Body text (lower weight)
        body_text = soup.get_text()
        words = self._clean_text(body_text)
        phrases = self._extract_phrases(body_text)
        for word in words:
            keyword_scores[word] += 1
        for phrase in phrases:
            phrase_scores[phrase] += 1
        
        # Combine single words and phrases with frequency weighting
        all_keywords = []
        
        # Add top phrases first with their scores
        top_phrases = phrase_scores.most_common(30)
        for phrase, score in top_phrases:
            if score > 3:
                all_keywords.append((phrase, score))
        
        # Add single words with their scores
        top_words = keyword_scores.most_common(50)
        for word, score in top_words:
            if score > 2 and word not in ' '.join([kw[0] for kw in all_keywords]):
                all_keywords.append((word, score))
        
        # Sort by frequency score (descending)
        all_keywords.sort(key=lambda x: x[1], reverse=True)
        
        # Return keywords with frequency weights
        return [(keyword, score) for keyword, score in all_keywords[:50]]
    
    def _extract_phrases(self, text):
        """Extract 2-3 word phrases from text"""
        if not text:
            return []
        
        # Clean text but keep structure for phrases
        clean_text = re.sub(r'[^a-zA-Z\s]', ' ', text.lower())
        words = clean_text.split()
        
        phrases = []
        # Extract 2-word phrases
        for i in range(len(words) - 1):
            if (len(words[i]) > 2 and len(words[i+1]) > 2 and 
                words[i] not in self.stop_words and words[i+1] not in self.stop_words):
                phrase = f"{words[i]} {words[i+1]}"
                phrases.append(phrase)
        
        # Extract 3-word phrases
        for i in range(len(words) - 2):
            if (len(words[i]) > 2 and len(words[i+1]) > 2 and len(words[i+2]) > 2 and
                words[i] not in self.stop_words and words[i+1] not in self.stop_words and words[i+2] not in self.stop_words):
                phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                phrases.append(phrase)
        
        return phrases
    
    def _clean_text(self, text):
        """Clean and tokenize text"""
        if not text:
            return []
        
        # Convert to lowercase and remove special characters
        text = re.sub(r'[^a-zA-Z\s]', ' ', text.lower())
        
        # Split into words
        words = text.split()
        
        # Filter out stop words and short words
        filtered_words = [
            word for word in words 
            if len(word) > 2 and word not in self.stop_words
        ]
        
        return filtered_words
    
    def save_keywords_to_file(self, keywords, url):
        """Save frequency-weighted keywords to a file named after the URL"""
        # Create filename from URL
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '').replace('.', '_')
        filename = f"keywords_{domain}.txt"
        
        # Ensure directory exists
        os.makedirs('seo/output', exist_ok=True)
        filepath = f"seo/output/{filename}"
        
        # Write keywords to file with frequency scores
        with open(filepath, 'w') as f:
            f.write(f"Frequency-weighted keywords extracted from: {url}\n")
            f.write(f"Total keywords found: {len(keywords)}\n")
            f.write("-" * 60 + "\n")
            f.write(f"{'Rank':<4} {'Keyword':<30} {'Frequency Score':<15}\n")
            f.write("-" * 60 + "\n")
            for i, (keyword, score) in enumerate(keywords, 1):
                f.write(f"{i:<4} {keyword:<30} {score:<15}\n")
        
        return filepath

def find_keywords_from_html(html_content, url):
    """Main function to extract frequency-weighted keywords from HTML and save to file"""
    finder = KeywordFinder()
    weighted_keywords = finder.extract_keywords(html_content)
    filepath = finder.save_keywords_to_file(weighted_keywords, url)
    
    # Extract just keywords for backward compatibility
    keywords_only = [keyword for keyword, score in weighted_keywords]
    
    return {
        'keywords': keywords_only,
        'weighted_keywords': weighted_keywords,
        'total_count': len(weighted_keywords),
        'file_path': filepath
    }