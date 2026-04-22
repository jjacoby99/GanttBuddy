import streamlit as st

from logic.backend.login import render_oidc_login_button

from PIL import Image
from pathlib import Path


def render_login():
    with st.container(horizontal_alignment="center", vertical_alignment="center"):
        with st.container(horizontal=True):
            gb_path = Path(__file__).parent.parent.resolve() / "assets" / "ganttbuddy.png"
            bta_path = Path(__file__).parent.parent.resolve() / "assets" / "bta_logo.png"

            st.image(Image.open(gb_path), width=100)
            st.space("stretch")
            st.image(Image.open(bta_path), width=100)

        with st.container(width="content"):
            st.subheader("Sign in")
            st.caption("Use your organization identity provider to continue.")

            with st.container(horizontal_alignment="center", vertical_alignment="center"):
                render_oidc_login_button()


def render_create_account():
    with st.container(horizontal_alignment="center", vertical_alignment="center"):
        st.title("Create Account")
        st.info("Accounts are now provisioned through your identity provider.")
