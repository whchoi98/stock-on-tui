#!/usr/bin/env python3
"""
글로벌 주식 모니터 TUI 애플리케이션 - 토스 증권 스타일 대시보드
Global Stock Monitor TUI Application - Toss Invest style dashboard.
"""
from __future__ import annotations

import sys
import os

# 프로젝트 루트를 Python 경로에 추가하여 모듈 임포트가 가능하게 함 / Add project root to Python path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Textual 프레임워크에서 앱과 키 바인딩 임포트 / Import App and Binding from Textual framework
from textual.app import App
from textual.binding import Binding

# 대시보드 화면 컴포넌트 임포트 / Import dashboard screen component
from screens.dashboard import DashboardScreen


# 주식 모니터 메인 애플리케이션 클래스 / Main Stock Monitor application class
class StockMonitorApp(App):
    """
    글로벌 주식 모니터의 메인 애플리케이션 클래스.
    Textual 기반 TUI로 미국/한국 시장 데이터를 실시간 대시보드에 표시.
    Main application class for Global Stock Monitor.
    Textual-based TUI displaying US/KR market data in a real-time dashboard.
    """

    # 앱 타이틀 및 서브 타이틀 설정 / App title and subtitle configuration
    TITLE = "Global Stock Monitor"
    SUB_TITLE = "US & KR Markets"

    # 스타일시트 경로 설정 / Stylesheet path configuration
    CSS_PATH = "styles/app.tcss"

    # 키보드 단축키 바인딩: 'q' 키로 앱 종료 / Keyboard shortcut bindings: press 'q' to quit the app
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    # 앱에서 사용할 화면 등록 / Register screens available in the app
    SCREENS = {
        "dashboard": DashboardScreen,
    }

    # 앱이 마운트(시작)될 때 대시보드 화면을 표시 / Display the dashboard screen when app is mounted (started)
    def on_mount(self) -> None:
        """앱 시작 시 대시보드 화면으로 전환 / Switch to dashboard screen on app start."""
        self.push_screen("dashboard")


# 메인 진입점: 스크립트가 직접 실행될 때 앱을 시작 / Main entry point: start the app when script is run directly
if __name__ == "__main__":
    # 앱 인스턴스 생성 및 실행 / Create app instance and run
    app = StockMonitorApp()
    app.run()
