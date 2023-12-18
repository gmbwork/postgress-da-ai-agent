import os
from postgres_da_ai_agent.modules.db import PostgresManager
from postgres_da_ai_agent.modules import llm
from postgres_da_ai_agent.modules import orchestrator
from postgres_da_ai_agent.modules import file_util
from postgres_da_ai_agent.modules import embedding
from postgres_da_ai_agent.agents  import agents
import dotenv
import argparse
import autogen

dotenv.load_dotenv()

assert os.environ.get("DATABASE_URL") is not None, "POSTGRES_CONNECTION_URL not found in .env file"
assert os.environ.get("OPENAI_API_KEY") != "", "OPENAI_API_KEY is empty in .env file"

DB_URL = os.environ.get("DATABASE_URL")
OPEBNAI_API_KEY = os.environ.get("OPENAI_API_KEY")

POSTGRES_TABLE_DEFINITIONS_CAP_REF = "TABLE_DEFINITIONS"
RESPONSE_FORMAT_CAP_REF = "RESPONSE_FORMAT"
SQL_DELIMITER = "----------"

def main():
    # parse prompt param using arg parse
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', help='The prompt to use for the AI agent')
    args = parser.parse_args()

    if not args.prompt:
        print("Please provide a prompt using the --prompt flag")
        return

    raw_prompt = args.prompt
    
    prompt = f"Fulfill this databse query: {raw_prompt}. "
    
    with PostgresManager() as db:
        db.connect_with_url(DB_URL)
        
        map_table_name_to_table_def = db.get_table_definitions_map_for_embeddings()
        
        database_embedder = embedding.DatabaseEmbeder()
        
        for name, table_def in map_table_name_to_table_def.items():
            database_embedder.add_tabel(name, table_def)
            
        similar_tables = database_embedder.get_similar_tables(raw_prompt, n=5)
        
        table_definitions = database_embedder.get_table_definitions_from_names(similar_tables)
        
        prompt = llm.add_cap_ref(
            prompt,
            f"Use this {POSTGRES_TABLE_DEFINITIONS_CAP_REF} to satisfy the database SQL query.",
            POSTGRES_TABLE_DEFINITIONS_CAP_REF,
            table_definitions,
        )
        
        data_eng_orchestrator = agents.build_team_orchestrator("data_eng", db)
        
        success, data_eng_messages = data_eng_orchestrator.sequential_conversation(prompt)
        
        #------------------------------------------------
        
        print(f"\n\n---------------------Run Cost & Tokens Usage---------------------")
        
        data_eng_cost, data_eng_tokens = data_eng_orchestrator.get_cost_and_tokens()
        
        print(f"Data Engineering Cost: {data_eng_cost}, Tokens: {data_eng_tokens}")
        
        print(f"💰📊🤖  Origanization Cost: {data_eng_cost}, Tokens: {data_eng_tokens}")
        
        # print("\n\n---------------------Overall Tokens Usage---------------------")
        
        # print(f"Total Tokens Used: {data_eng_orchestrator.count_tokens_total_used()}")
        
        # print("\n\n---------------------Overall Tokens Left---------------------")
        
        # print(f"Tokens Left: {data_eng_orchestrator.count_tokens_left()}")
        
        # # ----------------------------------------------

if __name__ == '__main__':
    main()