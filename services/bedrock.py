# AWS Bedrock AI 서비스 모듈 / AWS Bedrock AI service module
# Claude 모델을 사용하여 뉴스 기사 분석 및 종목 분석 기능을 제공합니다
# Provides news article analysis and stock analysis using Claude model via AWS Bedrock

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError

logger = logging.getLogger(__name__)

# Bedrock API Key 및 리전 설정 / Bedrock API Key and region config
BEDROCK_API_KEY = os.environ.get("BEDROCK_API_KEY", "")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")

# Bedrock 사용 가능 여부 캐시 (None이면 아직 확인 안 함) / Bedrock availability cache (None = not yet checked)
_bedrock_available: Optional[bool] = None
# Bedrock 비활성화 시 사용자에게 보여줄 안내 메시지 / Disabled message shown to user when Bedrock is unavailable
_DISABLED_MSG = (
    "⚠ Bedrock API Key가 설정되지 않아 AI 기능을 사용할 수 없습니다.\n"
    "  - 뉴스 기사 AI 분석 / 영한 번역\n"
    "  - AI 종목 분석\n"
    "설정 방법: install.sh 재실행 또는 .env에 BEDROCK_API_KEY 추가"
)


def is_bedrock_available() -> bool:
    # Bedrock API Key 또는 AWS 자격 증명이 설정되어 있는지 확인 / Check if Bedrock API Key or AWS credentials are configured
    """Check if Bedrock API Key or AWS credentials are configured."""
    global _bedrock_available
    if _bedrock_available is not None:
        return _bedrock_available
    # 1) BEDROCK_API_KEY 환경변수 확인 / Check BEDROCK_API_KEY env var
    if BEDROCK_API_KEY:
        _bedrock_available = True
        return True
    # 2) AWS IAM Role / aws configure 자격 증명 확인 / Check AWS IAM Role / aws configure credentials
    try:
        session = boto3.Session()
        creds = session.get_credentials()
        if creds:
            creds = creds.get_frozen_credentials()
            _bedrock_available = bool(creds.access_key and creds.secret_key)
        else:
            _bedrock_available = False
    except Exception:
        _bedrock_available = False
    return _bedrock_available


def _get_client():
    # Bedrock 런타임 클라이언트 생성 / Create Bedrock runtime client
    if not is_bedrock_available():
        raise RuntimeError(_DISABLED_MSG)
    # API Key가 있으면 해당 키로 클라이언트 생성 / Create client with API key if available
    if BEDROCK_API_KEY:
        return boto3.client(
            "bedrock-runtime",
            region_name=BEDROCK_REGION,
            aws_access_key_id=BEDROCK_API_KEY,
            aws_secret_access_key=BEDROCK_API_KEY,
        )
    # IAM Role / aws configure 자격 증명 사용 / Use IAM Role / aws configure credentials
    return boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def analyze_article(title: str, content: str, is_korean: bool) -> str:
    # 뉴스 기사를 AI로 분석하는 함수 / Analyze a news article using AI
    # 매개변수: title(기사 제목), content(기사 본문), is_korean(한국어 기사 여부)
    # Parameters: title(article title), content(article body), is_korean(whether article is in Korean)
    # 한국어 기사: 요약, 분석, 인사이트 제공 / Korean articles: summarize, analyze, provide insights
    # 영어 기사: 한국어 번역 후 요약/분석/인사이트 제공 / English articles: translate to Korean, then summarize/analyze/provide insights
    """Use Claude Sonnet 4.6 via Bedrock to analyze a news article.

    For Korean articles: summarize, analyze, provide insights.
    For English articles: translate to Korean first, then summarize/analyze/provide insights.
    """
    try:
        # Bedrock 클라이언트 가져오기 / Get Bedrock client
        client = _get_client()

        # 한국어/영어에 따라 다른 프롬프트 구성 / Build different prompts depending on Korean/English
        if is_korean:
            # 한국어 기사용 프롬프트: 요약, 분석, 투자 인사이트, 관련 종목 / Korean article prompt: summary, analysis, investment insights, related stocks
            prompt = f"""다음 경제/금융 뉴스 기사를 분석해 주세요.

제목: {title}

본문:
{content[:6000]}

다음 형식으로 한국어로 작성해 주세요:

## 요약
(기사의 핵심 내용을 3-5문장으로 요약)

## 분석
(이 뉴스가 시장에 미치는 영향, 관련 산업/기업에 대한 분석)

## 투자 인사이트
(투자자 관점에서의 시사점, 주목할 포인트)

## 관련 종목
(이 뉴스와 관련된 주요 종목들)"""
        else:
            # 영어 기사용 프롬프트: 번역 + 요약 + 분석 + 투자 인사이트 + 관련 종목 / English article prompt: translation + summary + analysis + investment insights + related stocks
            prompt = f"""다음 영문 경제/금융 뉴스 기사를 한국어로 번역하고 분석해 주세요.

Title: {title}

Content:
{content[:6000]}

다음 형식으로 한국어로 작성해 주세요:

## 한국어 번역
(기사 핵심 내용의 한국어 번역, 3-5문장)

## 요약
(기사의 핵심 내용을 3-5문장으로 요약)

## 분석
(이 뉴스가 글로벌 시장 및 한국 시장에 미치는 영향 분석)

## 투자 인사이트
(투자자 관점에서의 시사점, 주목할 포인트)

## 관련 종목
(이 뉴스와 관련된 주요 종목들 - 미국/한국)"""

        # Bedrock API 요청 본문 구성 / Build Bedrock API request body
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        })

        # Bedrock API 호출하여 모델 응답 받기 / Invoke Bedrock API to get model response
        response = client.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )

        # API 응답 본문에서 텍스트 추출 / Extract text from API response body
        result = json.loads(response["body"].read())
        text = result["content"][0]["text"]
        return text

    except Exception as e:
        # API 오류 로깅 및 사용자 친화적 오류 메시지 반환 / Log API error and return user-friendly error message
        logger.error(f"Bedrock API error: {e}")
        return f"(AI 분석을 불러올 수 없습니다: {e})"


