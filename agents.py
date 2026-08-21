"""
AI SQL Database Agent
Powered by LangGraph, LangChain, ChatGroq, and PostgreSQL.
"""

import os
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment variables are loaded from the project directory
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from sql_validator import is_query
from database import get_db_connection


# ---------------------------------------------------------------------------
# 1. Define LangGraph Database Tools
# ---------------------------------------------------------------------------

@tool
def fetch_schema() -> str:
    """Fetch the database schema including table names, columns, data types, and primary keys from the public schema."""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 1. Fetch column definitions
            cursor.execute("""
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
            """)
            rows = cursor.fetchall()
            if not rows:
                return "No tables found in the public schema."

            tables = {}
            for table_name, col_name, data_type, is_nullable in rows:
                if table_name not in tables:
                    tables[table_name] = []
                null_info = "" if is_nullable == "YES" else " NOT NULL"
                tables[table_name].append(f"{col_name} ({data_type}{null_info})")

            # 2. Fetch primary keys for better join inference
            cursor.execute("""
                SELECT tc.table_name, kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public';
            """)
            pk_rows = cursor.fetchall()
            pk_map = {}
            for t_name, c_name in pk_rows:
                pk_map[t_name] = c_name

            # Format the schema output
            schema_lines = [
                "=== PostgreSQL Database Schema (public) ===",
                f"Total Tables: {len(tables)}\n"
            ]
            for table_name, cols in tables.items():
                pk_str = f" [PK: {pk_map[table_name]}]" if table_name in pk_map else ""
                schema_lines.append(f"• Table: {table_name}{pk_str}")
                schema_lines.append(f"    Columns: {', '.join(cols)}")
                schema_lines.append("")

            return "\n".join(schema_lines).strip()
    except Exception as error:
        return f"Error fetching schema from database: {error}"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


@tool
def run_sql_query(query: str) -> str:
    """Execute a safe, read-only SQL query against the PostgreSQL database after security validation.

    Args:
        query: The SQL SELECT or WITH query string to execute. Must end with a semicolon.
    """
    # 1. Clean and sanitize the query input
    clean_query = query.strip()

    # Strip markdown code blocks if the LLM wrapped it in ```sql ... ```
    if clean_query.startswith("```"):
        lines = clean_query.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean_query = "\n".join(lines).strip()

    # Strip inline backticks
    clean_query = clean_query.strip("`").strip()

    # Auto-ensure trailing semicolon
    if not clean_query.endswith(";"):
        clean_query += ";"

    # 2. Security validation check
    if not is_query(clean_query):
        return (
            f"SECURITY REJECTION ERROR:\n"
            f"Query: {clean_query}\n"
            f"Reason: Only safe, read-only SELECT or WITH (CTE) queries are allowed. "
            f"Modification statements (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, etc.) "
            f"and unauthorized commands are strictly prohibited."
        )

    # 3. Execute the SQL query
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(clean_query)
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()

                if not rows:
                    return f"Query executed successfully.\nColumns: [{', '.join(columns)}]\nResult: 0 rows returned."

                # Format rows into a clean, readable text table
                total_count = len(rows)
                display_rows = rows[:100]  # Safeguard against huge query responses

                formatted_rows = []
                for row in display_rows:
                    row_str = [str(val) if val is not None else "NULL" for val in row]
                    formatted_rows.append(row_str)

                # Calculate column widths
                col_widths = [len(col) for col in columns]
                for row in formatted_rows:
                    for i, val in enumerate(row):
                        col_widths[i] = max(col_widths[i], len(val))

                # Build ASCII table
                header_line = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
                separator_line = "-+-".join("-" * col_widths[i] for i in range(len(columns)))
                data_lines = [
                    " | ".join(val.ljust(col_widths[i]) for i, val in enumerate(row))
                    for row in formatted_rows
                ]

                result_text = f"Query executed successfully ({total_count} rows):\n"
                result_text += header_line + "\n" + separator_line + "\n" + "\n".join(data_lines)

                if total_count > 100:
                    result_text += f"\n... ({total_count - 100} more rows truncated for display)"

                return result_text
            else:
                return "Query executed successfully. (0 rows returned)"
    except Exception as error:
        return f"Database execution error: {error}. Please review table/column names from fetch_schema and retry."
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# List of tools available to the SQL agent
tools = [fetch_schema, run_sql_query]


