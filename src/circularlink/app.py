"""
CircuLink Terminal — Main Application
======================================
Root Textual App class.  Manages:
  - Screen lifecycle (Welcome → Main)
  - Sidebar navigation with F1-F4 keybindings
  - Custom message types (LoginEvent, LogoutEvent)
  - Global CSS loading
  - Session state (current company_id)

Architecture
  WelcomeScreen  — login / registration (shown when no session)
  MainScreen     — sidebar + ContentSwitcher hosting 4 sub-screens
    ContentSwitcher
      DashboardScreen   (#c-dashboard)
      BuyerScreen       (#c-buyer)
      SellerScreen      (#c-seller)
      KYCSettingsScreen (#c-kyc)
"""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.css.query import NoMatches
from textual.message import Message
from textual.screen import Screen
from textual.widgets import (
    Button,
    ContentSwitcher,
    Footer,
    Header,
    Label,
    Static,
)

from circularlink.storage.db import Database
from circularlink.screens.welcome import WelcomeScreen
from circularlink.screens.dashboard import DashboardScreen
from circularlink.screens.buyer import BuyerScreen
from circularlink.screens.seller import SellerScreen
from circularlink.screens.kyc import KYCSettingsScreen


# ---------------------------------------------------------------------------
# Custom message types
# ---------------------------------------------------------------------------

class LoginEvent(Message):
    """Posted by WelcomeScreen when a company successfully authenticates."""
    def __init__(self, company_id: str) -> None:
        super().__init__()
        self.company_id = company_id


class LogoutEvent(Message):
    """Posted by any screen to trigger session teardown."""


# ---------------------------------------------------------------------------
# Sidebar Widget
# ---------------------------------------------------------------------------

_NAV_ITEMS = [
    ("F1", "Dashboard", "c-dashboard"),
    ("F2", "Buy: Sourcing", "c-buyer"),
    ("F3", "Sell: Inventory", "c-seller"),
    ("F4", "KYC / Settings", "c-kyc"),
]


class Sidebar(Container):
    """Left-docked navigation sidebar."""

    DEFAULT_CSS = """
    Sidebar {
        dock: left;
        width: 24;
        background: #24253A;
        border-right: solid #3E4451;
        padding: 0;
    }
    .nav-logo {
        height: 4;
        background: #1A1B26;
        color: #61AFEF;
        text-style: bold;
        padding: 1 2;
        content-align: left middle;
        border-bottom: solid #3E4451;
    }
    .nav-company {
        height: 3;
        color: #98C379;
        padding: 0 2;
        content-align: left middle;
        border-bottom: solid #3E4451;
    }
    Button.nav-item {
        height: 3;
        width: 1fr;
        padding: 0 2;
        color: #5C6370;
        background: #24253A;
        border: none;
        text-align: left;
        content-align: left middle;
    }
    Button.nav-item:hover {
        background: #2E3052;
        color: #ABB2BF;
    }
    Button.nav-item:focus {
        text-style: none;
    }
    Button.nav-item.active {
        background: #2E3052;
        color: #61AFEF;
        border-left: solid #61AFEF;
    }
    .nav-hotkey {
        color: #C678DD;
        text-style: bold;
    }
    .nav-divider {
        height: 1;
        border-top: solid #3E4451;
        margin: 0 1;
    }
    .nav-footer {
        height: 2;
        color: #5C6370;
        padding: 0 2;
        content-align: left middle;
        dock: bottom;
        border-top: solid #3E4451;
    }
    """

    def __init__(self, company_name: str, active_pane: str = "c-dashboard") -> None:
        super().__init__()
        self._company_name = company_name
        self._active_pane = active_pane

    def compose(self) -> ComposeResult:
        yield Static(" CircuLink ⚙", classes="nav-logo")
        name_short = self._company_name[:20] + ("…" if len(self._company_name) > 20 else "")
        yield Static(f" {name_short}", classes="nav-company")
        for hotkey, label, pane_id in _NAV_ITEMS:
            is_active = pane_id == self._active_pane
            item = Button(
                f" [{hotkey}]  {label}",
                classes=f"nav-item{'  active' if is_active else ''}",
                id=f"nav-{pane_id}",
            )
            yield item
        yield Static("", classes="nav-divider")
        yield Static(" v1.0.0  MIT License", classes="nav-footer")

    def set_active(self, pane_id: str) -> None:
        for _, _, pid in _NAV_ITEMS:
            try:
                widget = self.query_one(f"#nav-{pid}", Button)
                if pid == pane_id:
                    widget.add_class("active")
                else:
                    widget.remove_class("active")
            except NoMatches:
                pass
        self._active_pane = pane_id


# ---------------------------------------------------------------------------
# Main Screen (post-login)
# ---------------------------------------------------------------------------

