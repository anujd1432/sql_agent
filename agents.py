# We are now creating our agents; they will be able to perform tasks and actions based on the input they receive.
import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from sql_validator import is_query
from database import get_db_connection

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")


# 1. Define LangGraph tools.
@tool
def fetch_schema() -> str:
    """Fetch the database schema including table names, columns, and data types from the database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name, column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position;
                """)
                rows = cursor.fetchall()
                if not rows:
                    return "No tables found in the public schema."

                tables = {}
                for table_name, col_name, data_type in rows:
                    if table_name not in tables:
                        tables[table_name] = []
                    tables[table_name].append(f"{col_name} ({data_type})")

                schema_lines = ["Database Schema:"]
                for table_name, cols in tables.items():
                    schema_lines.append(f"Table: {table_name}")
                    schema_lines.append(f"  Columns: {', '.join(cols)}")
                return "\n".join(schema_lines)
    except Exception as error:
        return f"Error fetching schema from database: {error}"


@tool
def run_sql_query(query: str) -> str:
    """Execute a read-only SQL query against the database after security validation.

    Args:
        query: The SQL SELECT or WITH query string to execute. Must end with a semicolon.
    """
    # 1. Security validation check
    if not is_query(query):
        return (
            f"SECURITY ERROR: Query rejected.\n"
            f"Query: {query}\n"
            "Reason: Only safe, read-only SELECT or WITH (CTE) queries ending with a semicolon "
            "are allowed. Modification statements (e.g., INSERT, UPDATE, DELETE, DROP, ALTER) are forbidden."
        )

    # 2. Execute SQL query
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    if not rows:
                        return f"Query executed successfully. Columns: {', '.join(columns)}\nResult: 0 rows returned."

                    lines = [f"Columns: {', '.join(columns)}"]
                    for row in rows:
                        lines.append(str(row))
                    return "\n".join(lines)
                else:
                    return "Query executed successfully. No rows returned."
    except Exception as error:
        return f"Database error executing query: {error}"


# 2. List all tools which agent will use.
tools = [fetch_schema, run_sql_query]


# 3. Function to initialize LangGraph agent.
def create_agent():
    """Initializes and returns the LangGraph SQL assistant ReAct agent."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Please configure it in your .env file.")

    model_name = GROQ_MODEL if GROQ_MODEL else "openai/gpt-oss-120b"

    llm = ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name=model_name,
        temperature=0.1
    )

    system_prompt = (
        "You are an expert SQL assistant that helps users query a database "
        "using natural language.\n\n"
        "Follow this process for every user question:\n"
        "1. Use the `fetch_schema` tool to understand the table structure "
        "(tables, columns, data types) before writing any query. Never assume "
        "column or table names without checking the schema first.\n"
        "2. Formulate a single, correct SELECT or WITH (CTE) query based on "
        "the user's question and the actual schema. Never write INSERT, "
        "UPDATE, DELETE, DROP, ALTER, or any other write/DDL statements.\n"
        "3. Always use the `run_sql_query` tool to validate and execute your "
        "query. Ensure the query ends with a semicolon. Never present results you haven't actually run through this tool.\n"
        "4. If the query fails or returns unexpected results, revise the query "
        "and try again — don't guess at the answer.\n"
        "5. Once you have results, summarize them clearly and concisely in "
        "plain language for the user. Don't just dump raw rows — explain what "
        "the data means in the context of their question.\n\n"
        "Be precise, don't fabricate data, and always ground your answers in "
        "the actual query results."
    )

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt
    )
    return agent


# 4. Wrapper function to run queries.
def ask_agent(user_question: str) -> dict:
    """Wrapper function to invoke the agent with a user question and parse the result.

    Returns a dict containing:
        - answer: The final natural language response from the agent.
        - sql_query: The last executed SQL query (if any).
        - all_queries: List of all SQL queries executed during the run.
        - validation_passed: Boolean indicating if all queries passed security checks.
        - tool_output: Raw output string from the tools.
        - messages: Full message history from the agent run.
    """
    agent = create_agent()
    inputs = {"messages": [("user", user_question)]}
    response = agent.invoke(inputs)

    # Extract messages
    messages = response.get("messages", [])
    final_answer = ""
    if messages:
        last_msg = messages[-1]
        final_answer = getattr(last_msg, "content", str(last_msg))

    # Extract SQL queries and tool outputs
    last_sql = None
    all_queries = []
    validation_passed = True
    tool_output = ""

    for msg in messages:
        # Check tool calls
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc.get("name") == "run_sql_query":
                    query_arg = tc.get("args", {}).get("query")
                    if query_arg:
                        last_sql = query_arg
                        all_queries.append(query_arg)

        # Check tool output
        msg_type = getattr(msg, "type", "")
        if msg_type == "tool" or type(msg).__name__ == "ToolMessage":
            content_str = str(getattr(msg, "content", ""))
            tool_output += content_str + "\n"
            if "SECURITY ERROR" in content_str:
                validation_passed = False

    return {
        "answer": final_answer,
        "sql_query": last_sql,
        "all_queries": all_queries,
        "validation_passed": validation_passed,
        "tool_output": tool_output.strip(),
        "messages": messages,
    }


# 5. CLI mode (Command Line Interface)
def cli():
    """Interactive Command Line Interface for querying the SQL Database Agent."""
    print("=" * 60)
    print("🤖  AI SQL Database Agent CLI")
    print("=" * 60)
    print("Ask any question in natural language to query your database.")
    print("Commands:")
    print("  'schema'              - View database schema")
    print("  'exit' / 'quit' / 'q' - Exit the CLI")
    print("=" * 60)

    while True:
        try:
            user_input = input("\n💬 Enter your question: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                print("\n👋 Goodbye!")
                break

            if user_input.lower() == "schema":
                print("\nFetching database schema...")
                schema_info = fetch_schema.invoke({})
                print("-" * 60)
                print(schema_info)
                print("-" * 60)
                continue

            print("\n⏳ Agent is thinking and querying database...")
            result = ask_agent(user_input)

            print("\n" + "=" * 60)
            if result.get("sql_query"):
                print(f"🔍 Generated SQL Query:\n  {result['sql_query']}")
                status = "✅ Passed" if result.get("validation_passed") else "❌ Security Violation"
                print(f"🛡️  Security Validation: {status}")
                print("-" * 60)

            print(f"📊 Response:\n{result['answer']}")
            print("=" * 60)

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    cli()