# ---------------------------------------------------------------------------
# 2. Agent Factory Function
# ---------------------------------------------------------------------------

def create_agent():
    """Initializes and returns the LangGraph SQL assistant ReAct agent."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Please ensure your GROQ_API_KEY is configured in the .env file."
        )

    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip().strip('"').strip("'")
    if not groq_model:
        groq_model = "llama-3.3-70b-versatile"

    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name=groq_model,
        temperature=0.1,
    )

    system_prompt = (
        "You are an expert AI SQL Assistant and Data Analyst that helps users query a PostgreSQL database "
        "using natural language.\n\n"
        "Follow this exact step-by-step process for EVERY user question:\n"
        "1. ALWAYS inspect the database structure using the `fetch_schema` tool first. "
        "Never guess or assume table or column names without verifying the schema.\n"
        "2. Formulate a single, correct, and efficient PostgreSQL SELECT or WITH (CTE) query matching "
        "the exact table and column names found in the schema.\n"
        "3. ALWAYS execute your query using the `run_sql_query` tool. Ensure the query ends with a semicolon (;).\n"
        "4. If the query encounters a database error or security error, inspect the error message carefully, "
        "adjust your SQL query syntax or column names, and retry.\n"
        "5. Once you obtain the results from `run_sql_query`, summarize them clearly in natural language for the user. "
        "Highlight key numbers, metrics, or comparisons. If appropriate, format results in markdown tables or bullet points.\n\n"
        "CRITICAL RULES:\n"
        "- Only generate read-only SELECT or WITH statements.\n"
        "- NEVER generate write, DDL, or destructive statements (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE).\n"
        "- Ground all statements strictly in the actual query results returned by `run_sql_query`."
    )

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt
    )
    return agent


# ---------------------------------------------------------------------------
# 3. High-Level Invocation Wrapper
# ---------------------------------------------------------------------------

def ask_agent(user_question: str) -> dict:
    """Wrapper function to invoke the agent with a user question and parse the result.

    Returns a dict containing:
        - success: Boolean indicating if the agent invocation succeeded.
        - answer: The final natural language response from the agent.
        - sql_query: The last executed SQL query (if any).
        - all_queries: List of all SQL queries executed during the run.
        - validation_passed: Boolean indicating if all queries passed security checks.
        - tool_output: Raw output string from the tools.
        - messages: Full message history from the agent run.
        - error: Error message string if an exception occurred.
    """
    try:
        agent = create_agent()
        inputs = {"messages": [("user", user_question)]}
        response = agent.invoke(inputs)

        # Extract messages
        messages = response.get("messages", [])
        final_answer = ""
        if messages:
            last_msg = messages[-1]
            raw_content = getattr(last_msg, "content", "")
            if isinstance(raw_content, list):
                # Handle structured content blocks
                text_parts = []
                for part in raw_content:
                    if isinstance(part, str):
                        text_parts.append(part)
                    elif isinstance(part, dict) and part.get("text"):
                        text_parts.append(part["text"])
                    elif hasattr(part, "text"):
                        text_parts.append(str(part.text))
                final_answer = "\n".join(text_parts) if text_parts else str(raw_content)
            else:
                final_answer = str(raw_content)

        # Extract executed SQL queries and tool outputs
        last_sql = None
        all_queries = []
        validation_passed = True
        tool_outputs = []

        for msg in messages:
            # Check tool calls from AI messages
            tool_calls = getattr(msg, "tool_calls", None) or []
            for tc in tool_calls:
                fn_name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                fn_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})

                if fn_name == "run_sql_query":
                    q = fn_args.get("query") if isinstance(fn_args, dict) else getattr(fn_args, "query", None)
                    if q:
                        # Clean backticks and semicolons for display
                        q_clean = q.strip().strip("`").strip()
                        if not q_clean.endswith(";"):
                            q_clean += ";"
                        last_sql = q_clean
                        all_queries.append(q_clean)

            # Check tool output
            msg_type = getattr(msg, "type", "")
            if msg_type == "tool" or type(msg).__name__ == "ToolMessage":
                content_str = str(getattr(msg, "content", ""))
                tool_outputs.append(content_str)
                if "SECURITY REJECTION ERROR" in content_str or "SECURITY ERROR" in content_str:
                    validation_passed = False

        return {
            "success": True,
            "answer": final_answer.strip(),
            "sql_query": last_sql,
            "all_queries": all_queries,
            "validation_passed": validation_passed,
            "tool_output": "\n\n".join(tool_outputs).strip(),
            "messages": messages,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "answer": f"An error occurred while processing your request: {e}",
            "sql_query": None,
            "all_queries": [],
            "validation_passed": False,
            "tool_output": "",
            "messages": [],
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# 4. Interactive Command Line Interface (CLI)
# ---------------------------------------------------------------------------

def cli():
    """Interactive Command Line Interface for querying the SQL Database Agent."""
    # ANSI color codes for rich terminal styling
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    banner = f"""
{CYAN}{BOLD}╔══════════════════════════════════════════════════════════════════════╗
║               🤖  AI SQL DATABASE AGENT - INTERACTIVE CLI            ║
╚══════════════════════════════════════════════════════════════════════╝{RESET}
{MAGENTA}Ask any question in natural language to query your PostgreSQL database.{RESET}

