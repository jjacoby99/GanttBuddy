import streamlit as st

def use_compact_buttons():
    st.markdown("""
        <style>
        /* Make all Streamlit buttons more compact */
        .stButton > button {
            padding: 0.1rem 0.4rem !important;
            min-height: 1.5rem !important;
            height: 1.5rem !important;
            line-height: 1 !important;
        }
        /* Tighten paragraph spacing a bit so text rows match the button height */
        div[data-testid="column"] p {
            margin-bottom: 0.15rem;
        }
        </style>
    """, unsafe_allow_html=True)

use_compact_buttons()