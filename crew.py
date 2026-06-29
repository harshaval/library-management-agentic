"""
crew.py
Assembles the Library Crew and exposes run(crew, request) -> str.

Key efficiency choices:
- LLM and all agents are built once at startup and reused across requests.
- Process.hierarchical lets the manager dynamically route each request
  to the right specialist without a fixed sequential order.
- A single Task is created per request with a tight expected_output
  so the manager doesn't over-iterate.
"""

import os
from crewai import Crew, Task, LLM, Process

from agents.cataloguer        import build_cataloguer
from agents.borrowing_manager import build_borrowing_manager
from agents.recommender       import build_recommender
from agents.report_analyst    import build_report_analyst

_TASK_DESCRIPTION = (
    "A library user has made the following request:\n\n"
    '  "{request}"\n\n'
    "Fulfil it completely using the available agents and tools. "
    "If the request spans multiple steps (e.g. checkout then confirm), "
    "handle all of them. Confirm every action taken in your final answer."
)

_TASK_OUTPUT = (
    "A concise, complete response covering all parts of the user's request. "
    "Include titles, due dates, member names, stats, or recommendations as relevant."
)


def _build_llm() -> LLM:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file."
        )
    return LLM(
        model="anthropic/claude-sonnet-4-6",
        api_key=api_key,
        temperature=0.2,   # lower = more deterministic tool-calling
        max_tokens=2048,
    )


def build_crew() -> Crew:
    """Build and return the crew. Call once at process startup."""
    llm = _build_llm()
    return Crew(
        agents=[
            build_cataloguer(llm),
            build_borrowing_manager(llm),
            build_recommender(llm),
            build_report_analyst(llm),
        ],
        tasks=[],                        # populated dynamically in run()
        process=Process.hierarchical,
        manager_llm=llm,
        verbose=True,
        memory=False,
    )


def run(crew: Crew, user_request: str) -> str:
    """Execute one user request and return the crew's response string."""
    crew.tasks = [
        Task(
            description=_TASK_DESCRIPTION.format(request=user_request),
            expected_output=_TASK_OUTPUT,
        )
    ]
    return str(crew.kickoff())
