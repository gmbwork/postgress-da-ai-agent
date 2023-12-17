import os
from postgres_da_ai_agent.modules.db import PostgresManager
from postgres_da_ai_agent.modules import llm
from postgres_da_ai_agent.modules import orchestrator
from postgres_da_ai_agent.modules import file_util
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

    prompt = f"Fulfill this databse query: {args.prompt}. "

    with PostgresManager() as db:
        db.connect_with_url(DB_URL)

        table_definitions = db.get_table_definitions_for_prompt()

        prompt = llm.add_cap_ref(
            prompt,
            f"Use this {POSTGRES_TABLE_DEFINITIONS_CAP_REF} to satisfy the database SQL query.",
            POSTGRES_TABLE_DEFINITIONS_CAP_REF,
            table_definitions,
        )
        
        oai_config_list= autogen.config_list_from_json(
           env_or_file="OAI_CONFIG_LIST",
            filter_dict={
            "model": ["gpt-3.5-turbo-1106"],
        }
)

        # build gpt_configuration object
        # Base Configuration
        base_config = {
            "cache_seed": 0,
            "temperature": 0,
            "config_list": oai_config_list,
            "timeout": 120,
        }

        # Configuration with "run_sql" function
        run_sql_config = {
            **base_config,  # Inset base configuration
            "functions": [
                {
                    "name": "run_sql",
                    "description": "Run a SQL query against the postgres database",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "The SQL query to run against the database",
                            },
                        },
                        "required": ["sql"],
                    },
                },
            ],
        }
        
        # Configuration with "write_to_file" function
        write_to_file_config = {
            **base_config, # Inset base configuration
            "functions": [
                {
                    "name": "write_to_file",
                    "description": "Write given content to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "The name of the file to write to",
                            },
                            "content": {
                                "type": "string",
                                "description": "The content to write to the file",
                            },
                        },
                        "required": ["filename", "content"],
                    },
                },
            ],
        }
        
        # Configuration with "write_to_json_file" function
        write_to_json_file_config = {
            **base_config, # Inset base configuration
            "functions": [
                {
                    "name": "write_to_json_file",
                    "description": "Write given json string to a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "The name of the file to write to",
                            },
                            "json_str": {
                                "type": "string",
                                "description": "The json string to write to the file",
                            },
                        },
                        "required": ["filename", "json_str"],
                    },
                },
            ],
        }
        
        # Configuration with "write_to_yaml_file" function
        write_to_yaml_file_config = {
            **base_config,  # Inherit base configuration
            "functions": [
                {
                    "name": "write_yml_file",
                    "description": "Write a yml file to the filesystem",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "The name of the file to write",
                            },
                            "json_str": {
                                "type": "string",
                                "description": "The json content of the file to write",
                            },
                        },
                        "required": ["filename", "json_str"],
                    },
                }
            ],
        }
        
        # Build the function map
        function_map_run_sql = {
            "run_sql": db.run_sql,
        }
        
        function_map_write_to_file = {
            "write_to_file": file_util.write_to_file,
        }
        
        function_map_write_to_json_file = {
            "write_to_json_file": file_util.write_to_json_file,
        }
        
        function_map_write_to_yaml_file = {
            "write_yml_file": file_util.write_to_yaml_file,
        }
        
       # create our terminate msg function
        def is_termination_msg(content):
            have_content = content.get("content", None) is not None
            if have_content and "APPROVED" in content["content"]:
                return True
            return False

        COMPLETION_PROMPT = "If everything looks good, respond with APPROVED"

        USER_PROXY_PROMPT = "A human admin. Interact with the Product Manager to discuss the plan. Plan execution needs to be approved by this admin."
        DATA_ENGINEER_PROMPT = "A Data Engineer. Generate the initial SQL based on the requirements provided. Send it to the Sr Data Analyst to be executed. "
        SR_DATA_ANALYST_PROMPT = "Sr Data Analyst. You run the SQL query using the run_sql function, send the raw response to the data viz team. You use the run_sql function exclusively."
        PRODUCT_MANAGER_PROMPT = (
            "Product Manager. Validate the response to make sure it's correct"
            + COMPLETION_PROMPT
        )

        # create a set of agents with specific roles
        # admin user proxy agent - takes in the prompt and manages the group chat
        user_proxy = autogen.UserProxyAgent(
            name="Admin",
            system_message=USER_PROXY_PROMPT,
            code_execution_config=False,
            human_input_mode="NEVER",
            is_termination_msg=is_termination_msg,
        )

        # data engineer agent - generates the sql query
        data_engineer = autogen.AssistantAgent(
            name="Engineer",
            llm_config=base_config,
            system_message=DATA_ENGINEER_PROMPT,
            code_execution_config=False,
            human_input_mode="NEVER",
            is_termination_msg=is_termination_msg,
        )

        # sr data analyst agent - run the sql query and generate the response
        sr_data_analyst = autogen.AssistantAgent(
            name="Sr_Data_Analyst",
            llm_config=run_sql_config,
            system_message=SR_DATA_ANALYST_PROMPT,
            code_execution_config=False,
            human_input_mode="NEVER",
            function_map=function_map_run_sql,
        )

        # product manager - validate the response to make sure it's correct
        product_manager = autogen.AssistantAgent(
            name="Product_Manager",
            llm_config=base_config,
            system_message=PRODUCT_MANAGER_PROMPT,
            code_execution_config=False,
            human_input_mode="NEVER",
            is_termination_msg=is_termination_msg,
        )
        
        data_engineering_agents = [
            user_proxy, 
            data_engineer, 
            sr_data_analyst, 
            product_manager
        ]
        
        data_eng_orchestration = orchestrator.Orchestrator(
            name="Postgress Data Analytics Multi-Agents ::: Data Engineering Orchestration",
            agents=data_engineering_agents,
        )
        
        success, data_enginering_messages = data_eng_orchestration.sequential_conversation(
            prompt
        )
        
        data_eng_result = data_enginering_messages[-2]["content"]
        
        # ----------------------------------------------
        
        # Create a new prompt for the data visualization agents
        
        TEXT_REPORT_ANALYST_PROMPT = "Text File Report Analyst. You exclusively use the write_file function on a summarized report."
        JSON_REPORT_ANALYST_PROMPT = "JSON File Report Analyst. You exclusively use the write_json_file function on the report."
        YML_REPORT_ANALYST_PROMPT = "Yaml Report Analyst. Do not conver the input to YAML. The function call takes care of doing the JSON to YAML convertion. Pass the parameter as it is in the JSON format. You exclusively use the write_yml_file function on the report."
        
        # Text report analyst agent - writes a summary report of the results and saves it to a local text file.
        text_report_analyst = autogen.AssistantAgent(
            name="Text_Report_Analyst",
            llm_config=write_to_file_config,
            system_message=TEXT_REPORT_ANALYST_PROMPT,
            human_input_mode="NEVER",
            function_map=function_map_write_to_file,
        )
        
        # JSON report analyst agent - writes a summary report of the results and saves it to a local JSON file.
        json_report_analyst = autogen.AssistantAgent(
            name="JSON_Report_Analyst",
            llm_config=write_to_json_file_config,
            system_message=JSON_REPORT_ANALYST_PROMPT,
            human_input_mode="NEVER",
            function_map=function_map_write_to_json_file,
        )
        
        # YAML report analyst agent - writes a summary report of the results and saves it to a local YAML file.
        yml_report_analyst = autogen.AssistantAgent(
            name="YAML_Report_Analyst",
            llm_config=write_to_yaml_file_config,
            system_message=YML_REPORT_ANALYST_PROMPT,
            human_input_mode="NEVER",
            function_map=function_map_write_to_yaml_file,
        )
        
        data_viz_agents = [
            user_proxy,
            text_report_analyst,
            json_report_analyst,
            yml_report_analyst,
        ]
        
        data_viz_orchestration = orchestrator.Orchestrator(
            name="Postgress Data Analytics Multi-Agents ::: Data Visualization Orchestration",
            agents=data_viz_agents,
        )
        
        data_viz_prompt = f"Here is the data to report: {data_eng_result}"
        
        data_viz_orchestration.broadcast_conversation(data_viz_prompt)
        
        # ----------------------------------------------

if __name__ == '__main__':
    main()