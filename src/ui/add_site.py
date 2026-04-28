import streamlit as st

from logic.backend.sites.add_site import post_site
from models.site import SiteOut
from ui.utils.timezones import label_common_timezones_relative_to_user


@st.dialog("Add a site")
def add_site() -> None:
    headers = st.session_state.get("auth_headers", {})
    user_timezone = getattr(st.context, "timezone", "America/Vancouver")
    timezone_options = label_common_timezones_relative_to_user(user_timezone)
    timezone_names = [name for name, _ in timezone_options]
    timezone_labels = {name: label for name, label in timezone_options}

    with st.container(border=True):
        st.caption("Create a new site and choose its timezone from a common list.")

        code = st.text_input(
            label="Site Code",
            placeholder="HVC",
        ).strip()
        name = st.text_input(
            label="Site Name",
            placeholder="Highland Valley Copper",
        ).strip()
        timezone_name = st.selectbox(
            label="Timezone",
            options=timezone_names,
            index=timezone_names.index("America/Vancouver"),
            format_func=lambda tz_name: timezone_labels[tz_name],
        )
        is_active = st.checkbox(
            label="Active",
            value=True,
        )

        if st.button(":material/add: Add Site", type="primary"):
            if not code:
                st.error("The new site must have a code.")
                st.stop()
            if not name:
                st.error("The new site must have a name.")
                st.stop()

            site = SiteOut(
                code=code,
                name=name,
                timezone=timezone_name,
                is_active=bool(is_active),
            )
            try:
                created = post_site(headers=headers, site=site)
            except ValueError:
                st.error(f"Sorry, we were unable to add the {name} site.")
                st.stop()

            st.success(f"{created.name} site successfully created!")
            st.rerun()
