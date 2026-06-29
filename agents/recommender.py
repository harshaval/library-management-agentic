"""agents/recommender.py"""
from crewai import Agent, LLM
from tools.recommend_tools import books_by_genre, member_borrow_history


def build_recommender(llm: LLM) -> Agent:
    return Agent(
        role="Book Recommender",
        goal=(
            "Provide personalised book recommendations based on genre preference "
            "and the member's borrowing history."
        ),
        backstory=(
            "A passionate reader who has consumed over a thousand books. "
            "You match the right book to the right person and always check "
            "availability before suggesting anything."
        ),
        tools=[books_by_genre, member_borrow_history],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
        max_rpm=10,
    )
