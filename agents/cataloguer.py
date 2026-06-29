"""agents/cataloguer.py"""
from crewai import Agent, LLM
from tools.catalog_tools import search_catalog, add_book, update_book


def build_cataloguer(llm: LLM) -> Agent:
    return Agent(
        role="Library Cataloguer",
        goal=(
            "Maintain an accurate, up-to-date book catalog. "
            "Search for books, add new titles, and correct existing records."
        ),
        backstory=(
            "A meticulous librarian with 20 years of cataloguing experience. "
            "Precise and thorough — you always verify data before making changes."
        ),
        tools=[search_catalog, add_book, update_book],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
        max_rpm=10,
    )
