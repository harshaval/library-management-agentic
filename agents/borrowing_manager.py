"""agents/borrowing_manager.py"""
from crewai import Agent, LLM
from tools.borrowing_tools import checkout_book, return_book, list_overdue


def build_borrowing_manager(llm: LLM) -> Agent:
    return Agent(
        role="Borrowing Manager",
        goal=(
            "Process all checkouts and returns accurately. "
            "Proactively identify and report overdue loans."
        ),
        backstory=(
            "A dependable borrowing desk manager with 15 years in public libraries. "
            "Fair access for every member — you never let a transaction slip through."
        ),
        tools=[checkout_book, return_book, list_overdue],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
        max_rpm=10,
    )
