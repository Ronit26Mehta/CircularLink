"""
Welcome / Onboarding Screen
============================
First screen shown to the user.  Handles:
  - Login: returning companies authenticate by typing their GSTIN
  - Registration: new companies fill out a form — GSTIN is validated live
  - API key configuration (prompted if missing)
"""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Input,
    Label,
    LoadingIndicator,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)

from circularlink.core.gstin import GSTINValidator
from circularlink.core.geo import GeoService
from circularlink.storage.db import Database


_LOGO = """
 ██████╗██╗██████╗  ██████╗██╗   ██╗██╗     ██╗███╗   ██╗██╗  ██╗
██╔════╝██║██╔══██╗██╔════╝██║   ██║██║     ██║████╗  ██║██║ ██╔╝
██║     ██║██████╔╝██║     ██║   ██║██║     ██║██╔██╗ ██║█████╔╝ 
██║     ██║██╔══██╗██║     ██║   ██║██║     ██║██║╚██╗██║██╔═██╗ 
╚██████╗██║██║  ██║╚██████╗╚██████╔╝███████╗██║██║ ╚████║██║  ██╗
 ╚═════╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝
"""

_TAGLINE = "AI-Driven Marketplace for Industrial Circular Economy"


class WelcomeScreen(Screen):
    """Login / registration onboarding screen."""

    CSS = """
    WelcomeScreen {
        background: #1A1B26;
        align: center middle;
    }
    #welcome-panel {
        background: #24253A;
        border: double #61AFEF;
        width: 80;
        height: auto;
        padding: 1 3;
        min-height: 30;
    }
    .logo-text {
        color: #61AFEF;
        text-style: bold;
        height: 8;
        content-align: center middle;
        text-align: center;
    }
    .tagline {
        color: #5C6370;
        height: 1;
        content-align: center middle;
        text-align: center;
        margin-bottom: 1;
    }
    Input {
        background: #1E1F2E;
        border: solid #3E4451;
        color: #ABB2BF;
        margin-bottom: 1;
    }
    Input:focus { border: solid #61AFEF; }
    Input.-invalid { border: solid #E06C75; }
    Label {
        color: #ABB2BF;
        height: 1;
    }
    .hint { color: #5C6370; height: 1; margin-bottom: 1; }
    .validation-ok  { color: #98C379; height: 1; }
    .validation-err { color: #E06C75; height: 1; }
    Button { margin: 0 0 1 0; }
    #log-area {
        border: solid #3E4451;
        height: 5;
        background: #1A1B26;
        margin-top: 1;
    }
    TabbedContent { height: auto; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="welcome-panel"):
            yield Static(_LOGO, classes="logo-text")
            yield Static(_TAGLINE, classes="tagline")
            with TabbedContent(initial="login-tab"):
                with TabPane("  Login  ", id="login-tab"):
                    yield from self._login_form()
                with TabPane("  Register  ", id="register-tab"):
                    yield from self._register_form()
            yield RichLog(id="log-area", highlight=True, markup=True)

    # ── Login form ──────────────────────────────────────────────────────────

    def _login_form(self) -> ComposeResult:
        yield Label("Enter your GSTIN to log in:")
        yield Input(
            placeholder="e.g. 27AAPFU0939F1ZV",
            id="login-gstin",
            max_length=15,
        )
        yield Static("", id="login-gstin-status", classes="validation-ok")
        yield Label("Gemini API Key (leave blank to reuse saved key):")
        yield Input(
            placeholder="AIza...",
            id="login-apikey",
            password=True,
        )
        yield Button("  Log In", id="btn-login", classes="btn-ai")

    # ── Registration form ───────────────────────────────────────────────────

    def _register_form(self) -> ComposeResult:
        yield Label("Company Name *")
        yield Input(placeholder="e.g. Eco-Concrete Ltd", id="reg-name")
        yield Label("GSTIN *")
        yield Input(placeholder="27AAPFU0939F1ZV", id="reg-gstin", max_length=15)
        yield Static("", id="reg-gstin-status", classes="validation-ok")
        yield Label("Primary Product / Manufacturing Activity *")
        yield Input(placeholder="e.g. Manufacture of reinforced concrete products", id="reg-product")
        yield Label("City *")
        yield Input(placeholder="e.g. Mumbai", id="reg-city")
        yield Static("", id="reg-city-status", classes="hint")
        yield Label("State")
        yield Input(placeholder="e.g. Maharashtra", id="reg-state")
        yield Label("Contact Email *")
        yield Input(placeholder="contact@company.com", id="reg-email")
        yield Label("Gemini API Key *  (required for AI features)")
        yield Input(placeholder="AIza...", id="reg-apikey", password=True)
        with Horizontal():
            yield Button("  Register & Continue", id="btn-register", classes="btn-buy")
            yield Button("  Clear", id="btn-reg-clear", variant="default")

    # ── Event handlers ──────────────────────────────────────────────────────

    @on(Input.Changed, "#login-gstin")
    def _validate_login_gstin(self, event: Input.Changed) -> None:
        result = GSTINValidator.validate(event.value)
        status = self.query_one("#login-gstin-status", Static)
        if event.value == "":
            status.update("")
        elif result.valid:
            status.update(f"[green]✓ {result.state_name}[/green]")
            status.remove_class("validation-err")
            status.add_class("validation-ok")
        else:
            status.update(f"[red]✗ {result.error}[/red]")
            status.remove_class("validation-ok")
            status.add_class("validation-err")

    @on(Input.Changed, "#reg-gstin")
    def _validate_reg_gstin(self, event: Input.Changed) -> None:
        result = GSTINValidator.validate(event.value)
        status = self.query_one("#reg-gstin-status", Static)
        if event.value == "":
            status.update("")
        elif result.valid:
            status.update(f"[green]✓ Valid — {result.state_name} (State {result.state_code})[/green]")
            status.remove_class("validation-err")
            status.add_class("validation-ok")
        else:
            status.update(f"[red]✗ {result.error}[/red]")
            status.remove_class("validation-ok")
            status.add_class("validation-err")

    @on(Input.Changed, "#reg-city")
    def _validate_city(self, event: Input.Changed) -> None:
        status = self.query_one("#reg-city-status", Static)
        if event.value.strip():
            coords = GeoService.lookup_city(event.value.strip())
            if coords:
                status.update(f"[green]✓ Coordinates found: {coords.lat:.4f}°N, {coords.lon:.4f}°E[/green]")
            else:
                status.update("[yellow]⚠ City not in geo-database — using 0,0 until set[/yellow]")
        else:
            status.update("")

    @on(Button.Pressed, "#btn-login")
    def _handle_login(self) -> None:
        gstin = self.query_one("#login-gstin", Input).value.strip().upper()
        if not GSTINValidator.is_valid(gstin):
            self._log("[red]✗ Invalid GSTIN — cannot log in[/red]")
            return
        company = Database.get_company_by_gstin(gstin)
        if not company:
            self._log("[yellow]⚠ Company not found. Please register first.[/yellow]")
            return
        # Optionally update API key
        apikey = self.query_one("#login-apikey", Input).value.strip()
        if apikey:
            Database.set_api_key(apikey)
        Database.set_current_company_id(company["company_id"])
        self._log(f"[green]✓ Logged in as {company['name']}[/green]")
        self.post_message(self.app.LoginEvent(company_id=company["company_id"]))

    @on(Button.Pressed, "#btn-register")
    def _handle_register(self) -> None:
        name    = self.query_one("#reg-name", Input).value.strip()
        gstin   = self.query_one("#reg-gstin", Input).value.strip().upper()
        product = self.query_one("#reg-product", Input).value.strip()
        city    = self.query_one("#reg-city", Input).value.strip()
        state   = self.query_one("#reg-state", Input).value.strip()
        email   = self.query_one("#reg-email", Input).value.strip()
        apikey  = self.query_one("#reg-apikey", Input).value.strip()

        # Validation
        errors = []
        if not name:
            errors.append("Company name is required")
        if not GSTINValidator.is_valid(gstin):
            errors.append("Invalid GSTIN")
        if not product:
            errors.append("Primary product is required")
        if not city:
            errors.append("City is required")
        if not email or "@" not in email:
            errors.append("Valid email is required")
        if not apikey:
            errors.append("Gemini API key is required for registration")
        if errors:
            self._log("[red]✗ " + " | ".join(errors) + "[/red]")
            return

        # Check for duplicate GSTIN
        existing = Database.get_company_by_gstin(gstin)
        if existing:
            self._log(f"[yellow]⚠ GSTIN already registered as '{existing['name']}'. Please log in.[/yellow]")
            return

        # Resolve geo
        coords = GeoService.lookup_city(city)
        lat = coords.lat if coords else 0.0
        lon = coords.lon if coords else 0.0

        gstin_result = GSTINValidator.validate(gstin)
        company_data = {
            "name": name,
            "gstin": gstin,
            "primary_product": product,
            "address": "",
            "city": city,
            "state": state or gstin_result.state_name,
            "latitude": lat,
            "longitude": lon,
            "contact_email": email,
        }
        company = Database.upsert_company(company_data)
        Database.set_api_key(apikey)
        Database.set_current_company_id(company["company_id"])
        self._log(f"[green]✓ Registered '{name}' successfully! Welcome to CircuLink.[/green]")
        self.post_message(self.app.LoginEvent(company_id=company["company_id"]))

    @on(Button.Pressed, "#btn-reg-clear")
    def _handle_clear(self) -> None:
        for inp_id in ["reg-name", "reg-gstin", "reg-product", "reg-city",
                       "reg-state", "reg-email", "reg-apikey"]:
            self.query_one(f"#{inp_id}", Input).clear()
        for stat_id in ["reg-gstin-status", "reg-city-status"]:
            self.query_one(f"#{stat_id}", Static).update("")
        self._log("[dim]Form cleared.[/dim]")

    def _log(self, msg: str) -> None:
        try:
            log = self.query_one("#log-area", RichLog)
            log.write(msg)
        except Exception:
            pass
