# 뉴스 피드 위젯 모듈 — 경제 뉴스 헤드라인을 스크롤 가능한 리스트로 표시하고 키보드 탐색을 지원
# News feed widget module — displays economic news headlines in a scrollable list with keyboard navigation
from __future__ import annotations

from typing import List

from rich.text import Text
from textual.message import Message
from textual.widgets import Static, ListView, ListItem
from textual.containers import Vertical

from services.news import NewsItem


# 뉴스 리스트 아이템 클래스 — 개별 뉴스 헤드라인을 선택 가능한 리스트 항목으로 렌더링
# News list item class — renders individual news headline as a selectable list entry
class NewsListItem(ListItem):
    """A single news headline as a selectable list item."""

    # 위젯 기본 CSS 스타일 정의 / Default CSS style definition for the widget
    DEFAULT_CSS = """
    NewsListItem {
        height: 2;
        padding: 0 2;
    }
    """

    # 생성자: 뉴스 아이템 데이터를 저장하고 ListItem을 초기화
    # Constructor: store news item data and initialize ListItem
    def __init__(self, item: NewsItem, **kwargs) -> None:
        super().__init__(**kwargs)
        # 이 리스트 항목에 연결된 뉴스 데이터 / News data associated with this list entry
        self.news_item = item

    # UI 구성 메서드: 뉴스 출처, 제목, 게시 시간을 Rich Text로 렌더링
    # Compose method: render news source, title, and publish time as Rich Text
    def compose(self):
        text = Text()
        # 한국 뉴스이면 파란색 뱃지, 그 외(미국 등)이면 빨간색 뱃지 / Blue badge for Korean news, red badge for others (US, etc.)
        if self.news_item.is_korean:
            badge_color = "#3182F6"
        else:
            badge_color = "#F04452"
        # 뉴스 출처 뱃지 표시 / Display news source badge
        text.append(f"[{self.news_item.source}] ", style=f"bold {badge_color}")
        # 뉴스 제목 표시 / Display news title
        text.append(self.news_item.title, style="")
        # 게시 시간이 있으면 흐리게 표시 / Display publish time dimmed if available
        if self.news_item.published:
            text.append(f"  {self.news_item.published}", style="dim")
        yield Static(text)


# 뉴스 피드 컨테이너 클래스 — 뉴스 리스트를 포함하는 스크롤 가능한 수직 컨테이너 (키보드 탐색 지원)
# News feed container class — scrollable vertical container holding the news list (with keyboard navigation)
class NewsFeed(Vertical):
    """Scrollable, keyboard-navigable news feed."""

    # 위젯 기본 CSS 스타일 정의 / Default CSS style definition for the widget
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

    # 뉴스 선택 메시지 클래스 — 사용자가 뉴스 항목을 선택했을 때 발행되는 Textual 메시지
    # News selected message class — Textual message emitted when a user selects a news item
    class NewsSelected(Message):
        """Emitted when a news item is selected."""
        # 선택된 뉴스 아이템을 메시지에 담아 초기화 / Initialize message with the selected news item
        def __init__(self, item: NewsItem) -> None:
            super().__init__()
            self.item = item

    # 생성자: 내부 뉴스 아이템 리스트를 빈 상태로 초기화
    # Constructor: initialize internal news items list as empty
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # 현재 로드된 뉴스 아이템 목록 / Currently loaded news items list
        self._items: List[NewsItem] = []

    # UI 구성 메서드: 제목 행과 뉴스 리스트뷰를 배치
    # Compose method: lay out title row and news list view
    def compose(self):
        # 뉴스 피드 제목 (단축키 안내 포함) / News feed title (with shortcut key hints)
        yield Static(" Economic News  [Enter] Read  [Up/Down] Navigate", classes="news-title")
        # 뉴스 항목을 담는 리스트뷰 / ListView holding news entries
        yield ListView(id="news-list")

    # 뉴스 데이터 갱신 메서드: 기존 항목을 비우고 새 뉴스 아이템으로 리스트를 다시 구성
    # Update news method: clear existing items and rebuild list with new news items
    def update_news(self, items: List[NewsItem]) -> None:
        self._items = items
        list_view = self.query_one("#news-list", ListView)
        # 기존 리스트 항목 모두 제거 / Remove all existing list entries
        list_view.clear()
        # 새 뉴스 항목을 리스트에 추가 / Append new news items to the list
        for item in items:
            list_view.append(NewsListItem(item))

    # 리스트뷰 선택 이벤트 핸들러: 뉴스 항목이 선택되면 NewsSelected 메시지를 발행
    # ListView selection event handler: emit NewsSelected message when a news item is selected
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # 선택된 항목이 NewsListItem인지 확인 후 메시지 발행 / Verify selected item is NewsListItem before emitting message
        if isinstance(event.item, NewsListItem):
            self.post_message(self.NewsSelected(event.item.news_item))
