import streamlit as st

from logic.backend.sites.fetch_sites import get_sites
from logic.backend.crews.fetch_crews import get_crews
from logic.backend.crews.add_crew import post_crew

from models.site import SiteIn
from models.crew import CrewOut, CrewIn

@st.dialog(f"Add a crew")
def add_crew() -> CrewIn:
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
    
    crews = None
    show_crews = st.checkbox("Show existing crews")
    if show_crews:
        crews = get_crews(headers, site.id)

    if crews:
        view = CrewIn.to_df(crews)
        view = view.rename(
            columns={
                "name": "Crew Name", 
                "members": "Crew Members"
                })
        view = view.drop(columns=["id", "site_id"])

    if crews:
        st.caption(f"{len(crews)} available crews for **{site.name}**")
    else:
        st.caption(f"No crews, *yet*, for **{site.name}**")
    
    if show_crews:
        st.dataframe(
            view,
            hide_index=True,
            height=200,
        )


    
    with st.container(border=True):
        st.caption(f"Create a new crew. Ensure the name differs from the existing crews.")
        with st.container(horizontal=True):
            with st.container():
                new_name = st.text_input(
                    label="Crew Name"
                )

                if crews and (view['Crew Name'] == new_name).any():
                    st.error(f"**{new_name}** is already a crew at **{site.code}**")
                    st.stop()

            st.space("stretch")

            crew_members = st.number_input(
                label="Crew Members",
                min_value=0,
                step=1,
            )

        if st.button(":material/add: Add Crew"):
            if new_name == "":
                st.error(f"The new crew must have a name.")
                st.stop()

            out = CrewOut(
                site_id=str(site.id),
                name=str(new_name),
                members=int(crew_members)
            )
            try:
                crew_in = post_crew(headers=headers, crew=out)
            except ValueError:
                st.error(f"Sorry, we were unable to add the {new_name} crew to {site.name}")
                st.stop()
            st.success(f"{new_name} crew successfully created!")
            st.rerun()



