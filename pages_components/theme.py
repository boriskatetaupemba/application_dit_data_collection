"""Visual identity and small presentational helpers for Streamlit pages."""

from __future__ import annotations

from html import escape
from typing import Any, Iterable


GLOBAL_CSS = """
<style>
    :root {
        --dc-ink: #10243e;
        --dc-navy: #0b1f33;
        --dc-navy-soft: #14324f;
        --dc-teal: #0f8f88;
        --dc-teal-light: #dff7f4;
        --dc-amber: #f2b84b;
        --dc-canvas: #f6f9fc;
        --dc-surface: #ffffff;
        --dc-muted: #61758a;
        --dc-border: #dce6ef;
        --dc-shadow: 0 12px 32px rgba(16, 36, 62, 0.08);
        --dc-radius: 18px;
    }

    .stApp {
        background:
            radial-gradient(circle at 92% 4%, rgba(15, 143, 136, 0.09), transparent 25rem),
            linear-gradient(180deg, #fbfdff 0%, var(--dc-canvas) 100%);
        color: var(--dc-ink);
    }

    header[data-testid="stHeader"] {
        background: rgba(246, 249, 252, 0.82);
        backdrop-filter: blur(12px);
    }

    [data-testid="stMainBlockContainer"] {
        max-width: 1420px;
        padding-top: 2.4rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        color: var(--dc-ink);
        letter-spacing: -0.025em;
    }

    h1 {
        font-weight: 760 !important;
        line-height: 1.08 !important;
        margin-top: 0.15rem !important;
    }

    h2, h3 {
        font-weight: 700 !important;
    }

    .dc-page-kicker {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--dc-teal);
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 0.13em;
        text-transform: uppercase;
        margin-bottom: 0.1rem;
    }

    .dc-page-kicker::before {
        content: "";
        width: 1.65rem;
        height: 3px;
        border-radius: 99px;
        background: linear-gradient(90deg, var(--dc-amber), var(--dc-teal));
    }

    .dc-page-intro {
        max-width: 780px;
        color: var(--dc-muted);
        font-size: 1.02rem;
        line-height: 1.7;
        margin: -0.35rem 0 1.55rem;
    }

    .dc-brand {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        padding: 0.45rem 0.15rem 1.15rem;
    }

    .dc-brand-mark {
        display: grid;
        place-items: center;
        width: 2.75rem;
        height: 2.75rem;
        flex: 0 0 2.75rem;
        border-radius: 14px;
        color: #082738;
        background: linear-gradient(145deg, #70e2d8, var(--dc-amber));
        box-shadow: 0 8px 22px rgba(4, 16, 29, 0.26);
        font-weight: 900;
        letter-spacing: -0.06em;
    }

    .dc-brand-name {
        color: #ffffff;
        font-size: 0.92rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        line-height: 1.2;
    }

    .dc-brand-subtitle {
        color: #9eb4c8;
        font-size: 0.75rem;
        margin-top: 0.2rem;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--dc-navy) 0%, #071725 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    section[data-testid="stSidebar"] > div {
        background: transparent;
    }

    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #d7e3ee;
    }

    section[data-testid="stSidebar"] [data-testid="stRadio"] > label p {
        color: #91a9be;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 0.25rem;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        padding: 0.57rem 0.7rem;
        border: 1px solid transparent;
        border-radius: 11px;
        transition: background 150ms ease, border-color 150ms ease, transform 150ms ease;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.07);
        transform: translateX(2px);
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: rgba(53, 199, 188, 0.15);
        border-color: rgba(112, 226, 216, 0.32);
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label p {
        color: #eaf2f8;
        font-weight: 600;
    }

    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.12);
    }

    .dc-sidebar-footer {
        color: #b8cad9;
        font-size: 0.69rem;
        line-height: 1.65;
        padding: 0.85rem 0.05rem 0.15rem;
        margin-top: 1.35rem;
        border-top: 1px solid rgba(255, 255, 255, 0.11);
    }

    .dc-sidebar-footer div {
        white-space: nowrap;
    }

    .dc-sidebar-footer div:nth-child(2) {
        color: #ffffff;
        font-weight: 650;
    }

    [data-testid="stMetric"] {
        min-height: 116px;
        padding: 1rem 1.1rem;
        border: 1px solid var(--dc-border);
        border-top: 3px solid var(--dc-teal);
        border-radius: 15px;
        background: rgba(255, 255, 255, 0.88);
        box-shadow: 0 7px 22px rgba(16, 36, 62, 0.055);
    }

    [data-testid="stMetricLabel"] p {
        color: var(--dc-muted);
        font-weight: 650;
    }

    [data-testid="stMetricValue"] {
        color: var(--dc-ink);
        font-weight: 760;
    }

    [data-testid="stAlert"] {
        border-radius: 14px;
        border-width: 1px;
        box-shadow: 0 5px 18px rgba(16, 36, 62, 0.04);
    }

    [data-testid="stExpander"] {
        border-color: var(--dc-border);
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.72);
    }

    .stButton > button,
    .stDownloadButton > button,
    .stLinkButton > a {
        min-height: 2.8rem;
        border-radius: 11px;
        font-weight: 700;
        transition: transform 150ms ease, box-shadow 150ms ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stLinkButton > a:hover {
        transform: translateY(-1px);
        box-shadow: 0 8px 22px rgba(15, 143, 136, 0.16);
    }

    button[kind="primary"] {
        border: 0 !important;
        background: linear-gradient(110deg, var(--dc-teal), #08716c) !important;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--dc-border);
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 8px 24px rgba(16, 36, 62, 0.055);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.4rem;
        border-bottom: 1px solid var(--dc-border);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        font-weight: 650;
    }

    .dc-callout {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 0.9rem;
        align-items: start;
        padding: 1rem 1.1rem;
        margin: 0.25rem 0 1.25rem;
        border: 1px solid #bce4df;
        border-radius: 14px;
        background: linear-gradient(115deg, #effbf9, #ffffff);
    }

    .dc-raw-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.38rem 0.65rem;
        margin: -0.35rem 0 1rem;
        border: 1px solid #f0c89a;
        border-radius: 999px;
        color: #92400e;
        background: #fff7ed;
        font-size: 0.74rem;
        font-weight: 850;
        letter-spacing: 0.06em;
    }

    .dc-raw-badge::before {
        content: "";
        width: 0.48rem;
        height: 0.48rem;
        border-radius: 50%;
        background: #d97706;
        box-shadow: 0 0 0 4px rgba(217, 119, 6, 0.12);
    }

    .dc-callout-mark {
        display: grid;
        place-items: center;
        width: 2rem;
        height: 2rem;
        border-radius: 9px;
        background: var(--dc-teal-light);
        color: var(--dc-teal);
        font-weight: 900;
    }

    .dc-callout strong {
        display: block;
        color: var(--dc-ink);
        margin-bottom: 0.2rem;
    }

    .dc-callout p {
        color: var(--dc-muted);
        line-height: 1.55;
        margin: 0;
    }

    .dc-step-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.85rem;
        margin: 0.45rem 0 1.25rem;
    }

    .dc-step-card {
        position: relative;
        min-height: 150px;
        padding: 1rem;
        border: 1px solid var(--dc-border);
        border-radius: 15px;
        background: rgba(255, 255, 255, 0.88);
        box-shadow: 0 7px 22px rgba(16, 36, 62, 0.045);
    }

    .dc-step-number {
        display: grid;
        place-items: center;
        width: 2rem;
        height: 2rem;
        margin-bottom: 0.75rem;
        border-radius: 50%;
        color: #ffffff;
        background: var(--dc-navy-soft);
        font-size: 0.78rem;
        font-weight: 850;
    }

    .dc-step-card strong {
        display: block;
        color: var(--dc-ink);
        margin-bottom: 0.35rem;
    }

    .dc-step-card p {
        color: var(--dc-muted);
        font-size: 0.88rem;
        line-height: 1.55;
        margin: 0;
    }

    .dc-empty-state {
        text-align: center;
        padding: 2.3rem 1.25rem;
        margin: 0.6rem 0 1rem;
        border: 1px dashed #a9c4d8;
        border-radius: var(--dc-radius);
        background:
            radial-gradient(circle at 50% 15%, rgba(15, 143, 136, 0.10), transparent 12rem),
            rgba(255, 255, 255, 0.72);
    }

    .dc-empty-icon {
        display: grid;
        place-items: center;
        width: 3.4rem;
        height: 3.4rem;
        margin: 0 auto 0.9rem;
        border: 1px solid #bce4df;
        border-radius: 17px;
        color: var(--dc-teal);
        background: #ecfaf8;
        font-size: 1.45rem;
        font-weight: 900;
        box-shadow: 0 8px 22px rgba(15, 143, 136, 0.10);
    }

    .dc-empty-state h3 {
        margin: 0 0 0.35rem;
        font-size: 1.15rem;
    }

    .dc-empty-state p {
        max-width: 620px;
        margin: 0 auto;
        color: var(--dc-muted);
        line-height: 1.6;
    }

    .dc-empty-state code {
        color: #075e5a;
        background: var(--dc-teal-light);
        border-radius: 6px;
        padding: 0.12rem 0.34rem;
    }

    .dc-file-summary {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin: 0.35rem 0 1rem;
    }

    .dc-pill {
        display: inline-flex;
        align-items: center;
        padding: 0.35rem 0.65rem;
        border: 1px solid var(--dc-border);
        border-radius: 999px;
        color: var(--dc-muted);
        background: #ffffff;
        font-size: 0.78rem;
        font-weight: 650;
    }

    :where(button, a, input, [tabindex]):focus-visible {
        outline: 3px solid rgba(242, 184, 75, 0.75) !important;
        outline-offset: 2px !important;
    }

    @media (max-width: 1100px) {
        .dc-step-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 900px) {
        [data-testid="stMainBlockContainer"] {
            padding-left: 1.1rem;
            padding-right: 1.1rem;
            /* Leave room for Streamlit's fixed mobile toolbar. */
            padding-top: 3.8rem;
        }

        .dc-step-card {
            min-height: auto;
        }
    }

    @media (max-width: 600px) {
        .dc-step-grid {
            grid-template-columns: 1fr;
        }

        .dc-page-intro {
            font-size: 0.95rem;
        }

        .dc-empty-state {
            padding: 1.7rem 0.85rem;
        }

        [data-testid="stMetric"] {
            min-height: 100px;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            scroll-behavior: auto !important;
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
        }
    }
</style>
"""


