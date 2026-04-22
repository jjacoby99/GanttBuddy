import streamlit as st

from logic.backend.api_client import fetch_sites
from models.site import SiteIn

@st.cache_data
def get_sites(headers: dict) -> list[SiteIn]:
    try:
        data = fetch_sites(headers=headers)
    except Exception:
        return []
    
    sites = []
    for site_dict in data:
        code = site_dict.get("code")
        name = site_dict.get("name")
        timezone = site_dict.get("timezone")
        is_active = site_dict.get("is_active")
        id = site_dict.get("id")
        created_at = site_dict.get("created_at")
        updated_at = site_dict.get("updated_at")

        sites.append(
            SiteIn(
                code=code,
                name=name,
                timezone=timezone,
                is_active=is_active,
                id=id,
                created_at=created_at,
                updated_at=updated_at,
            )
        )
    return sites
        