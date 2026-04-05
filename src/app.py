import streamlit as st

from logic.state import initialize_session_state
from logic.backend.guards import require_login, is_admin
from logic.backend.login import is_logged_in, get_current_user, logout

st.set_page_config(
    page_title="GanttBuddy", 
    layout="wide", 
    initial_sidebar_state="auto"
)

initialize_session_state()

# If not logged in, show ONLY the login page (or a login callable)
if not is_logged_in():
    login_page = st.Page("pages/login.py", title="Sign in")  
    page = st.navigation([login_page])
    page.run()
    st.stop()

with st.sidebar:
    st.subheader("User")
    user_data = get_current_user(st.session_state.get("auth_headers"))
    with st.container(horizontal=True):
        
        st.caption(f":material/person: {user_data['email']}")
        st.space("stretch")
        if st.button(":material/logout: Logout", type="tertiary"):
            logout()

# Logged in:
home = st.Page("pages/home.py", title="Home", icon=":material/home:")
todos = st.Page("pages/todo.py", title="Todos", icon=":material/checklist:")
account = st.Page("pages/account.py", title="Account", icon=":material/person:")
projects = st.Page("pages/projects.py", title="Load", icon=":material/folder_open:")
excel_import = st.Page("pages/excel_import.py", title="Excel Import", icon=":material/table_view:")
feed = st.Page("pages/feed.py", title="Feed", icon=":material/view_list:")
build = st.Page("pages/build.py", title="Build", icon=":material/build:")
plan = st.Page("pages/plan.py", title="Plan", icon=":material/view_timeline:")
execute = st.Page("pages/execute.py", title="Execute", icon=":material/construction:")
signals = st.Page("pages/signals.py", title="Signals", icon=":material/sensors:")
delays = st.Page("pages/analyze.py", title="Delays", icon=":material/timer:")
analytics = st.Page("pages/analytics.py", title="Analytics", icon=":material/query_stats:")
manage = st.Page("pages/manage.py", title="Manage", icon=":material/manage_accounts:")

pages = {
    "Home": [home, todos, account], 
    "Projects": [projects, excel_import, feed, build],
}

#if st.session_state.session.project:
pages["Workspace"] = [plan, execute, signals, delays, analytics]

pages["Manage"] = [manage]



# Admin-only
if is_admin():
    admin = st.Page("pages/admin.py", title="Admin", icon="🛠️")
    pages["Admin"] = []
    pages["Admin"].append(admin)

page = st.navigation(pages)
page.run()