{YELLOW}{BOLD}Available Commands:{RESET}
  {GREEN}schema{RESET}       - View all tables, columns, and data types
  {GREEN}help{RESET}         - Show this help menu
  {GREEN}clear{RESET} / {GREEN}cls{RESET}  - Clear the terminal screen
  {GREEN}exit{RESET} / {GREEN}quit{RESET}   - Exit the CLI
{"=" * 72}
"""
    print(banner)

    # Test database connection silently
    try:
        conn = get_db_connection()
        conn.close()
        print(f"{GREEN}✓ Database connection verified.{RESET}\n")
    except Exception as err:
        print(f"{YELLOW}⚠️  Note: Database connection check returned: {err}{RESET}\n")

    while True:
        try:
            user_input = input(f"{CYAN}{BOLD}💬 Enter your question: {RESET}").strip()

            if not user_input:
                continue

            cmd_lower = user_input.lower()

            # Exit command
            if cmd_lower in ["exit", "quit", "q"]:
                print(f"\n{GREEN}👋 Thank you for using AI SQL Database Agent. Goodbye!{RESET}\n")
                break

            # Clear screen command
            if cmd_lower in ["clear", "cls"]:
                os.system("cls" if os.name == "nt" else "clear")
                print(banner)
                continue

            # Help command
            if cmd_lower in ["help", "?"]:
                print(f"\n{YELLOW}{BOLD}Commands:{RESET}")
                print(f"  {GREEN}schema{RESET}       - Fetch and display the database schema")
                print(f"  {GREEN}clear{RESET}        - Clear the terminal screen")
                print(f"  {GREEN}exit{RESET}         - Quit the application")
                print(f"  {GREEN}<question>{RESET}   - Ask any question (e.g. 'Show top 5 highest paid employees')\n")
                continue

            # Schema command
            if cmd_lower in ["schema", "tables", "show schema"]:
                print(f"\n{BLUE}⏳ Fetching database schema...{RESET}")
                schema_info = fetch_schema.invoke({})
                print(f"\n{CYAN}{BOLD}{'-' * 60}{RESET}")
                print(schema_info)
                print(f"{CYAN}{BOLD}{'-' * 60}{RESET}\n")
                continue

            # Natural language agent query
            print(f"\n{MAGENTA}⏳ Agent is analyzing schema, generating SQL, and querying database...{RESET}")
            result = ask_agent(user_input)

            print(f"\n{CYAN}{BOLD}{'═' * 70}{RESET}")

            # Display generated SQL Query if any
            if result.get("sql_query"):
                print(f"{YELLOW}{BOLD}🔍 Generated SQL Query:{RESET}")
                print(f"  {GREEN}{result['sql_query']}{RESET}")

                status_badge = (
                    f"{GREEN}✅ Safe & Validated{RESET}"
                    if result.get("validation_passed")
                    else f"{RED}❌ Security Violation{RESET}"
                )
                print(f"{BLUE}🛡️  Security Validation:{RESET} {status_badge}")
                print(f"{CYAN}{'-' * 70}{RESET}")

            # Display AI Response
            print(f"{BOLD}📊 AI Assistant Response:{RESET}\n")
            print(result.get("answer", "No response generated."))
            print(f"{CYAN}{BOLD}{'═' * 70}{RESET}\n")

        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{GREEN}👋 Session interrupted. Goodbye!{RESET}\n")
            break
        except Exception as e:
            print(f"\n{RED}❌ Unexpected Error: {e}{RESET}\n")


if __name__ == "__main__":
    cli()