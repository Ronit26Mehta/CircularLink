"""
Modal Dialogs
=============
Reusable modal screens:

  MessageModal    — informational / error message
  ConfirmModal    — yes/no confirmation
  AddProductModal — add a new product listing
  SearchModal     — search/find materials (buyer flow)
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea


# ---------------------------------------------------------------------------
# MessageModal
# ---------------------------------------------------------------------------

class MessageModal(ModalScreen[None]):
    """Display a simple message and an OK button."""

    CSS = """
    MessageModal { align: center middle; }
    #modal-panel {
        background: #24253A;
        border: solid #3E4451;
        width: 70;
        height: auto;
        padding: 2 3;
        min-height: 10;
    }
    #modal-title { color: #61AFEF; text-style: bold; height: 2; }
    #modal-body  { color: #ABB2BF; height: auto; min-height: 3; }
    Button { margin-top: 1; }
    """

    def __init__(self, title: str, message: str, level: str = "info") -> None:
        super().__init__()
        self._title = title
        self._message = message
        # level: info | success | warning | error
        self._level = level

    def compose(self) -> ComposeResult:
        colour = {"info": "#61AFEF", "success": "#98C379",
                  "warning": "#D19A66", "error": "#E06C75"}.get(self._level, "#61AFEF")
        with Container(id="modal-panel"):
            yield Static(f"[bold {colour}]{self._title}[/bold {colour}]", id="modal-title")
            yield Static(self._message, id="modal-body", markup=True)
            yield Button("  OK", id="btn-ok", classes="btn-ai")

    @on(Button.Pressed, "#btn-ok")
    def _close(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# ConfirmModal
# ---------------------------------------------------------------------------

class ConfirmModal(ModalScreen[bool]):
    """Yes/No confirmation dialog. Dismisses with True (yes) or False (no)."""

    CSS = """
    ConfirmModal { align: center middle; }
    #modal-panel {
        background: #24253A;
        border: solid #D19A66;
        width: 70;
        height: auto;
        padding: 2 3;
        min-height: 10;
    }
    #modal-title { color: #D19A66; text-style: bold; height: 2; }
    #modal-body  { color: #ABB2BF; height: auto; min-height: 3; }
    #btn-row     { height: 3; margin-top: 1; }
    """

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        with Container(id="modal-panel"):
            yield Static(f"[bold yellow]{self._title}[/bold yellow]", id="modal-title")
            yield Static(self._message, id="modal-body", markup=True)
            with Horizontal(id="btn-row"):
                yield Button("  Yes", id="btn-yes", classes="btn-sell")
                yield Button("  No", id="btn-no", variant="default")

    @on(Button.Pressed, "#btn-yes")
    def _yes(self) -> None: self.dismiss(True)

    @on(Button.Pressed, "#btn-no")
    def _no(self) -> None: self.dismiss(False)


# ---------------------------------------------------------------------------
# AddProductModal
# ---------------------------------------------------------------------------

class AddProductModal(ModalScreen[dict | None]):
    """
    Form to add a new product/byproduct listing.
    Dismisses with a product dict, or None if cancelled.
    """

    CSS = """
    AddProductModal { align: center middle; }
    #modal-panel {
        background: #24253A;
        border: solid #E06C75;
        width: 80;
        height: auto;
        padding: 2 3;
        min-height: 28;
    }
    #modal-title { color: #E06C75; text-style: bold; height: 2; }
    Label { color: #ABB2BF; height: 1; }
    Input {
        background: #1E1F2E;
        border: solid #3E4451;
        color: #ABB2BF;
        margin-bottom: 1;
    }
    Input:focus { border: solid #61AFEF; }
    #desc-area {
        background: #1E1F2E;
        border: solid #3E4451;
        color: #ABB2BF;
        height: 5;
        margin-bottom: 1;
    }
    #btn-row { height: 3; margin-top: 1; }
    .hint { color: #5C6370; height: 1; margin-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="modal-panel"):
            yield Static("[bold red]  Add Product / Byproduct Listing[/bold red]", id="modal-title")
            yield Label("Product / Material Name *")
            yield Input(placeholder="e.g. Fly Ash, Steel Scrap, Spent Catalyst", id="p-name")
            yield Label("Description *")
            yield TextArea(id="p-desc")
            with Horizontal():
                with Vertical():
                    yield Label("Quantity")
                    yield Input(placeholder="100", id="p-qty", type="number")
                with Vertical():
                    yield Label("Unit")
                    yield Input(placeholder="tonnes / kg / litres", id="p-unit")
            yield Label("City (overrides company default)")
            yield Input(placeholder="Leave blank to use company city", id="p-city")
            yield Static(
                "[dim]The system will auto-run hazard screening before listing.[/dim]",
                classes="hint",
            )
            with Horizontal(id="btn-row"):
                yield Button("  Submit for Review", id="btn-submit", classes="btn-sell")
                yield Button("  Cancel", id="btn-cancel", variant="default")

    @on(Button.Pressed, "#btn-submit")
    def _submit(self) -> None:
        name = self.query_one("#p-name", Input).value.strip()
        desc = self.query_one("#p-desc", TextArea).text.strip()
        qty_str = self.query_one("#p-qty", Input).value.strip()
        unit = self.query_one("#p-unit", Input).value.strip()
        city_override = self.query_one("#p-city", Input).value.strip()
        if not name:
            return  # Silently ignore — user hasn't filled form
        try:
            qty = float(qty_str) if qty_str else 0.0
        except ValueError:
            qty = 0.0
        self.dismiss(
            {
                "name": name,
                "description": desc,
                "quantity": qty,
                "unit": unit,
                "city_override": city_override,
            }
        )

    @on(Button.Pressed, "#btn-cancel")
    def _cancel(self) -> None:
        self.dismiss(None)


# ---------------------------------------------------------------------------
# SearchModal
# ---------------------------------------------------------------------------

class SearchModal(ModalScreen[str | None]):
    """
    Buyer search dialog.
    Dismisses with a search query string, or None if cancelled.
    """

    CSS = """
    SearchModal { align: center middle; }
    #modal-panel {
        background: #24253A;
        border: solid #98C379;
        width: 70;
        height: auto;
        padding: 2 3;
        min-height: 14;
    }
    #modal-title { color: #98C379; text-style: bold; height: 2; }
    Label { color: #ABB2BF; height: 1; }
    Input {
        background: #1E1F2E;
        border: solid #3E4451;
        color: #ABB2BF;
        margin-bottom: 1;
    }
    Input:focus { border: solid #98C379; }
    #btn-row { height: 3; margin-top: 1; }
    .hint { color: #5C6370; height: 1; margin-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="modal-panel"):
            yield Static("[bold green]  Search for Materials[/bold green]", id="modal-title")
            yield Label("What material are you looking for?")
            yield Input(
                placeholder="e.g. fly ash, copper scrap, waste oil, spent catalyst",
                id="search-query",
            )
            yield Static(
                "[dim]Gemini AI will expand your query with synonyms for better matching.[/dim]",
                classes="hint",
            )
            with Horizontal(id="btn-row"):
                yield Button("  Search", id="btn-search", classes="btn-buy")
                yield Button("  Cancel", id="btn-cancel", variant="default")

    def on_mount(self) -> None:
        self.query_one("#search-query", Input).focus()

    @on(Button.Pressed, "#btn-search")
    def _search(self) -> None:
        query = self.query_one("#search-query", Input).value.strip()
        if query:
            self.dismiss(query)

    @on(Input.Submitted, "#search-query")
    def _search_on_enter(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.dismiss(query)

    @on(Button.Pressed, "#btn-cancel")
    def _cancel(self) -> None:
        self.dismiss(None)
