"""agents/report_analyst.py"""
from crewai import Agent, LLM
from tools.report_tools import library_stats, most_borrowed_books


def build_report_analyst(llm: LLM) -> Agent:
    return Agent(
        role="Library Report Analyst",
        goal=(
            "Generate accurate reports on library performance and surface "
            "actionable insights from borrowing data."
        ),
        backstory=(
            "A data-driven analyst who translates raw numbers into clear narratives "
            "that help librarians make better decisions about stock and budget."
        ),
        tools=[library_stats, most_borrowed_books],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
        max_rpm=10,
    )
