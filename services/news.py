from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from config import NEWS_FEEDS

logger = logging.getLogger(__name__)

# English-to-Korean translation map for financial terms
EN_KO_TERMS = {
    "stock": "주식", "stocks": "주식", "market": "시장", "markets": "시장",
    "Wall Street": "월스트리트", "rally": "랠리", "crash": "폭락",
    "bull": "강세", "bear": "약세", "recession": "경기침체",
    "inflation": "인플레이션", "Fed": "연준", "Federal Reserve": "연준",
    "interest rate": "금리", "interest rates": "금리",
    "bond": "채권", "bonds": "채권", "yield": "수익률", "yields": "수익률",
    "earnings": "실적", "revenue": "매출", "profit": "이익", "loss": "손실",
    "S&P 500": "S&P 500", "Nasdaq": "나스닥", "Dow": "다우",
    "investor": "투자자", "investors": "투자자",
    "trade": "무역", "tariff": "관세", "tariffs": "관세",
    "oil": "유가", "gold": "금", "Bitcoin": "비트코인",
    "tech": "기술주", "AI": "AI", "chip": "반도체", "chips": "반도체",
    "semiconductor": "반도체", "semiconductors": "반도체",
    "bank": "은행", "banks": "은행", "economy": "경제",
    "rise": "상승", "rises": "상승", "fall": "하락", "falls": "하락",
    "drop": "하락", "drops": "하락", "surge": "급등", "surges": "급등",
    "plunge": "급락", "plunges": "급락", "jump": "급등", "jumps": "급등",
    "gain": "상승", "gains": "상승", "decline": "하락", "declines": "하락",
    "record high": "사상 최고치", "record low": "사상 최저치",
    "China": "중국", "Japan": "일본", "Europe": "유럽", "Korea": "한국",
    "Trump": "트럼프", "Biden": "바이든",
    "Apple": "애플", "Microsoft": "마이크로소프트", "Google": "구글",
    "Amazon": "아마존", "Tesla": "테슬라", "Nvidia": "엔비디아",
    "Meta": "메타", "Netflix": "넷플릭스", "Samsung": "삼성",
    "analyst": "애널리스트", "analysts": "애널리스트",
    "report": "보고서", "quarter": "분기", "quarterly": "분기",
    "annual": "연간", "growth": "성장", "forecast": "전망",
    "price": "가격", "prices": "가격",
    "trading": "거래", "session": "세션",
    "higher": "더 높은", "lower": "더 낮은",
    "billion": "십억", "trillion": "조", "million": "백만",
    "percent": "퍼센트", "index": "지수",
    "crude": "원유", "Treasury": "국채",
    "crypto": "암호화폐", "cryptocurrency": "암호화폐",
    "Ethereum": "이더리움", "dollar": "달러", "yen": "엔",
    "yuan": "위안", "won": "원", "euro": "유로",
}


@dataclass
class NewsItem:
    title: str
    source: str
    url: str
    published: str
    description: str = ""
    is_korean: bool = False


def _translate_text(text: str) -> str:
    """Translate English text to Korean using term replacement."""
    result = text
    sorted_terms = sorted(EN_KO_TERMS.items(), key=lambda x: len(x[0]), reverse=True)
    for en, ko in sorted_terms:
        pattern = re.compile(re.escape(en), re.IGNORECASE)
        result = pattern.sub(ko, result)
    return result


def _clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"&[a-zA-Z]+;", " ", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def _parse_rss(xml_text: str, source: str, is_korean: bool) -> List[NewsItem]:
    """Parse RSS XML and return news items."""
    items = []
    try:
        root = ET.fromstring(xml_text)
        for item_el in root.findall(".//item"):
            title = item_el.findtext("title", "").strip()
            link = item_el.findtext("link", "").strip()
            pub_date = item_el.findtext("pubDate", "").strip()
            desc = item_el.findtext("description", "").strip()

            if not title:
                continue

            desc = _clean_html(desc)
            pub_short = pub_date[:16] if pub_date else ""

            if not is_korean:
                title = "[EN] " + _translate_text(title)
                desc = _translate_text(desc)

            items.append(NewsItem(
                title=title,
                source=source,
                url=link,
                published=pub_short,
                description=desc,
                is_korean=is_korean,
            ))
    except ET.ParseError as e:
        logger.warning(f"Failed to parse RSS from {source}: {e}")
    return items


