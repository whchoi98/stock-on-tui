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


class ArticleScreen(Screen):
    """Full-screen article viewer with AI analysis via Bedrock Claude Sonnet 4.6."""

    BINDINGS = [
        Binding("b", "go_back", "Back"),
        Binding("escape", "go_back", "Back"),
        Binding("r", "refresh", "Reload"),
    ]

    def __init__(self, item: NewsItem, **kwargs) -> None:
        super().__init__(**kwargs)
        self._item = item

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll():
            yield Static("", id="article-title")
            yield Static("", id="article-meta")
            yield Static("", id="article-status")
            yield Markdown("", id="article-ai")
        yield Footer()

    def on_mount(self) -> None:
        # Title
        title_text = Text()
        title_text.append(f"  {self._item.title}", style="bold")
        self.query_one("#article-title", Static).update(title_text)

        # Meta
        meta_text = Text()
        badge_color = "#3182F6" if self._item.is_korean else "#F04452"
        meta_text.append(f"  [{self._item.source}]", style=f"bold {badge_color}")
        if self._item.published:
            meta_text.append(f"  {self._item.published}", style="dim")
        lang = "한국어" if self._item.is_korean else "English -> 한국어 번역"
        meta_text.append(f"  |  {lang}", style="dim")
        self.query_one("#article-meta", Static).update(meta_text)

        self.query_one("#article-status", Static).update(
            "  Fetching article & AI analysis (Claude Sonnet 4.6)..."
        )
        self.load_and_analyze()

    def action_go_back(self) -> None:
        self.dismiss()

    def action_refresh(self) -> None:
        self.query_one("#article-status", Static).update(
            "  Reloading..."
        )
        self.query_one("#article-ai", Markdown).update("")
        self.load_and_analyze()

    @work(exclusive=True, group="article", exit_on_error=False)
    async def load_and_analyze(self) -> None:
        from services.bedrock import is_bedrock_available, _DISABLED_MSG

        # Check Bedrock availability first
        if not is_bedrock_available():
            self.query_one("#article-status", Static).update("")
            self.query_one("#article-ai", Markdown).update(_DISABLED_MSG)
            return

        # Step 1: Fetch article content
        self.query_one("#article-status", Static).update(
            "  [1/2] Fetching article content..."
        )
        content = await asyncio.to_thread(fetch_article_content, self._item.url)

        # Step 2: Analyze with Bedrock
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

        # Display result
        self.query_one("#article-status", Static).update(
            "  AI Analysis (Powered by Claude Sonnet 4.6 via Amazon Bedrock)"
        )
        self.query_one("#article-ai", Markdown).update(analysis)
