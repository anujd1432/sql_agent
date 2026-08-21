import re

# Keywords that modify database tables or structure
FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
    "PG_SLEEP", "VACUUM", "REINDEX", "COPY"
]

def is_query(sql_query: str) -> bool:
    """
    Validates that a query is a safe, read-only SQL query:
    1. Query must start with SELECT or WITH statement.
    2. Query must not contain any forbidden modification keywords.
    3. Query must contain a semicolon at the end of the statement.
    """
    if not sql_query or not isinstance(sql_query, str):
        return False

    cleaned = sql_query.strip()
    
    # 1. Must start with SELECT or WITH
    if not (cleaned.upper().startswith("SELECT") or cleaned.upper().startswith("WITH")):
        return False

    # 2. Check for forbidden keywords (whole words, case-insensitive)
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", cleaned, re.IGNORECASE):
            return False

    # 3. Must end with a semicolon
    if not cleaned.endswith(";"):
        return False

    return True

if __name__ == "__main__":
    user_sql = input("enter your sql query: ")
    print(is_query(user_sql))


