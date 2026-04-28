from models.site import SiteIn, SiteOut
from logic.backend.api_client import add_site as post_new_site


def post_site(headers: dict, site: SiteOut) -> SiteIn:
    try:
        response = post_new_site(headers=headers, site=site)
    except ValueError as e:
        print(f"Failed to create new site: {str(e)}")
        raise ValueError(f"Failed to create new site {site.name}")

    return SiteIn(**response)
