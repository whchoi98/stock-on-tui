# 뉴스 데이터 서비스 모듈 / News data service module
# RSS 피드를 통해 경제/금융 뉴스를 수집하고, 영어 뉴스의 금융 용어를 한국어로 번역합니다
# Collects economic/financial news via RSS feeds and translates English financial terms to Korean

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from config import NEWS_FEEDS

logger = logging.getLogger(__name__)

# 영어→한국어 금융 용어 번역 매핑 / English-to-Korean translation map for financial terms
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


# 뉴스 항목 데이터 클래스 / News item data class
@dataclass
class NewsItem:
    title: str          # 기사 제목 / Article title
    source: str         # 뉴스 출처 / News source
    url: str            # 기사 URL / Article URL
    published: str      # 발행일시 / Published date/time
    description: str = ""    # 기사 설명/요약 / Article description/summary
    is_korean: bool = False  # 한국어 기사 여부 / Whether article is in Korean


def _translate_text(text: str) -> str:
    # 영어 텍스트의 금융 용어를 한국어로 치환 번역 / Translate English financial terms to Korean using term replacement
    # 긴 용어부터 먼저 치환하여 부분 매칭 방지 / Replaces longer terms first to prevent partial matching
    # 매개변수: text(원본 영어 텍스트) / Parameters: text(original English text)
    """Translate English text to Korean using term replacement."""
    result = text
    # 긴 용어부터 정렬하여 부분 매칭 방지 / Sort by length descending to prevent partial matches
    sorted_terms = sorted(EN_KO_TERMS.items(), key=lambda x: len(x[0]), reverse=True)
    for en, ko in sorted_terms:
        # 대소문자 무시 정규식 매칭 / Case-insensitive regex matching
        pattern = re.compile(re.escape(en), re.IGNORECASE)
        result = pattern.sub(ko, result)
    return result


def _clean_html(text: str) -> str:
    # HTML 태그 및 엔티티 제거 / Remove HTML tags and entities
    # 매개변수: text(HTML 포함 텍스트) / Parameters: text(text containing HTML)
    """Remove HTML tags from text."""
    clean = re.sub(r"<[^>]+>", "", text)       # HTML 태그 제거 / Remove HTML tags
    clean = re.sub(r"&[a-zA-Z]+;", " ", clean) # HTML 엔티티 제거 / Remove HTML entities
    clean = re.sub(r"\s+", " ", clean)          # 연속 공백 정리 / Normalize whitespace
    return clean.strip()


def _parse_rss(xml_text: str, source: str, is_korean: bool) -> List[NewsItem]:
    # RSS XML을 파싱하여 뉴스 항목 리스트 반환 / Parse RSS XML and return news items list
    # 영어 기사의 경우 제목과 설명을 한국어 용어로 번역 / For English articles, translates title and description with Korean terms
    # 매개변수: xml_text(RSS XML), source(출처명), is_korean(한국어 여부) / Parameters: xml_text(RSS XML), source(source name), is_korean(whether Korean)
    """Parse RSS XML and return news items."""
    items = []
    try:
        # XML 파싱하여 item 요소 순회 / Parse XML and iterate over item elements
        root = ET.fromstring(xml_text)
        for item_el in root.findall(".//item"):
            title = item_el.findtext("title", "").strip()
            link = item_el.findtext("link", "").strip()
            pub_date = item_el.findtext("pubDate", "").strip()
            desc = item_el.findtext("description", "").strip()

            if not title:
                continue

            # HTML 태그 제거 및 발행일 축약 / Clean HTML and shorten publish date
            desc = _clean_html(desc)
            pub_short = pub_date[:16] if pub_date else ""

            # 영어 기사: [EN] 접두사 추가 및 금융 용어 번역 / English articles: add [EN] prefix and translate financial terms
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
    # 설정된 모든 RSS 피드에서 뉴스 수집 / Fetch news from all configured RSS feeds
    # 매개변수: max_per_source(출처당 최대 뉴스 수) / Parameters: max_per_source(max news items per source)
    # 반환: NewsItem 리스트 / Returns: list of NewsItem
    """Fetch news from all configured RSS feeds."""
    all_news: List[NewsItem] = []
    # 한국어 뉴스 소스 식별 / Identify Korean news sources
    korean_sources = {"hankyung", "mk"}

    for source_key, url in NEWS_FEEDS.items():
        try:
            # RSS 피드 HTTP 요청 / HTTP request to RSS feed
            r = httpx.get(
                url, timeout=10, follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (StockMonitor/1.0)"},
            )
            if r.status_code != 200:
                continue

            # 한국어 소스 여부 판별 및 출처 라벨 매핑 / Determine Korean source and map source label
            is_korean = source_key in korean_sources
            source_label = {
                "yahoo": "Yahoo", "yahoo_markets": "Yahoo",
                "hankyung": "한경", "mk": "매경",
            }.get(source_key, source_key)

            # RSS 파싱 후 출처당 최대 개수만큼 추가 / Parse RSS and add up to max per source
            items = _parse_rss(r.text, source_label, is_korean)
            all_news.extend(items[:max_per_source])
        except Exception as e:
            logger.warning(f"Failed to fetch news from {source_key}: {e}")

    return all_news


