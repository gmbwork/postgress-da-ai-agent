
import argparse
import os
from postgres_da_ai_agent.modules.db import PostgresManager
from postgres_da_ai_agent.modules import llm
import dotenv

dotenv.load_dotenv()

assert os.environ.get("POSTGRES_URL") is not None, "POSTGRES_CONNECTION_URL not found in .env file"
assert os.environ.get("OPENAI_API_KEY") != "", "OPENAI_API_KEY is empty in .env file"

DB_URL = os.environ.get("POSTGRES_URL")
OPEBNAI_API_KEY = os.environ.get("OPENAI_API_KEY")

POSTGRES_TABLE_DEFINITIONS_CAP_REF = "TABLE_DEFINITIONS"
RESPONSE_FORMAT_CAP_REF = "RESPONSE_FORMAT"

SQL_DELIMITER = "----------"

def main():
    
    # parse prompt param using arg parse
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', help='The prompt to use for the AI agent')
    args = parser.parse_args()

    prompt = args.prompt

    # connect to db using with statement and create a db_manager
    with PostgresManager() as db:

        print("prompt v1", prompt)
        #"postgres://postgres:postgres@localhost:5432/postgres"
        db.connect_with_url(DB_URL)

    # call db_manager.get_table_definition() to get tables in prompt ready form
    table_definitions = db.get_table_definition_for_prompt()
    print("table_definitions", table_definitions)

    # create two blank calls to llm.add_cap_ref() that update our current prompt passed in from cli

    prompt = llm.add_cap_ref(
        args.prompt, 
        f"Use these {POSTGRES_TABLE_DEFINITIONS_CAP_REF} to satisfy the database query.", 
        POSTGRES_TABLE_DEFINITIONS_CAP_REF,
        table_definitions
    )

    print("prompt v2", prompt)

    prompt = llm.add_cap_ref(
        prompt, 
        f"\n\nRespond in this format {RESPONSE_FORMAT_CAP_REF}. Replace the text between <> with it's request. I need to be able to easily parse the sql query from your response.",
        RESPONSE_FORMAT_CAP_REF,
        f"""<explanation of the sql query>
{SQL_DELIMITER}
<sql query exclusively as raw text>""",
    )

    print("\n\n ------------ PROMPT ------------")
    print("prompt v3", prompt)

    #call llm.prompt to get a prompt_response variable

    prompt_response = llm.prompt(prompt)

    print("\n\n ------------ PROMPT RESPONSE ------------")
    print("prompt_response", prompt_response)

    # parse sql response from prompt_response using AQLQUERYDELIMITER '----------'
    sql_query = prompt_response.split(SQL_DELIMITER)[1].strip()

    print("\n\n ------------ PARSED SQL QUERY ------------")
    print("sql_query", sql_query)

    # call db_manager.run_sql() with the parsed sql

    result = db.run_sql(sql_query)

    print("================== POSTGRES DATA ANALYTICS AI AGENT RESPONSE ==================")
    print(result)
    pass

if __name__ == '__main__':
    main()