def analyze_stock(
    symbol: str,
    name: str,
    price: float,
    change_pct: float,
    pe_ratio: Optional[float] = None,
    week52_high: float = 0,
    week52_low: float = 0,
    sector: str = "",
    market: str = "US",
    news_titles: Optional[list] = None,
) -> str:
    # AI를 사용하여 종목을 분석하고 인사이트 제공 / Analyze a stock and provide insights using AI
    # 매개변수: symbol(종목코드), name(종목명), price(현재가), change_pct(등락률),
    #          pe_ratio(PER), week52_high/low(52주 고가/저가), sector(섹터), market(시장), news_titles(최근 뉴스 제목들)
    # Parameters: symbol(ticker), name(stock name), price(current price), change_pct(change percentage),
    #            pe_ratio(P/E ratio), week52_high/low(52-week high/low), sector(sector), market(market), news_titles(recent news titles)
    """Use Claude via Bedrock to analyze a stock and provide insights."""
    try:
        # Bedrock 클라이언트 가져오기 / Get Bedrock client
        client = _get_client()

        # 최근 뉴스 제목을 문자열로 변환 (최대 5개) / Convert recent news titles to string (max 5)
        news_str = ""
        if news_titles:
            news_str = "\n".join(f"- {t}" for t in news_titles[:5])

        # PER 값을 문자열로 변환 (없으면 N/A) / Convert PE ratio to string (N/A if not available)
        per_str = f"{pe_ratio:.2f}" if pe_ratio else "N/A"
        # 현재 가격의 52주 범위 내 위치를 백분율로 계산 / Calculate current price position within 52-week range as percentage
        w52_pct = ((price - week52_low) / (week52_high - week52_low) * 100) if week52_high > week52_low else 0

        # 종목 분석 프롬프트 구성: 기술적 분석, 투자 포인트, 리스크 요인 / Build stock analysis prompt: technical analysis, investment points, risk factors
        prompt = f"""다음 종목을 간결하게 분석해 주세요. 각 항목을 2-3문장으로 작성하세요.

종목: {symbol} ({name})
시장: {"미국" if market == "US" else "한국"}
섹터: {sector or "N/A"}
현재가: {price:,.2f} ({change_pct:+.2f}%)
PER: {per_str}
52주 범위: {week52_low:,.2f} ~ {week52_high:,.2f} (현재 위치: {w52_pct:.0f}%)

최근 뉴스:
{news_str if news_str else "(없음)"}

다음 형식으로 한국어로 간결하게 작성해 주세요:

## 기술적 분석
(가격 위치, 추세, 모멘텀에 대한 간단 분석)

## 투자 포인트
(이 종목의 매력 포인트 2-3개)

## 리스크 요인
(주의할 리스크 2-3개)"""

        # Bedrock API 요청 본문 구성 (종목 분석은 max_tokens 1024) / Build Bedrock API request body (stock analysis uses max_tokens 1024)
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        })

        # Bedrock API 호출 / Invoke Bedrock API
        response = client.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )

        # API 응답에서 분석 텍스트 추출 / Extract analysis text from API response
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    except Exception as e:
        # 종목 분석 오류 로깅 및 사용자 친화적 오류 메시지 반환 / Log stock analysis error and return user-friendly error message
        logger.error(f"Bedrock stock analysis error: {e}")
        return f"(AI 종목 분석을 불러올 수 없습니다: {e})"
