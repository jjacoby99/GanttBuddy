import streamlit as st

from logic.backend.login import render_oidc_login_button
from ui.utils.page_header import render_registered_page_header

from PIL import Image
from pathlib import Path

def render_login():
    render_registered_page_header("login", chips=["Organization SSO"])
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
            login_message = st.session_state.pop("login_message", None)
            if login_message:
                st.info(login_message)

            with st.container(horizontal_alignment="center", vertical_alignment="center"):
                render_oidc_login_button()

  

def render_create_account():
    
    with st.container(horizontal_alignment="center", vertical_alignment="center"):
        st.title("Create Account")
        
        with st.form("create_account_form", width="content"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")

            with st.container(horizontal=True):
                
                if st.form_submit_button(":material/person_add: Create Account"):
                    if password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        # Here you would add logic to create the account
                        st.success("Account created successfully! Please log in.")

                st.space("stretch")

if __name__ == "__main__":
    render_login()
