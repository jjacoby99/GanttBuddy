from __future__ import annotations

import streamlit as st
from typing import Sequence, TypeVar

T = TypeVar("T")


_SEGMENTED_CSS = """
<style>
/* Make radio options lay out horizontally with spacing */
div[data-testid="stRadio"] > div[role="radiogroup"],
div.row-widget.stRadio > div[role="radiogroup"] {
  flex-direction: row;
  gap: 0.5rem;
}

/* Each option looks like a pill button */
div[data-testid="stRadio"] label[data-baseweb="radio"],
div.row-widget.stRadio label[data-baseweb="radio"] {
  border: 1px solid rgba(49, 51, 63, 0.20);
  border-radius: 999px;
  padding: 0.35rem 0.75rem;
  margin: 0;
}

/* Hide the default radio circle */
div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child,
div.row-widget.stRadio label[data-baseweb="radio"] > div:first-child {
  display: none;
}

/* Tighten label spacing */
div[data-testid="stRadio"] label[data-baseweb="radio"] > div:last-child,
div.row-widget.stRadio label[data-baseweb="radio"] > div:last-child {
  padding: 0;
}

/*
Selected state:
Streamlit/BaseWeb nests an <input type="radio"> then a sibling <div> that holds the label.
This selector is a common working pattern.
*/
div[data-testid="stRadio"] label[data-baseweb="radio"] input[type="radio"]:checked + div,
div.row-widget.stRadio label[data-baseweb="radio"] input[type="radio"]:checked + div {
  background: var(--primary-color, #249ded) !important;
  color: white !important;
  border-radius: 999px;
  padding: 0.35rem 0.75rem;
}

/* Optional: make pills a bit more “buttony” on hover */
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover,
div.row-widget.stRadio label[data-baseweb="radio"]:hover {
  border-color: rgba(49, 51, 63, 0.35);
}
</style>
"""


def _inject_css_once() -> None:
    # Avoid injecting the same <style> block many times per rerun.
    # if st.session_state.get("_segmented_css_injected"):
    #     return
    st.markdown(_SEGMENTED_CSS, unsafe_allow_html=True)
    # st.session_state["_segmented_css_injected"] = True


def segmented_radio(
    options: Sequence[T],
    *,
    key: str,
    label: str = "",
    default: T | None = None,
) -> T:
    """
    A pill-styled, horizontal radio that behaves like tabs.

    Notes:
    - CSS is a hack: Streamlit DOM can change across versions.
    - You must pass a stable, unique key.
    """
    _inject_css_once()

    # Only apply "index" on first render; afterwards Streamlit state wins.
    index = 0
    if default is not None and default in options:
        index = list(options).index(default)

    if key in st.session_state:
        index = None  # don't fight Streamlit state

    return st.radio(
        label if label else " ",
        options,
        horizontal=True,
        key=key,
        index=index,
        label_visibility="collapsed" if not label else "visible",
    )