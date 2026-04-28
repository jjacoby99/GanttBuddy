import streamlit as st
from pydantic import ValidationError
from typing import Optional

from models.project_metadata import RelineMetadata

from logic.backend.api_client import fetch_sites, fetch_mills, fetch_site

def render_reline_metadata_inputs(
    existing: Optional[RelineMetadata] = None,
    *,
    template_version: Optional[str] = None,
    title: str = "Project Setup (Mill Reline)",
    require_submit: bool = True,
    state_key: str = "reline_metadata",
    key_prefix: str = "reline_metadata",
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

    headers = st.session_state.get("auth_headers", {})
    try:
        sites = fetch_sites(headers)
    except Exception as exc:
        st.error(f"Failed to load sites: {exc}")
        return existing

    site_ids = {site.get("id"): site.get("name") for site in sites}
    options = list(site_ids.keys())
    if not options:
        st.warning("No sites are available yet. Create a site in the backend before configuring mill reline inputs.")
        return existing

    selected_site_index = 0
    if ex.site_id in options:
        selected_site_index = options.index(ex.site_id)

    c1, c2 = st.columns(2)
    with c1:
        selected_site_id = st.selectbox(
            "Site",
            options=options,
            index=selected_site_index,
            format_func=lambda s: site_ids[s],
            key=f"{key_prefix}_site_id",
        )

        vendor_options = ["Metso", "Other"]
        vendor_index = vendor_options.index(ex.vendor) if ex.vendor in vendor_options else 0
        vendor = st.selectbox(
            "Vendor",
            options=vendor_options,
            index=vendor_index,
            key=f"{key_prefix}_vendor",
        )
    
        campaign_id = st.text_input(
            "Campaign ID", 
            value=_s(ex.campaign_id), 
            placeholder="2026_C1",
            key=f"{key_prefix}_campaign_id",
        )
        liner_options = ["polymet", "steel", "rubber"] 
        liner_index = liner_options.index(ex.liner_type) if ex.liner_type in liner_options else 0
        liner_type = st.selectbox(
            "Liner Type",
            options=liner_options,
            index=liner_index,
            key=f"{key_prefix}_liner_type",
        )

    with c2:
        try:
            mills = fetch_mills(headers, site_id=selected_site_id)
        except Exception as exc:
            st.error(f"Failed to load mills: {exc}")
            return existing

        mill_ids = {mill["id"]: mill["name"] for mill in mills}
        mill_options = list(mill_ids.keys())
        if not mill_options:
            st.warning("No mills are available for the selected site.")
            return existing

        selected_mill_index = 0
        if ex.mill_id in mill_options:
            selected_mill_index = mill_options.index(ex.mill_id)
        selected_mill_id = st.selectbox(
            "Select Mill", 
            options=mill_options,
            format_func=lambda m: mill_ids[m],
            index=selected_mill_index,
            key=f"{key_prefix}_mill_id",
        )

        liner_system_options = ["Megaliner", "Generic"]
        liner_system_index = (
            liner_system_options.index(ex.liner_system)
            if ex.liner_system in liner_system_options
            else 0
        )
        liner_system = st.selectbox(
            "Liner System",
            options=liner_system_options,
            index=liner_system_index,
            key=f"{key_prefix}_liner_system",
        )

        scope_options = ["", "Full", "Partial", "Other"]
        scope_index = scope_options.index(ex.scope) if ex.scope in scope_options else 0
        scope = st.selectbox(
            "Scope", 
            options=scope_options, 
            index=scope_index,
            key=f"{key_prefix}_scope",
        )
        

    st.divider()

    supervisor = st.text_input("Supervisor", value=_s(ex.supervisor), key=f"{key_prefix}_supervisor")

    notes = st.text_area("Notes", value=_s(ex.notes), height=90, key=f"{key_prefix}_notes")

    submitted = st.button("Save Setup", width="stretch") if require_submit else True

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
        "supervisor": supervisor.strip() or "Unnamed",
        "notes": notes.strip() or "",
    }


    try:
        model = RelineMetadata(**payload)
        # Optional: show a small success marker only when submitted
        if require_submit:
            st.success("Reline setup information saved")
            st.session_state[state_key] = model
            st.session_state["reline_dialog_open"] = False
            st.rerun()
        return model
    except ValidationError as e:
        # Make errors readable in UI
        st.error("Fix the highlighted issues and save again.")
        for err in e.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            st.caption(f"- {loc}: {msg}")
        if require_submit:
            st.session_state[state_key] = None
            st.session_state["reline_dialog_open"] = False
            st.rerun()
        return None


@st.dialog("Mill Reline Setup Information")
def render_reline_metadata_form(
    existing: Optional[RelineMetadata] = None,
    *,
    template_version: Optional[str] = None,
    title: str = "Project Setup (Mill Reline)",
    require_submit: bool = True,
    state_key: str = "reline_metadata",
    key_prefix: str = "reline_metadata",
) -> Optional[RelineMetadata]:
    return render_reline_metadata_inputs(
        existing=existing,
        template_version=template_version,
        title=title,
        require_submit=require_submit,
        state_key=state_key,
        key_prefix=key_prefix,
    )
