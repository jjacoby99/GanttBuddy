import streamlit as st

from ui.load_from_excel import render_excel_import_page


def main() -> None:
    render_excel_import_page()


if __name__ == "__main__":
    main()
