import streamlit as st

from ui.todo_list import render_todo_list
from ui.utils.page_header import render_registered_page_header


render_registered_page_header("todos")
render_todo_list()
