from __future__ import annotations

from typing import List

from rich.text import Text
from textual.message import Message
from textual.widgets import Static, ListView, ListItem
from textual.containers import Vertical

from services.news import NewsItem


class NewsListItem(ListItem):
    """A single news headline as a selectable list item."""

    DEFAULT_CSS = """
    NewsListItem {
        height: 2;
        padding: 0 2;
    }
    """

    def __init__(self, item: NewsItem, **kwargs) -> None:
        super().__init__(**kwargs)
        self.news_item = item

    def compose(self):
        text = Text()
        if self.news_item.is_korean:
            badge_color = "#3182F6"
        else:
            badge_color = "#F04452"
        text.append(f"[{self.news_item.source}] ", style=f"bold {badge_color}")
        text.append(self.news_item.title, style="")
        if self.news_item.published:
            text.append(f"  {self.news_item.published}", style="dim")
        yield Static(text)


class NewsFeed(Vertical):
    """Scrollable, keyboard-navigable news feed."""

    DEFAULT_CSS = """
    NewsFeed {
        height: auto;
        max-height: 18;
        min-height: 8;
        border: solid $surface-lighten-2;
        margin: 0 1;
    }
    NewsFeed .news-title {
        text-style: bold;
        padding: 0 2;
        height: 2;
        color: $text;
    }
    NewsFeed ListView {
        height: auto;
        max-height: 15;
    }
    """

    class NewsSelected(Message):
        """Emitted when a news item is selected."""
        def __init__(self, item: NewsItem) -> None:
            super().__init__()
            self.item = item

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._items: List[NewsItem] = []

    def compose(self):
        yield Static(" Economic News  [Enter] Read  [Up/Down] Navigate", classes="news-title")
        yield ListView(id="news-list")

    def update_news(self, items: List[NewsItem]) -> None:
        self._items = items
        list_view = self.query_one("#news-list", ListView)
        list_view.clear()
        for item in items:
            list_view.append(NewsListItem(item))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, NewsListItem):
            self.post_message(self.NewsSelected(event.item.news_item))
