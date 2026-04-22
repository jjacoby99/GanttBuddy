import streamlit as st

from ui.todo_list import render_todo_list


st.header("Todos")
render_todo_list()
