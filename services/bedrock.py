from __future__ import annotations

import json
import logging
import os
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError

logger = logging.getLogger(__name__)

BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")

_bedrock_available: Optional[bool] = None
_DISABLED_MSG = (
    "⚠ AWS Bedrock가 설정되지 않아 AI 기능을 사용할 수 없습니다.\n"
    "  - 뉴스 기사 AI 분석 / 영한 번역\n"
    "  - AI 종목 분석\n"
    "설정 방법: install.sh 재실행 또는 aws configure 실행"
)


def is_bedrock_available() -> bool:
    """Check if AWS Bedrock credentials are configured."""
    global _bedrock_available
    if _bedrock_available is not None:
        return _bedrock_available
    try:
        session = boto3.Session()
        creds = session.get_credentials()
        if creds is None:
            _bedrock_available = False
        else:
            creds = creds.get_frozen_credentials()
            _bedrock_available = bool(creds.access_key and creds.secret_key)
    except Exception:
        _bedrock_available = False
    return _bedrock_available


def _get_client():
    if not is_bedrock_available():
        raise RuntimeError(_DISABLED_MSG)
    return boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def analyze_article(title: str, content: str, is_korean: bool) -> str:
    """Use Claude Sonnet 4.6 via Bedrock to analyze a news article.

    For Korean articles: summarize, analyze, provide insights.
    For English articles: translate to Korean first, then summarize/analyze/provide insights.
    """
    try:
        client = _get_client()

        if is_korean:
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

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        })

        response = client.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )

        result = json.loads(response["body"].read())
        text = result["content"][0]["text"]
        return text

    except Exception as e:
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
    """Use Claude via Bedrock to analyze a stock and provide insights."""
    try:
        client = _get_client()

        news_str = ""
        if news_titles:
            news_str = "\n".join(f"- {t}" for t in news_titles[:5])

        per_str = f"{pe_ratio:.2f}" if pe_ratio else "N/A"
        w52_pct = ((price - week52_low) / (week52_high - week52_low) * 100) if week52_high > week52_low else 0

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

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        })

        response = client.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=body,
        )

        result = json.loads(response["body"].read())
        return result["content"][0]["text"]

    except Exception as e:
        logger.error(f"Bedrock stock analysis error: {e}")
        return f"(AI 종목 분석을 불러올 수 없습니다: {e})"
