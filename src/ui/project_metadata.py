import streamlit as st
from pydantic import ValidationError
from typing import Optional

from models.project_metadata import RelineMetadata
from models.mill import HVC_MILLS

import streamlit as st
from pydantic import ValidationError
from typing import Optional

from logic.backend.api_client import fetch_sites, fetch_mills, fetch_site

@st.dialog("Mill Reline Setup Information")
def render_reline_metadata_form(
    existing: Optional[RelineMetadata] = None,
    *,
    template_version: Optional[str] = None,
    title: str = "Project Setup (Mill Reline)",
    require_submit: bool = True,
) -> Optional[RelineMetadata]:

    st.subheader(title)

    ex = existing or RelineMetadata(
        site_id="",
        site_name="",
        mill_id="",
        mill_name="",
        vendor="",
        liner_system="",
    )

    def _s(x: Optional[str]) -> str:
        return x or ""

    if template_version:
        st.caption(f"Template version: {template_version}")

    c1, c2 = st.columns(2)
    with c1:
        headers = st.session_state.get("auth_headers", {})
        sites = fetch_sites(headers)
        site_ids = {site.get("id"): site.get("name") for site in sites }
        options = list(site_ids.keys())
        selected_site_id = st.selectbox(
            "Site",
            options=options,
            index=options.index(existing.site_id) if existing else 0,
            format_func=lambda s: site_ids[s],
        )

        vendor_options = ["Metso", "Other"]
        vendor = st.selectbox(
            "Vendor",
            options=vendor_options,
            index=vendor_options.index(existing.vendor) if existing else 0
        )
    
        campaign_id = st.text_input(
            "Campaign ID", 
            value=_s(ex.campaign_id), 
            placeholder="2026_C1"
        )
        liner_options = ["polymet", "steel", "rubber"] 
        liner_type = st.selectbox(
            "Liner Type",
            options=liner_options,
            index=liner_options.index(existing) if existing else 0
        )

    with c2:
        mills = fetch_mills(headers, site_id=selected_site_id)
        mill_ids = {mill["id"]: mill["name"] for mill in mills}
        mill_options = list(mill_ids.keys())
        selected_mill_id = st.selectbox(
            "Select Mill", 
            options=mill_options,
            format_func=lambda m: mill_ids[m],
            index=mill_options.index(existing.mill_id) if existing else 0
        )

        liner_system = st.selectbox(
            "Liner System",
            options=["Megaliner"]
        )

        scope_options = ["", "Full", "Partial", "Other"]
        scope = st.selectbox(
            "Scope", 
            options=scope_options, 
            index=scope_options.index(existing.scope) if existing else 0
        )
        

    st.divider()

    c4, c5, c6 = st.columns(3)
    with c4:
        crew_count_day = st.number_input(
            "Crew Count (Day)",
            min_value=0,
            step=1,
            value=int(ex.crew_count_day or 5),
        )

    with c5:
        crew_count_night = st.number_input(
            "Crew Count (Night)",
            min_value=0,
            step=1,
            value=int(ex.crew_count_night or 5),
        )

    with c6:
        supervisor = st.text_input("Supervisor", value=_s(ex.supervisor))

    notes = st.text_area("Notes", value=_s(ex.notes), height=90)

    submitted = st.button("Save Setup", use_container_width=True) if require_submit else True

    # If we require submit, only validate/return after click
    if require_submit and not submitted:
        return None

    # Normalize blanks to None for optional strings
    payload = {
        "site_id": selected_site_id,
        "site_name": site_ids[selected_site_id],
        "mill_id": selected_mill_id,
        "mill_name": mill_ids[selected_mill_id],
        "vendor": vendor,
        "liner_system": liner_system,
        "campaign_id": campaign_id.strip() or None,
        "scope": scope or None,
        "liner_type": liner_type or None,
        "template_version": template_version or getattr(ex, "template_version", None),
        "crew_count_day": crew_count_day,
        "crew_count_night": crew_count_night,
        "supervisor": supervisor.strip() or "Unnamed",
        "notes": notes.strip() or "",
    }


    try:
        model = RelineMetadata(**payload)
        # Optional: show a small success marker only when submitted
        if require_submit:
            st.success("Reline setup information saved")
            st.session_state["reline_metadata"] = model
            st.session_state["reline_dialog_open"] = False
            st.rerun()
    except ValidationError as e:
        # Make errors readable in UI
        st.error("Fix the highlighted issues and save again.")
        for err in e.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            st.caption(f"- {loc}: {msg}")
        st.session_state["reline_metadata"] = None
        st.session_state["reline_dialog_open"] = False
        st.rerun()