"""
Dashboard Screen  [F1]
======================
Overview panel showing:
  - Company details and GSTIN verification badge
  - Marketplace statistics (companies, products, matches)
  - Recent recommendations / matches for this company
  - Recent AI inference log
  - Quick-action buttons
"""

from __future__ import annotations

from datetime import datetime

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Button, DataTable, Label, RichLog, Static

from circularlink.storage.db import Database


class DashboardScreen(Container):
    """F1 — Dashboard overview."""

    DEFAULT_CSS = """
    DashboardScreen { background: #1A1B26; overflow-y: auto; }
    .section-title {
        background: #24253A;
        color: #61AFEF;
        text-style: bold;
        height: 3;
        padding: 0 2;
        content-align: left middle;
        border-bottom: solid #3E4451;
    }
    #company-card {
        background: #24253A;
        border: solid #3E4451;
        margin: 1 2 0 2;
        padding: 1 2;
        height: auto;
    }
    .company-name { color: #ABB2BF; text-style: bold; height: 2; }
    .company-detail { color: #5C6370; height: 1; }
    .gstin-verified { color: #98C379; text-style: bold; }
    #stats-grid {
        layout: grid;
        grid-size: 3;
        grid-gutter: 1 2;
        height: 7;
        margin: 1 2;
    }
    .stat-card {
        background: #24253A;
        border: solid #3E4451;
        padding: 0 2;
        height: 6;
        content-align: left middle;
    }
    .stat-card.s-company { border-left: solid #61AFEF; }
    .stat-card.s-sell    { border-left: solid #E06C75; }
    .stat-card.s-buy     { border-left: solid #98C379; }
    .stat-val { text-style: bold; color: #ABB2BF; }
    .stat-lbl { color: #5C6370; }
    DataTable {
        background: #1A1B26;
        border: solid #3E4451;
        margin: 0 2 0 2;
        height: 10;
    }
    DataTable > .datatable--header {
        background: #24253A;
        color: #61AFEF;
        text-style: bold;
    }
    DataTable > .datatable--cursor { background: #2E3052; }
    RichLog {
        background: #1A1B26;
        border: solid #3E4451;
        margin: 0 2 1 2;
        height: 8;
    }
    #btn-row { height: 3; margin: 1 2; }
    Button { margin-right: 1; }
    """

    def __init__(self, company_id: str) -> None:
        super().__init__()
        self._company_id = company_id

    def compose(self) -> ComposeResult:
        yield Static("  CircuLink Dashboard", classes="section-title")
        yield Container(id="company-card")
        # Stats row
        with Container(id="stats-grid"):
            yield Container(id="stat-companies", classes="stat-card s-company")
            yield Container(id="stat-listings", classes="stat-card s-sell")
            yield Container(id="stat-matches", classes="stat-card s-buy")
        yield Static("  Recent Marketplace Matches", classes="section-title")
        yield DataTable(id="matches-table", zebra_stripes=True)
        yield Static("  Gemini AI Inference Log", classes="section-title")
        yield RichLog(id="llm-log", highlight=True, markup=True)
        with Horizontal(id="btn-row"):
            yield Button("  Refresh", id="btn-refresh", classes="btn-ai")
            yield Button("  Export Data Dir", id="btn-datadir", variant="default")

    def on_mount(self) -> None:
        self._build_matches_table()
        self._refresh_all()

    def _build_matches_table(self) -> None:
        table = self.query_one("#matches-table", DataTable)
        table.clear(columns=True)
        table.add_columns(
            "Material", "Seller", "City", "Fuzzy %", "Location %", "Score %", "Distance"
        )

    def _refresh_all(self) -> None:
        self._load_company_card()
        self._load_stats()
        self._load_matches()
        self._load_llm_log()

    def _load_company_card(self) -> None:
        company = Database.get_company(self._company_id)
        card = self.query_one("#company-card")
        card.remove_children()
        if not company:
            card.mount(Static("[red]Company not found.[/red]"))
            return

        gstin = company.get("gstin", "")
        state = company.get("state", "")
        city  = company.get("city", "")
        email = company.get("contact_email", "")
        prod  = company.get("primary_product", "N/A")
        lat   = company.get("latitude", 0)
        lon   = company.get("longitude", 0)
        vtime = company.get("verified_at", "")[:10]

        from circularlink.core.gstin import GSTINValidator
        gstin_ok = GSTINValidator.is_valid(gstin)
        badge = "[bold green]✓ KYC Verified[/bold green]" if gstin_ok else "[bold red]✗ Unverified[/bold red]"

        card.mount(Static(f"[bold]{company['name']}[/bold]  {badge}", classes="company-name"))
        card.mount(Static(f"GSTIN: [cyan]{gstin}[/cyan]  |  State: {state}  |  City: {city}", classes="company-detail"))
        card.mount(Static(f"Primary Product: [dim]{prod}[/dim]", classes="company-detail"))
        card.mount(Static(f"Email: {email}  |  Coords: {lat:.4f}°N {lon:.4f}°E  |  KYC: {vtime}", classes="company-detail"))

    def _load_stats(self) -> None:
        stats = Database.stats()
        my_products = Database.products_by_company(self._company_id)
        my_matches  = Database.matches_for_company(self._company_id)
        my_approved = sum(1 for p in my_products if p.get("status") == "approved")

        def _fill(widget_id: str, value: str, label: str) -> None:
            c = self.query_one(f"#{widget_id}")
            c.remove_children()
            c.mount(Static(f"[bold]{value}[/bold]", classes="stat-val"))
            c.mount(Static(label, classes="stat-lbl"))

        _fill("stat-companies",
              str(stats["total_companies"]),
              f"Companies  ({stats['approved_products']} listings approved)")
        _fill("stat-listings",
              str(my_approved),
              f"Your Active Listings  ({len(my_products)} total)")
        _fill("stat-matches",
              str(len(my_matches)),
              "Matches Found For You")

    def _load_matches(self) -> None:
        table = self.query_one("#matches-table", DataTable)
        table.clear()
        matches = Database.matches_for_company(self._company_id)
        # Sort by final_score desc
        matches.sort(key=lambda m: m.get("final_score", 0), reverse=True)
        for m in matches[:30]:
            fs  = m.get("final_score", 0)
            fuz = m.get("fuzzy_score", 0)
            loc = m.get("location_score", 0)
            score_text = f"{round(fs * 100)}%"
            dist = m.get("distance_km", -1)
            dist_text = f"{dist:.1f} km" if dist >= 0 else "N/A"
            table.add_row(
                m.get("query_material", m.get("product_name", "")),
                m.get("seller_company_name", ""),
                m.get("seller_city", ""),
                f"{round(fuz * 100)}%",
                f"{round(loc * 100)}%",
                score_text,
                dist_text,
            )

    def _load_llm_log(self) -> None:
        log_widget = self.query_one("#llm-log", RichLog)
        log_widget.clear()
        logs = Database.get_llm_logs(limit=20)
        if not logs:
            log_widget.write("[dim]No AI inference logs yet. Register a product to trigger Gemini.[/dim]")
            return
        for entry in reversed(logs[-10:]):
            ts = str(entry.get("created_at", ""))[:19]
            mats = ", ".join(entry.get("predicted_materials", []))
            conf = entry.get("confidence", 0)
            pid  = entry.get("product_id", "")[:8]
            log_widget.write(
                f"[cyan]{ts}[/cyan] [dim]pid:{pid}[/dim] "
                f"→ [green]{mats}[/green] "
                f"([yellow]conf:{conf:.2f}[/yellow])"
            )

    @on(Button.Pressed, "#btn-refresh")
    def _refresh(self) -> None:
        self._refresh_all()
        self.app.notify("Dashboard refreshed", severity="information")

    @on(Button.Pressed, "#btn-datadir")
    def _open_datadir(self) -> None:
        data_dir = str(Database.data_dir())
        self.app.notify(f"Data stored at: {data_dir}", severity="information", timeout=8)
