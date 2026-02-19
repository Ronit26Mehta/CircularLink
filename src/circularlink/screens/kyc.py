"""
KYC / Settings Screen  [F4]
============================
Lets the logged-in company:
  - View and update their company profile
  - Update their Gemini API key
  - Update primary product (triggers fresh AI scan potential)
  - Update city / geocoordinates
  - Log out
  - Delete account
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Button, Input, Label, Static

from circularlink.core.gstin import GSTINValidator
from circularlink.core.geo import GeoService
from circularlink.storage.db import Database


class KYCSettingsScreen(Container):
    """F4 — KYC / Settings."""

    DEFAULT_CSS = """
    KYCSettingsScreen { background: #1A1B26; overflow-y: auto; }
    .section-title {
        background: #24253A;
        color: #C678DD;
        text-style: bold;
        height: 3;
        padding: 0 2;
        content-align: left middle;
        border-bottom: solid #C678DD;
        margin-bottom: 1;
    }
    #form-container {
        background: #24253A;
        border: solid #3E4451;
        margin: 0 2 1 2;
        padding: 1 2;
        height: auto;
    }
    #api-container {
        background: #24253A;
        border: solid #3E4451;
        margin: 0 2 1 2;
        padding: 1 2;
        height: auto;
    }
    Label { color: #ABB2BF; height: 1; margin-top: 1; }
    Input {
        background: #1E1F2E;
        border: solid #3E4451;
        color: #ABB2BF;
        margin-bottom: 0;
    }
    Input:focus { border: solid #C678DD; }
    Input.-invalid { border: solid #E06C75; }
    .hint { color: #5C6370; height: 1; }
    .validation-ok  { color: #98C379; height: 1; }
    .validation-err { color: #E06C75; height: 1; }
    #btn-row { height: 3; margin: 1 2; }
    Button { margin-right: 1; }
    #danger-row { height: 3; margin: 0 2 1 2; }
    #gstin-display {
        color: #98C379;
        height: 2;
        margin: 0 2 1 2;
        background: #1A2520;
        border: solid #3E4451;
        padding: 0 2;
        content-align: left middle;
    }
    """

    def __init__(self, company_id: str) -> None:
        super().__init__()
        self._company_id = company_id

    def compose(self) -> ComposeResult:
        yield Static("  KYC / Account Settings", classes="section-title")

        # GSTIN status badge (read-only)
        yield Static(id="gstin-display")

        with Container(id="form-container"):
            yield Label("Company Name")
            yield Input(id="f-name")

            yield Label("Primary Product / Manufacturing Activity")
            yield Input(id="f-product")
            yield Static("[dim]Updating this enables re-running the AI byproduct scan.[/dim]", classes="hint")

            yield Label("City")
            yield Input(id="f-city")
            yield Static("", id="f-city-status", classes="hint")

            yield Label("State")
            yield Input(id="f-state")

            yield Label("Contact Email")
            yield Input(id="f-email")

            yield Label("Address (optional)")
            yield Input(id="f-address")

            yield Label("Latitude (optional, overrides city lookup)")
            yield Input(id="f-lat", type="number")

            yield Label("Longitude (optional, overrides city lookup)")
            yield Input(id="f-lon", type="number")

        yield Static("  API Configuration", classes="section-title")
        with Container(id="api-container"):
            yield Label("Gemini API Key  (stored locally, never transmitted)")
            yield Input(id="f-apikey", password=True)
            yield Static(
                "[dim]Get your key free at: https://aistudio.google.com/apikey[/dim]",
                classes="hint",
            )

        with Horizontal(id="btn-row"):
            yield Button("  Save Changes", id="btn-save", classes="btn-ai")
            yield Button("  Reload", id="btn-reload", variant="default")
            yield Button("  Log Out", id="btn-logout", variant="default")

        yield Static("  Danger Zone", classes="section-title")
        with Horizontal(id="danger-row"):
            yield Button("  Delete Account & All Data", id="btn-delete-account", classes="btn-danger")

    def on_mount(self) -> None:
        self._load_company()

    def _load_company(self) -> None:
        company = Database.get_company(self._company_id)
        if not company:
            return

        gstin = company.get("gstin", "")
        r = GSTINValidator.validate(gstin)
        badge = (
            f"[bold green]✓ KYC Verified[/bold green]  GSTIN: [cyan]{gstin}[/cyan]  |  "
            f"State: {r.state_name}  |  Registered: {str(company.get('verified_at',''))[:10]}"
            if r.valid
            else f"[bold red]✗ Invalid GSTIN: {gstin}[/bold red]"
        )
        self.query_one("#gstin-display", Static).update(badge)

        self.query_one("#f-name", Input).value    = company.get("name", "")
        self.query_one("#f-product", Input).value = company.get("primary_product", "")
        self.query_one("#f-city", Input).value    = company.get("city", "")
        self.query_one("#f-state", Input).value   = company.get("state", "")
        self.query_one("#f-email", Input).value   = company.get("contact_email", "")
        self.query_one("#f-address", Input).value = company.get("address", "")

        lat = company.get("latitude", 0)
        lon = company.get("longitude", 0)
        self.query_one("#f-lat", Input).value = str(lat) if lat else ""
        self.query_one("#f-lon", Input).value = str(lon) if lon else ""

        # Show masked API key placeholder
        saved_key = Database.get_api_key()
        if saved_key:
            self.query_one("#f-apikey", Input).placeholder = "Key saved  (enter new key to replace)"
        else:
            self.query_one("#f-apikey", Input).placeholder = "AIza..."

    # ── Input events ────────────────────────────────────────────────────────

    @on(Input.Changed, "#f-city")
    def _city_changed(self, event: Input.Changed) -> None:
        status = self.query_one("#f-city-status", Static)
        if event.value.strip():
            coords = GeoService.lookup_city(event.value.strip())
            if coords:
                status.update(
                    f"[green]✓ {coords.lat:.4f}°N, {coords.lon:.4f}°E[/green]"
                )
            else:
                status.update("[yellow]⚠ City not in geo-database[/yellow]")
        else:
            status.update("")

    # ── Button handlers ──────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-save")
    def _save(self) -> None:
        company = Database.get_company(self._company_id)
        if not company:
            return

        name    = self.query_one("#f-name", Input).value.strip()
        product = self.query_one("#f-product", Input).value.strip()
        city    = self.query_one("#f-city", Input).value.strip()
        state   = self.query_one("#f-state", Input).value.strip()
        email   = self.query_one("#f-email", Input).value.strip()
        address = self.query_one("#f-address", Input).value.strip()
        lat_str = self.query_one("#f-lat", Input).value.strip()
        lon_str = self.query_one("#f-lon", Input).value.strip()
        apikey  = self.query_one("#f-apikey", Input).value.strip()

        # Resolve coordinates — explicit > lookup
        try:
            lat = float(lat_str) if lat_str else 0.0
            lon = float(lon_str) if lon_str else 0.0
        except ValueError:
            lat, lon = 0.0, 0.0

        if (lat == 0 or lon == 0) and city:
            coords = GeoService.lookup_city(city)
            if coords:
                lat, lon = coords.lat, coords.lon

        if not state and city:
            # Try to derive from GSTIN state code if we have it
            gstin = company.get("gstin", "")
            r = GSTINValidator.validate(gstin)
            if r.valid:
                state = state or r.state_name

        updates = {
            "company_id": self._company_id,
            "name": name or company.get("name", ""),
            "primary_product": product or company.get("primary_product", ""),
            "city": city or company.get("city", ""),
            "state": state or company.get("state", ""),
            "contact_email": email or company.get("contact_email", ""),
            "address": address or company.get("address", ""),
            "latitude": lat,
            "longitude": lon,
        }
        Database.upsert_company(updates)
        if apikey:
            Database.set_api_key(apikey)
        self._load_company()
        self.app.notify("Settings saved successfully", severity="information")

    @on(Button.Pressed, "#btn-reload")
    def _reload(self) -> None:
        self._load_company()
        self.app.notify("Profile reloaded", severity="information")

    @on(Button.Pressed, "#btn-logout")
    def _logout(self) -> None:
        from circularlink.screens.modals import ConfirmModal

        def _confirmed(yes: bool) -> None:
            if yes:
                Database.set_current_company_id(None)
                self.post_message(self.app.LogoutEvent())

        self.app.push_screen(
            ConfirmModal("Log Out", "Are you sure you want to log out?"),
            _confirmed,
        )

    @on(Button.Pressed, "#btn-delete-account")
    def _delete_account(self) -> None:
        from circularlink.screens.modals import ConfirmModal

        def _first_confirm(yes: bool) -> None:
            if not yes:
                return

            def _final_confirm(yes2: bool) -> None:
                if yes2:
                    # Delete all products for this company
                    for p in Database.products_by_company(self._company_id):
                        Database.delete_product(p["product_id"])
                    Database.delete_company(self._company_id)
                    Database.set_current_company_id(None)
                    self.app.notify("Account deleted.", severity="warning")
                    self.post_message(self.app.LogoutEvent())

            self.app.push_screen(
                ConfirmModal(
                    "FINAL WARNING",
                    "[bold red]This will permanently delete your account and all listings.[/bold red]\n"
                    "This action CANNOT be undone. Continue?",
                ),
                _final_confirm,
            )

        self.app.push_screen(
            ConfirmModal("Delete Account", "Delete your account and all associated listings?"),
            _first_confirm,
        )