class MainScreen(Screen):
    """
    The primary application screen shown after login.
    Contains the sidebar and a ContentSwitcher for the four main panels.
    """

    BINDINGS = [
        Binding("f1", "show_dashboard", "Dashboard", show=True),
        Binding("f2", "show_buyer",     "Sourcing",  show=True),
        Binding("f3", "show_seller",    "Inventory", show=True),
        Binding("f4", "show_kyc",       "KYC/Settings", show=True),
        Binding("ctrl+q", "quit_app",   "Quit",      show=True),
    ]

    DEFAULT_CSS = """
    MainScreen {
        background: #1A1B26;
        layout: horizontal;
    }
    #content-wrapper {
        background: #1A1B26;
        width: 1fr;
        overflow: auto;
    }
    ContentSwitcher {
        height: 1fr;
        width: 1fr;
        background: #1A1B26;
    }
    Footer {
        background: #24253A;
        color: #5C6370;
        height: 1;
    }
    """

    def __init__(self, company_id: str) -> None:
        super().__init__()
        self._company_id = company_id
        self._active_pane = "c-dashboard"

    def compose(self) -> ComposeResult:
        company = Database.get_company(self._company_id)
        company_name = company["name"] if company else "Unknown"

        yield Sidebar(company_name=company_name, active_pane="c-dashboard")
        with Container(id="content-wrapper"):
            with ContentSwitcher(initial="c-dashboard", id="main-switcher"):
                dashboard = DashboardScreen(self._company_id)
                dashboard.id = "c-dashboard"
                yield dashboard
                
                buyer = BuyerScreen(self._company_id)
                buyer.id = "c-buyer"
                yield buyer
                
                seller = SellerScreen(self._company_id)
                seller.id = "c-seller"
                yield seller
                
                kyc = KYCSettingsScreen(self._company_id)
                kyc.id = "c-kyc"
                yield kyc
            yield Footer()

    # ── Navigation actions ──────────────────────────────────────────────────

    def _switch_to(self, pane_id: str) -> None:
        try:
            switcher = self.query_one("#main-switcher", ContentSwitcher)
            switcher.current = pane_id
            sidebar = self.query_one(Sidebar)
            sidebar.set_active(pane_id)
            self._active_pane = pane_id
        except NoMatches:
            pass

    def action_show_dashboard(self) -> None:
        self._switch_to("c-dashboard")
        # Refresh dashboard stats on each visit
        try:
            self.query_one("#c-dashboard", DashboardScreen)._refresh_all()
        except Exception:
            pass

    def action_show_buyer(self) -> None:
        self._switch_to("c-buyer")

    def action_show_seller(self) -> None:
        self._switch_to("c-seller")

    def action_show_kyc(self) -> None:
        self._switch_to("c-kyc")
        try:
            self.query_one("#c-kyc", KYCSettingsScreen)._load_company()
        except Exception:
            pass

    def action_quit_app(self) -> None:
        self.app.exit()

    # ── Handle sidebar click ────────────────────────────────────────────────

    @on(Button.Pressed)
    def _nav_click(self, event: Button.Pressed) -> None:
        widget_id = event.button.id or ""
        mapping = {
            "nav-c-dashboard": "c-dashboard",
            "nav-c-buyer":     "c-buyer",
            "nav-c-seller":    "c-seller",
            "nav-c-kyc":       "c-kyc",
        }
        if widget_id in mapping:
            self._switch_to(mapping[widget_id])


# ---------------------------------------------------------------------------
# Root Application
# ---------------------------------------------------------------------------

class CircuLinkApp(App):
    """CircuLink Terminal — Root Application."""

    # Expose message types as class attributes so screens can reference them
    LoginEvent  = LoginEvent
    LogoutEvent = LogoutEvent

    TITLE = "CircuLink Terminal"
    SUB_TITLE = "AI-Driven Marketplace for Industrial Circular Economy"
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    # Load TCSS from bundled file
    @property
    def CSS_PATH(self) -> str:
        return str(Path(__file__).parent / "styles.tcss")

    def on_mount(self) -> None:
        """On startup, check for existing session; show welcome or main."""
        company_id = Database.get_current_company_id()
        if company_id and Database.get_company(company_id):
            self.push_screen(MainScreen(company_id=company_id))
        else:
            self.push_screen(WelcomeScreen())

    # ── Global message handlers ─────────────────────────────────────────────

    def on_login_event(self, message: LoginEvent) -> None:
        """Switch from WelcomeScreen to MainScreen after successful login."""
        # Pop all screens except the last one, then push MainScreen
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.push_screen(MainScreen(company_id=message.company_id))

    def on_logout_event(self, message: LogoutEvent) -> None:
        """Tear down session and return to WelcomeScreen."""
        Database.set_current_company_id(None)
        # Pop all screens except the last one
        while len(self.screen_stack) > 1:
            self.pop_screen()
        # Push WelcomeScreen
        self.push_screen(WelcomeScreen())

    def compose(self) -> ComposeResult:
        # App compose is bypassed — on_mount handles screen routing
        yield Container()
