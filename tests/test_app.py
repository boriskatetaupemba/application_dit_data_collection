from __future__ import annotations

import re

from pages_components.pages import _format_file_size
from pages_components.theme import (
    GLOBAL_CSS,
    configure_plotly_theme,
    render_sidebar_footer,
)


class _SidebarRecorder:
    def __init__(self) -> None:
        self.body = ""
        self.unsafe_allow_html = False

    def markdown(self, body: str, *, unsafe_allow_html: bool = False) -> None:
        self.body = body
        self.unsafe_allow_html = unsafe_allow_html


class _StreamlitRecorder:
    def __init__(self) -> None:
        self.sidebar = _SidebarRecorder()


def test_sidebar_footer_contains_exactly_the_three_requested_lines() -> None:
    streamlit = _StreamlitRecorder()

    render_sidebar_footer(streamlit)

    lines = re.findall(r"<div>([^<]+)</div>", streamlit.sidebar.body)
    assert lines == [
        "Projet Examen Data Collection",
        "Développé par Boris KATETA UPEMBA",
        "Master 1 DIT Mars 2026",
    ]
    assert streamlit.sidebar.unsafe_allow_html is True


def test_theme_defines_accessible_focus_and_responsive_breakpoints() -> None:
    assert ":focus-visible" in GLOBAL_CSS
    assert "@media (max-width: 900px)" in GLOBAL_CSS
    assert "@media (max-width: 600px)" in GLOBAL_CSS
    assert "@media (prefers-reduced-motion: reduce)" in GLOBAL_CSS
    assert "grid-template-columns: repeat(4, minmax(0, 1fr))" in GLOBAL_CSS
    assert "display: none" not in GLOBAL_CSS


def test_raw_file_sizes_are_human_readable() -> None:
    assert _format_file_size(48) == "48 o"
    assert _format_file_size(2 * 1024) == "2.0 Kio"
    assert _format_file_size(2 * 1024**2) == "2.0 Mio"


def test_plotly_theme_uses_the_application_palette() -> None:
    import plotly.io as pio

    configure_plotly_theme()

    template = pio.templates["data_collection_lab"]
    assert template.layout.colorway[:3] == ("#0F8F88", "#F2B84B", "#14324F")
    assert "data_collection_lab" in pio.templates.default
