"""
Agent entrypoint alias for agents.py
"""

from agents import (
    fetch_schema,
    run_sql_query,
    tools,
    create_agent,
    ask_agent,
    cli,
)

__all__ = [
    "fetch_schema",
    "run_sql_query",
    "tools",
    "create_agent",
    "ask_agent",
    "cli",
]

if __name__ == "__main__":
    cli()
