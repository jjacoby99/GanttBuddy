import streamlit as st

from logic.backend.sites.fetch_sites import get_sites
from logic.backend.crews.fetch_crews import get_crews

from models.site import SiteIn
from models.crew import CrewIn

@st.dialog(f"Add a crew")
def add_crew() -> None:
    headers = st.session_state.get("auth_headers", {})
    
    sites = get_sites(headers)
    
    if not sites:
        st.error("No Sites available. Create some to add crews.")
        return 
    
    site = st.selectbox(
        label="Site",
        options=sites,
        format_func=lambda s: s.name
    )

    if not site:
        return
    
    crews = get_crews(headers, site.id)

    st.captions(f"Available crews for **{site.name}**")
    st.table(CrewIn.to_df(crews))

    with st.form("New Crew"):
        pass


