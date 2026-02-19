"""
Buyer / Sourcing Screen  [F2]
==============================
Flow B — Buyer (Intelligent Sourcing):
  1. Buyer types a material they need (e.g. "fly ash", "copper scrap")
  2. Gemini AI expands the query with synonyms/related terms
  3. FuzzyMatcher scores all approved marketplace listings against the expanded query
  4. Results ranked by:  final_score = 0.7 × fuzzy_score + 0.3 × location_score
  5. Buyer sees a verified ranked table of "Industrial Matches"
  6. Results are persisted to matches.json for audit/analytics

The screen also shows all approved marketplace listings (browse mode).
"""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Label, LoadingIndicator, RichLog, Static

from circularlink.core.matcher import FuzzyMatcher, MatchCandidate
from circularlink.core.geo import GeoService
from circularlink.storage.db import Database


class BuyerScreen(Container):
    """F2 — Buy: Sourcing (Intelligent Matching)."""

    DEFAULT_CSS = """
    BuyerScreen { background: #1A1B26; overflow-y: auto; }
    .section-title {
        background: #24253A;
        color: #98C379;
        text-style: bold;
        height: 3;
        padding: 0 2;
        content-align: left middle;
        border-bottom: solid #98C379;
        margin-bottom: 1;
    }
    .ai-banner {
        background: #162016;
        color: #98C379;
        border: solid #98C379;
        height: 3;
        padding: 0 2;
        content-align: left middle;
        margin: 0 2 1 2;
    }
    DataTable {
        background: #1A1B26;
        border: solid #3E4451;
        margin: 0 2 1 2;
        height: 14;
    }
    DataTable > .datatable--header {
        background: #24253A;
        color: #98C379;
        text-style: bold;
    }
    DataTable > .datatable--cursor { background: #1E2E1E; }
    RichLog {
        background: #1A1B26;
        border: solid #3E4451;
        margin: 0 2 1 2;
        height: 8;
    }
    #btn-row { height: 3; margin: 0 2 1 2; }
    Button { margin-right: 1; }
    LoadingIndicator { color: #98C379; height: 3; }
    .score-high { color: #98C379; text-style: bold; }
    .score-med  { color: #D19A66; }
    .score-low  { color: #E06C75; }
    """

    SCORE_FORMULA = "final_score = [bold cyan]0.7[/bold cyan] × fuzzy  +  [bold cyan]0.3[/bold cyan] × location"

    def __init__(self, company_id: str) -> None:
        super().__init__()
        self._company_id = company_id
        self._last_query = ""

    def compose(self) -> ComposeResult:
        yield Static("  Buy: Intelligent Sourcing", classes="section-title")
        yield Static(
            f"  Hybrid recommendation engine — {self.SCORE_FORMULA}",
            classes="ai-banner",
        )
        with Horizontal(id="btn-row"):
            yield Button("  Search for Material", id="btn-search", classes="btn-buy")
            yield Button("  Browse All Listings", id="btn-browse", variant="default")
            yield Button("  My Match History", id="btn-history", variant="default")
        yield LoadingIndicator(id="loading", classes="loading")
        yield Static("  Verified Industrial Matches", classes="section-title")
        yield DataTable(id="results-table", zebra_stripes=True, cursor_type="row")
        yield Static("  Matching Engine Log", classes="section-title")
        yield RichLog(id="buyer-log", highlight=True, markup=True)

    def on_mount(self) -> None:
        self.query_one("#loading", LoadingIndicator).display = False
        self._build_results_table()
        self._log(
            "[dim]Welcome to the sourcing screen. "
            "Click 'Search for Material' to find industrial matches.[/dim]"
        )

    def _build_results_table(self) -> None:
        t = self.query_one("#results-table", DataTable)
        t.clear(columns=True)
        t.add_columns(
            "Action", "Material", "Seller", "City", "Qty", "Fuzzy %", "Loc %", "Score %", "Dist km", "Status"
        )

    def _log(self, msg: str) -> None:
        try:
            self.query_one("#buyer-log", RichLog).write(msg)
        except Exception:
            pass

    def _set_loading(self, visible: bool) -> None:
        try:
            self.query_one("#loading", LoadingIndicator).display = visible
        except Exception:
            pass

    # ── Search triggered ────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-search")
    def _open_search(self) -> None:
        from circularlink.screens.modals import SearchModal

        def _on_query(query: str | None) -> None:
            if query:
                self._last_query = query
                self._run_search(query)

        self.app.push_screen(SearchModal(), _on_query)

    @on(Button.Pressed, "#btn-browse")
    def _browse_all(self) -> None:
        self._run_browse()

    @on(Button.Pressed, "#btn-history")
    def _show_history(self) -> None:
        self._load_match_history()

    # ── Worker: run full search pipeline ────────────────────────────────────

    @work(thread=True)
    def _run_search(self, query: str) -> None:
        self.app.call_from_thread(self._set_loading, True)
        self.app.call_from_thread(self._log, f"[cyan]  Searching for: '{query}'…[/cyan]")

        # Resolve buyer coordinates
        company = Database.get_company(self._company_id)
        buyer_lat = float((company or {}).get("latitude", 0) or 0)
        buyer_lon = float((company or {}).get("longitude", 0) or 0)
        if buyer_lat == 0 or buyer_lon == 0:
            city = (company or {}).get("city", "")
            coords = GeoService.lookup_city(city)
            if coords:
                buyer_lat, buyer_lon = coords.lat, coords.lon

        # Step 1 — Gemini keyword expansion
        api_key = Database.get_api_key()
        expanded_queries: list[str] = [query]

        if api_key:
            try:
                from circularlink.core.gemini_agent import GeminiAgent
                agent = GeminiAgent(api_key=api_key)
                self.app.call_from_thread(self._log, "[cyan]  Gemini: Expanding query keywords…[/cyan]")
                resp = agent.expand_keywords(query)
                if resp.success and resp.expanded_keywords:
                    expanded_queries.extend(resp.expanded_keywords)
                    kw_str = ", ".join(resp.expanded_keywords[:5])
                    self.app.call_from_thread(
                        self._log,
                        f"[cyan]  Gemini: Expanded to [{kw_str}][/cyan]",
                    )
            except Exception as exc:
                self.app.call_from_thread(self._log, f"[yellow]⚠ Gemini expansion failed: {exc}[/yellow]")
        else:
            self.app.call_from_thread(self._log, "[yellow]⚠ No API key — skipping Gemini expansion[/yellow]")

        # Step 2 — Load candidates (approved only, not own listings)
        products = Database.all_products(status_filter="approved")
        candidates: list[MatchCandidate] = []
        company_cache: dict[str, dict] = {}

        for p in products:
            cid = p.get("company_id", "")
            if cid == self._company_id:
                continue  # skip own listings
            if cid not in company_cache:
                c = Database.get_company(cid)
                company_cache[cid] = c or {}
            cdata = company_cache[cid]
            candidates.append(MatchCandidate.from_product_dict(p, cdata.get("name", "")))

        if not candidates:
            self.app.call_from_thread(
                self._log,
                "[yellow]⚠ No approved listings from other companies yet.[/yellow]",
            )
            self.app.call_from_thread(self._set_loading, False)
            return

        self.app.call_from_thread(self._log, f"[dim]  Scoring {len(candidates)} candidates…[/dim]")

        # Step 3 — Run fuzzy matching for each expanded query, merge results
        best_results: dict[str, any] = {}  # product_id → MatchResult
        for eq in expanded_queries[:6]:  # cap at 6 expansions to avoid slowdown
            results = FuzzyMatcher.match(
                query=eq,
                candidates=candidates,
                buyer_lat=buyer_lat,
                buyer_lon=buyer_lon,
                top_k=20,
                exclude_company_id=self._company_id,
            )
            for r in results:
                if r.product_id not in best_results or r.final_score > best_results[r.product_id].final_score:
                    best_results[r.product_id] = r

        final_results = sorted(best_results.values(), key=lambda r: r.final_score, reverse=True)[:20]

        # Step 4 — Persist to matches
        if final_results:
            Database.save_matches(
                buyer_company_id=self._company_id,
                query_material=query,
                results=[
                    {
                        "product_id": r.product_id,
                        "product_name": r.product_name,
                        "seller_company_name": r.seller_company_name,
                        "seller_city": r.seller_city,
                        "fuzzy_score": r.fuzzy_score,
                        "location_score": r.location_score,
                        "final_score": r.final_score,
                        "distance_km": r.distance_km,
                    }
                    for r in final_results
                ],
            )

        self.app.call_from_thread(
            self._log,
            f"[green]  Found {len(final_results)} matches (best: {final_results[0].final_pct}%)[/green]"
            if final_results else "[yellow]  No matches found above threshold.[/yellow]",
        )
        self.app.call_from_thread(self._render_results, final_results)
        self.app.call_from_thread(self._set_loading, False)
        self.app.call_from_thread(
            self.app.notify,
            f"{len(final_results)} matches found for '{query}'",
            severity="information",
        )

    def _render_results(self, results: list) -> None:
        t = self.query_one("#results-table", DataTable)
        t.clear()
        for r in results:
            dist_str = f"{r.distance_km:.1f}" if r.distance_km >= 0 else "N/A"
            score_pct = r.final_pct
            score_style = "[green]" if score_pct >= 75 else "[yellow]" if score_pct >= 50 else "[red]"
            status_str = (
                "[green]Verified[/green]" if r.status == "approved"
                else "[red]Restricted[/red]"
            )
            qty_str = f"{r.quantity:.0f} {r.unit}".strip() if r.quantity else "N/A"
            t.add_row(
                "BUY",
                r.product_name,
                r.seller_company_name,
                r.seller_city,
                qty_str,
                f"{r.fuzzy_pct}%",
                f"{r.location_pct}%",
                f"{score_style}{score_pct}%[/]",
                dist_str,
                status_str,
                key=r.product_id,
            )

    @work(thread=True)
    def _run_browse(self) -> None:
        self.app.call_from_thread(self._set_loading, True)
        self.app.call_from_thread(self._log, "[dim]  Loading all approved marketplace listings…[/dim]")

        products = Database.all_products(status_filter="approved")
        company_cache: dict[str, dict] = {}

        t = self.query_one("#results-table", DataTable)
        self.app.call_from_thread(t.clear)

        rows = []
        for p in products:
            if p.get("company_id") == self._company_id:
                continue
            cid = p.get("company_id", "")
            if cid not in company_cache:
                c = Database.get_company(cid)
                company_cache[cid] = c or {}
            cname = company_cache[cid].get("name", "")
            qty_str = f"{p.get('quantity', 0):.0f} {p.get('unit', '')}".strip()
            rows.append((
                "BROWSE",
                p.get("name", ""),
                cname,
                p.get("city", ""),
                qty_str,
                "—",
                "—",
                "—",
                "—",
                "[green]Verified[/green]",
            ))

        def _add_rows() -> None:
            for row in rows:
                t.add_row(*row)

        self.app.call_from_thread(_add_rows)
        self.app.call_from_thread(self._log, f"[dim]  {len(rows)} listings in marketplace.[/dim]")
        self.app.call_from_thread(self._set_loading, False)

    def _load_match_history(self) -> None:
        t = self.query_one("#results-table", DataTable)
        t.clear()
        matches = Database.matches_for_company(self._company_id)
        matches.sort(key=lambda m: m.get("final_score", 0), reverse=True)
        self._log(f"[dim]  Showing {len(matches)} saved matches.[/dim]")
        for m in matches[:30]:
            fs  = round(m.get("final_score", 0) * 100)
            fuz = round(m.get("fuzzy_score", 0) * 100)
            loc = round(m.get("location_score", 0) * 100)
            dist = m.get("distance_km", -1)
            dist_str = f"{dist:.1f}" if isinstance(dist, float) and dist >= 0 else "N/A"
            t.add_row(
                "HISTORY",
                m.get("product_name", ""),
                m.get("seller_company_name", ""),
                m.get("seller_city", ""),
                "—",
                f"{fuz}%",
                f"{loc}%",
                f"{fs}%",
                dist_str,
                "[green]Verified[/green]",
                key=m.get("match_id", ""),
            )