def fetch_company_news(symbol: str, name: str, market: str = "US", max_items: int = 10) -> List[NewsItem]:
    # 특정 종목의 관련 뉴스 조회 / Fetch news for a specific company
    # 미국 주식: Yahoo Finance RSS, 한국 주식: Google News RSS / US stocks: Yahoo Finance RSS, KR stocks: Google News RSS
    # 매개변수: symbol(종목코드), name(종목명), market(시장), max_items(최대 뉴스 수)
    # Parameters: symbol(ticker), name(stock name), market(market), max_items(max news count)
    """Fetch news for a specific company."""
    all_news: List[NewsItem] = []

    try:
        if market == "US":
            # 미국 주식: Yahoo Finance RSS 피드에서 종목 뉴스 조회 / US stocks: fetch stock news from Yahoo Finance RSS feed
            url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
            r = httpx.get(url, timeout=10, follow_redirects=True,
                          headers={"User-Agent": "Mozilla/5.0 (StockMonitor/1.0)"})
            if r.status_code == 200:
                items = _parse_rss(r.text, "Yahoo", is_korean=False)
                all_news.extend(items[:max_items])
        else:
            # 한국 주식: Google News RSS 피드에서 종목명+주식 검색 / KR stocks: search stock name+주식 from Google News RSS feed
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
    # 기사 URL에서 본문 텍스트를 추출 / Fetch and extract article content text from URL
    # 3단계 전략으로 본문 추출: article 태그 > 본문 클래스 > 전체 p 태그 / 3-stage strategy: article tag > body class > all p tags
    # 매개변수: url(기사 URL) / Parameters: url(article URL)
    # 반환: 기사 본문 텍스트 / Returns: article body text
    """Fetch and extract article content from URL."""
    try:
        # 기사 페이지 HTTP 요청 / HTTP request to article page
        r = httpx.get(
            url, timeout=15, follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (StockMonitor/1.0)"},
        )
        if r.status_code != 200:
            return "(기사를 불러올 수 없습니다)"

        html = r.text
        text_parts = []

        # 전략 1: <article> 태그에서 추출 (가장 신뢰할 수 있음) / Strategy 1: Extract from <article> tag (most reliable)
        article_match = re.search(r"<article[^>]*>(.*?)</article>", html, re.DOTALL)
        if article_match:
            paras = re.findall(r"<p[^>]*>(.*?)</p>", article_match.group(1), re.DOTALL)
            for p in paras:
                clean = _clean_html(p).strip()
                if len(clean) > 20:
                    text_parts.append(clean)

        # 전략 2: 일반적인 기사 본문 CSS 클래스에서 추출 / Strategy 2: Extract from common article body CSS classes
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

        # 전략 3: 모든 <p> 태그에서 추출 (네비게이션, 광고 등 필터링) / Strategy 3: Fallback to all <p> tags with filtering (navigation, ads, etc.)
        if not text_parts:
            paras = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
            for p in paras:
                clean = _clean_html(p).strip()
                # 네비게이션, 광고, 약관 등 불필요한 텍스트 필터링 / Filter out navigation, ads, terms, etc.
                if len(clean) > 50 and not any(skip in clean.lower() for skip in
                        ["cookie", "javascript", "subscribe", "sign up", "login",
                         "copyright", "privacy policy", "terms of"]):
                    text_parts.append(clean)

        # 최대 25개 단락을 합쳐 본문 구성 / Combine up to 25 paragraphs into content
        content = "\n\n".join(text_parts[:25])
        if not content:
            return "(기사 본문을 추출할 수 없습니다. 브라우저에서 확인해 주세요.)"

        return content
    except Exception as e:
        logger.warning(f"Failed to fetch article: {e}")
        return f"(기사를 불러올 수 없습니다: {e})"
