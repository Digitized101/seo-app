from system import *
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json
import re

# -----------------------------
# Helpers
# -----------------------------

def _clean_brand(text: str) -> str:
    """Normalize brand text: trim, remove pipes/dashes/extra spaces, title-case smartly."""
    if not text:
        return ""
    # Split on common separators and take the most brand-ish chunk (shorter, capitalized)
    parts = re.split(r"\s*[|\-–—·:]\s*", text.strip())
    # Heuristic: pick the shortest, non-empty segment that isn’t generic
    candidates = [p.strip() for p in parts if p.strip()]
    if not candidates:
        candidates = [text.strip()]
    # Prefer things with 1–3 words and some capitalization
    candidates.sort(key=lambda s: (len(s.split()) > 3, len(s)))
    cleaned = candidates[0]
    # Tidy whitespace and title-ish case (but don’t butcher ALLCAPS acronyms)
    cleaned = re.sub(r"\s+", " ", cleaned)
    # If looks like all caps and short, keep; else title-case-ish
    if not (cleaned.isupper() and len(cleaned) <= 6):
        cleaned = " ".join(w if w.isupper() else w[:1].upper() + w[1:] for w in cleaned.split())
    return cleaned

def _domain_to_brand(url: str) -> str:
    """Derive a brand-y name from a domain like 'my-awesome-site.co.uk' -> 'My Awesome Site'."""
    if not url:
        return ""
    host = urlparse(url).hostname or ""
    # Strip common subdomains
    host = re.sub(r"^(www\d?|m|web|app)\.", "", host, flags=re.I)
    # Keep only the registrable part (rough heuristic)
    parts = host.split(".")
    if len(parts) >= 2:
        core = parts[-3] if parts[-2] in {"co", "com", "net", "org"} and len(parts) >= 3 else parts[-2]
    else:
        core = host
    core = re.sub(r"[^a-z0-9\-]+", " ", core, flags=re.I)
    core = re.sub(r"[-_]+", " ", core)
    core = re.sub(r"\s+", " ", core).strip()
    return _clean_brand(core)

def _jsonld_names(soup: BeautifulSoup):
    """Yield names found in JSON-LD Organization/WebSite/Brand blocks."""
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        for obj in (data if isinstance(data, list) else [data]):
            if isinstance(obj, dict):
                t = (obj.get("@type") or obj.get("type") or "")
                if isinstance(t, list):
                    t = " ".join(t).lower()
                else:
                    t = str(t).lower()
                if any(k in t for k in ("organization", "brand", "website")):
                    name = obj.get("name") or obj.get("legalName")
                    if isinstance(name, str) and name.strip():
                        yield ("jsonld", name.strip())

def _logo_alt_candidates(soup: BeautifulSoup):
    """Common logo selectors—alts often contain the brand."""
    # <img alt="Brand" src="...logo...">
    for img in soup.find_all("img", alt=True):
        alt = (img.get("alt") or "").strip()
        src = (img.get("src") or "").lower()
        if alt and ("logo" in src or "logo" in alt.lower()):
            yield ("logo-alt", alt)
    # <a class="logo">Brand</a>
    for a in soup.find_all("a"):
        cls = " ".join(a.get("class", [])).lower()
        if "logo" in cls:
            text = a.get_text(strip=True)
            if text:
                yield ("logo-link", text)

# -----------------------------
# Main detector
# -----------------------------

def detect_brand_name(html: str, url: str = "") -> dict:
    """
    Try to detect the website brand name using HTML cues (preferred) and fall back to URL.
    Returns: {'brand': str, 'source': str, 'confidence': float, 'candidates': [(source, value, score), ...]}
    """
    soup = BeautifulSoup(html or "", "html.parser")
    candidates = []

    # 1) og:site_name (usually very reliable)
    og_site_name = soup.find("meta", attrs={"property": "og:site_name"})
    if og_site_name and og_site_name.get("content"):
        candidates.append(("og:site_name", og_site_name["content"].strip(), 0.95))

    # 2) JSON-LD Organization/Brand/WebSite name
    for src, name in _jsonld_names(soup):
        candidates.append((src, name, 0.9))

    # 3) <meta name="application-name">
    app_name = soup.find("meta", attrs={"name": "application-name"})
    if app_name and app_name.get("content"):
        candidates.append(("application-name", app_name["content"].strip(), 0.85))

    # 4) <title> heuristics (often "Page | Brand" or "Brand - Tagline")
    if soup.title and soup.title.string:
        title_brand = _clean_brand(soup.title.string)
        if title_brand:
            candidates.append(("title", title_brand, 0.75))

    # 5) Homepage H1 (sometimes is just the brand)
    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
    if h1s:
        # Use the shortest H1 (more likely brand than long slogans)
        h1_brand = _clean_brand(sorted(h1s, key=lambda s: (len(s.split()) > 4, len(s)))[0])
        if h1_brand:
            candidates.append(("h1", h1_brand, 0.65))

    # 6) Logo-based alts/links
    for src, text in _logo_alt_candidates(soup):
        candidates.append((src, text, 0.7))

    # 7) Fallback to domain-derived brand
    if url:
        domain_brand = _domain_to_brand(url)
        if domain_brand:
            candidates.append(("domain", domain_brand, 0.55))

    # Normalize candidates (clean + de-dup roughly)
    norm = {}
    for src, val, score in candidates:
        cleaned = _clean_brand(val)
        if not cleaned:
            continue
        # Merge scores if same cleaned value appears from multiple sources
        prev = norm.get(cleaned)
        if prev:
            prev_source, prev_score = prev
            # Combine by taking the higher score and noting multiple sources
            norm[cleaned] = (prev_source + f"+{src}", max(prev_score, score))
        else:
            norm[cleaned] = (src, score)

    if not norm:
        return {"brand": "", "source": "none", "confidence": 0.0, "candidates": []}

    # Pick the best-scoring candidate
    best_brand, (best_source, best_score) = max(norm.items(), key=lambda kv: kv[1][1])

    # Return detailed info
    ranked = sorted(
        [(s, b, sc) for b, (s, sc) in norm.items()],
        key=lambda x: x[2],
        reverse=True
    )

    return {
        "brand": best_brand,
        "source": best_source,
        "confidence": round(best_score, 2),
        "candidates": ranked
    }