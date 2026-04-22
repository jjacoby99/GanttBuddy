import streamlit as st
from zoneinfo import ZoneInfo

from models.project import Project
from models.project_access import ProjectAccess
from logic.backend.sites.fetch_sites import get_sites
from models.site import SiteIn
from models.project_type import ProjectType, project_type_to_dict

@st.dialog(":material/add: Create a project")
def create_project():
    project_name = st.text_input(
        f"Project name",
        placeholder="Super awesome project"
    )

    if not project_name:
        st.info("Enter a valid name for your project.")
        st.stop()
    
    project_description = st.text_area(
        label=f"Describe your project. This may be useful to recall later",
        placeholder="Constructing the death star..."
    )
    project_type_dict = project_type_to_dict()
    project_type_str = st.pills(
        label="Select Project Type",
        options=project_type_dict.keys(),
        help="Characterize what's going on in your project. If unsure, use Generic"
    )
    
    try:
        project_type = project_type_dict[project_type_str]
    except Exception:
        project_type = ProjectType.GENERIC

    new_project = Project(
        name=project_name,
        description=project_description,
        project_type=project_type
    )

    specify_site = st.checkbox(
        label=f"Specify Project Site?",
        value=False
    )

    selected_site = None
    if specify_site:
        sites = get_sites(headers=st.session_state.get("auth_headers", {}))
        sites_by_id = SiteIn.by_id(sites)
        
        if not sites:
            st.info(":material/info: No sites available. Create some if you want!")
            st.stop()
        
        selected_site_id = st.selectbox(
            label="Site",
            options=list(sites_by_id.keys()),
            format_func=lambda id: sites_by_id[id].name,
            help="Select the site where the project takes place."
        )

        if selected_site_id:
            selected_site = sites_by_id[selected_site_id]
            st.info(f":material/info: {selected_site.name} specified. Timezone: {selected_site.timezone}")

            new_project = Project(
                name=project_name,
                project_type=project_type,
                description=project_description,
                site_id=selected_site_id,
                timezone=ZoneInfo(selected_site.timezone),
            )
    
    
    if st.button("Create", icon=":material/add:", type='primary'):
        st.session_state.session.project = new_project
        st.session_state["project_access"] = ProjectAccess(
            project_id=new_project.uuid,
            can_view=True,
            can_edit=True,
            can_manage_members=True,
            source="local_project",
        )
        st.info(f"✅ New project created!")
        st.rerun()
        return