def inject_global_theme(st: Any) -> None:
    """Inject the application-wide code-native identity once per script run."""

    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def configure_plotly_theme() -> None:
    """Apply the same identity to every Plotly figure created by the app."""

    try:
        import plotly.graph_objects as go
        import plotly.io as pio
    except ImportError:  # The dashboard already reports missing optional extras.
        return

    template_name = "data_collection_lab"
    if template_name not in pio.templates:
        pio.templates[template_name] = go.layout.Template(
            layout=go.Layout(
                colorway=(
                    "#0F8F88",
                    "#F2B84B",
                    "#14324F",
                    "#56B4AE",
                    "#C86B3C",
                    "#758CA3",
                    "#7C6BAE",
                ),
                font={
                    "family": "Inter, Aptos, Segoe UI, sans-serif",
                    "color": "#10243E",
                },
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#FFFFFF",
                title={"font": {"color": "#10243E", "size": 18}},
                legend={"title": {"font": {"color": "#61758A"}}},
                hoverlabel={"bgcolor": "#0B1F33", "font": {"color": "#FFFFFF"}},
            )
        )
    pio.templates.default = f"plotly_white+{template_name}"


def render_sidebar_brand(st: Any) -> None:
    st.sidebar.markdown(
        """
        <div class="dc-brand">
            <div class="dc-brand-mark" aria-hidden="true">DC</div>
            <div>
                <div class="dc-brand-name">DATA COLLECTION</div>
                <div class="dc-brand-subtitle">Books · Gaaraas · Insights</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_footer(st: Any) -> None:
    """Render the three attribution lines requested by the project owner."""

    st.sidebar.markdown(
        """
        <div class="dc-sidebar-footer">
            <div>Projet Examen Data Collection</div>
            <div>Développé par Boris KATETA UPEMBA</div>
            <div>Master 1 DIT Mars 2026</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(st: Any, *, kicker: str, title: str, intro: str) -> None:
    """Render a consistent, accessible page heading."""

    st.markdown(
        f'<div class="dc-page-kicker">{escape(kicker)}</div>',
        unsafe_allow_html=True,
    )
    st.title(title)
    st.markdown(
        f'<p class="dc-page-intro">{escape(intro)}</p>',
        unsafe_allow_html=True,
    )


def render_callout(st: Any, *, title: str, text: str, mark: str = "i") -> None:
    st.markdown(
        f"""
        <div class="dc-callout">
            <div class="dc-callout-mark" aria-hidden="true">{escape(mark)}</div>
            <div><strong>{escape(title)}</strong><p>{escape(text)}</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_raw_badge(st: Any) -> None:
    st.markdown(
        '<div class="dc-raw-badge">BRUT · NON TRANSFORMÉ</div>',
        unsafe_allow_html=True,
    )


def render_step_cards(
    st: Any,
    steps: Iterable[tuple[str, str]],
) -> None:
    cards = []
    for index, (title, text) in enumerate(steps, start=1):
        cards.append(
            '<div class="dc-step-card">'
            f'<div class="dc-step-number">{index:02d}</div>'
            f"<strong>{escape(title)}</strong><p>{escape(text)}</p>"
            "</div>"
        )
    st.markdown(
        '<div class="dc-step-grid">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


def render_empty_state(st: Any, *, title: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="dc-empty-state">
            <div class="dc-empty-icon" aria-hidden="true">↓</div>
            <h3>{escape(title)}</h3>
            <p>{escape(text)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_file_summary(st: Any, items: Iterable[str]) -> None:
    pills = "".join(f'<span class="dc-pill">{escape(item)}</span>' for item in items)
    st.markdown(
        f'<div class="dc-file-summary">{pills}</div>',
        unsafe_allow_html=True,
    )