def fetch_news(max_per_source: int = 10) -> List[NewsItem]:
    """Fetch news from all configured RSS feeds."""
    all_news: List[NewsItem] = []
    korean_sources = {"hankyung", "mk"}

    for source_key, url in NEWS_FEEDS.items():
        try:
            r = httpx.get(
                url, timeout=10, follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (StockMonitor/1.0)"},
            )
            if r.status_code != 200:
                continue

            is_korean = source_key in korean_sources
            source_label = {
                "yahoo": "Yahoo", "yahoo_markets": "Yahoo",
                "hankyung": "한경", "mk": "매경",
            }.get(source_key, source_key)

            items = _parse_rss(r.text, source_label, is_korean)
            all_news.extend(items[:max_per_source])
        except Exception as e:
            logger.warning(f"Failed to fetch news from {source_key}: {e}")

    return all_news


def fetch_company_news(symbol: str, name: str, market: str = "US", max_items: int = 10) -> List[NewsItem]:
    """Fetch news for a specific company."""
    all_news: List[NewsItem] = []

    try:
        if market == "US":
            # Yahoo Finance RSS for US stocks
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
            r = httpx.get(url, timeout=10, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0 (StockMonitor/1.0)"})
            if r.status_code == 200:
                items = _parse_rss(r.text, "Yahoo", is_korean=False)
                all_news.extend(items[:max_items])
        else:
            # Google News RSS for KR stocks
            query = f"{name}+주식"
            url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
            r = httpx.get(url, timeout=10, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0 (StockMonitor/1.0)"})
            if r.status_code == 200:
                items = _parse_rss(r.text, "Google", is_korean=True)
                all_news.extend(items[:max_items])
    except Exception as e:
        logger.warning(f"Failed to fetch company news for {symbol}: {e}")

    return all_news


def fetch_article_content(url: str) -> str:
    """Fetch and extract article content from URL."""
    try:
        r = httpx.get(
            url, timeout=15, follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (StockMonitor/1.0)"},
        )
        if r.status_code != 200:
            return "(기사를 불러올 수 없습니다)"

        html = r.text
        text_parts = []

        # Strategy 1: Extract from <article> tag (most reliable)
        article_match = re.search(r"<article[^>]*>(.*?)</article>", html, re.DOTALL)
        if article_match:
            paras = re.findall(r"<p[^>]*>(.*?)</p>", article_match.group(1), re.DOTALL)
            for p in paras:
                clean = _clean_html(p).strip()
                if len(clean) > 20:
                    text_parts.append(clean)

        # Strategy 2: Look for common article body classes
        if not text_parts:
            for cls in ["article-body", "article_body", "article-content",
                         "newsct_article", "news_end", "view_con"]:
                body_match = re.search(
                    rf'<div[^>]*class="[^"]*{cls}[^"]*"[^>]*>(.*?)</div>',
                    html, re.DOTALL,
                )
                if body_match:
                    paras = re.findall(r"<p[^>]*>(.*?)</p>", body_match.group(1), re.DOTALL)
                    for p in paras:
                        clean = _clean_html(p).strip()
                        if len(clean) > 20:
                            text_parts.append(clean)
                    if text_parts:
                        break

        # Strategy 3: Fallback to all <p> tags with filtering
        if not text_parts:
            paras = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
            for p in paras:
                clean = _clean_html(p).strip()
                # Filter out navigation, ads, etc.
                if len(clean) > 50 and not any(skip in clean.lower() for skip in
                        ["cookie", "javascript", "subscribe", "sign up", "login",
                         "copyright", "privacy policy", "terms of"]):
                    text_parts.append(clean)

        content = "\n\n".join(text_parts[:25])
        if not content:
            return "(기사 본문을 추출할 수 없습니다. 브라우저에서 확인해 주세요.)"

        return content
    except Exception as e:
        logger.warning(f"Failed to fetch article: {e}")
        return f"(기사를 불러올 수 없습니다: {e})"
