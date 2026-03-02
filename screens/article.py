# 뉴스 기사 AI 분석 화면 모듈: 기사 내용을 가져와 Bedrock Claude로 분석
# Article AI analysis screen module: fetches article content and analyzes via Bedrock Claude

from __future__ import annotations

import asyncio

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, Markdown

from services.news import NewsItem, fetch_article_content


# 기사 전문 뷰어 및 AI 분석 화면 클래스: Bedrock Claude Sonnet을 통한 기사 분석 제공
# Full-screen article viewer and AI analysis class: provides article analysis via Bedrock Claude Sonnet
class ArticleScreen(Screen):
    """Full-screen article viewer with AI analysis via Bedrock Claude Sonnet 4.6."""

    # 키 바인딩: b/esc=뒤로, r=새로고침 / Key bindings: b/esc=back, r=reload
    BINDINGS = [
        Binding("b", "go_back", "Back"),
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Reload"),
    ]

    # 기사 화면 초기화: 뉴스 항목 저장 / Initialize article screen: store news item
    def __init__(self, item: NewsItem, **kwargs) -> None:
        super().__init__(**kwargs)
        self._item = item

    # UI 위젯 구성: 제목, 메타정보, 상태, AI 분석 결과 영역
    # Compose UI widgets: title, meta info, status, AI analysis result area
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll():
            yield Static("", id="article-title")
            yield Static("", id="article-meta")
            yield Static("", id="article-status")
            # AI 분석 결과를 마크다운으로 표시 / Display AI analysis result as markdown
            yield Markdown("", id="article-ai")
        yield Footer()

    # 화면 마운트 시 제목/메타 표시 및 AI 분석 시작
    # On mount: display title/meta and start AI analysis
    def on_mount(self) -> None:
        # 기사 제목 표시 / Display article title
        title_text = Text()
        title_text.append(f"  {self._item.title}", style="bold")
        self.query_one("#article-title", Static).update(title_text)

        # 메타 정보: 출처 뱃지, 발행일, 언어 표시
        # Meta info: source badge, publish date, language indicator
        meta_text = Text()
        badge_color = "#3182F6" if self._item.is_korean else "#F04452"
        meta_text.append(f"  [{self._item.source}]", style=f"bold {badge_color}")
        if self._item.published:
            meta_text.append(f"  {self._item.published}", style="dim")
        # 한국어 기사는 그대로, 영어 기사는 한국어 번역 표시
        # Korean articles shown as-is, English articles marked for Korean translation
        lang = "한국어" if self._item.is_korean else "English -> 한국어 번역"
        meta_text.append(f"  |  {lang}", style="dim")
        self.query_one("#article-meta", Static).update(meta_text)

        self.query_one("#article-status", Static).update(
            "  Fetching article & AI analysis (Claude Sonnet 4.6)..."
        )
        self.load_and_analyze()

    # 뒤로 가기: 이전 화면으로 복귀 / Go back: return to previous screen
    def action_go_back(self) -> None:
        self.dismiss()

    # 새로고침: AI 분석 초기화 후 다시 로딩 / Refresh: clear AI analysis and reload
    def action_refresh(self) -> None:
        self.query_one("#article-status", Static).update(
            "  Reloading..."
        )
        self.query_one("#article-ai", Markdown).update("")
        self.load_and_analyze()

    # 기사 내용 가져오기 + AI 분석 2단계 비동기 처리
    # Two-step async process: fetch article content + AI analysis
    @work(exclusive=True, group="article", exit_on_error=False)
    async def load_and_analyze(self) -> None:
        from services.bedrock import is_bedrock_available, _DISABLED_MSG

        # Bedrock 사용 가능 여부 확인 / Check Bedrock availability first
        if not is_bedrock_available():
            self.query_one("#article-status", Static).update("")
            self.query_one("#article-ai", Markdown).update(_DISABLED_MSG)
            return

        # 1단계: 기사 원문 가져오기 / Step 1: Fetch article content
        self.query_one("#article-status", Static).update(
            "  [1/2] Fetching article content..."
        )
        content = await asyncio.to_thread(fetch_article_content, self._item.url)

        # 2단계: Bedrock Claude로 AI 분석 수행 / Step 2: Perform AI analysis with Bedrock Claude
        self.query_one("#article-status", Static).update(
            "  [2/2] AI analyzing with Claude Sonnet 4.6..."
        )

        from services.bedrock import analyze_article
        analysis = await asyncio.to_thread(
            analyze_article,
            self._item.title,
            content,
            self._item.is_korean,
        )

        # 분석 결과를 마크다운으로 표시 / Display analysis result as markdown
        self.query_one("#article-status", Static).update(
            "  AI Analysis (Powered by Claude Sonnet 4.6 via Amazon Bedrock)"
        )
        self.query_one("#article-ai", Markdown).update(analysis)
