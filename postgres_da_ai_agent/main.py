import os
from postgres_da_ai_agent.modules.db import PostgresManager
# from postgres_da_ai_agent.modules import llm
import dotenv
import argparse
import autogen
from postgres_da_ai_agent.modules.llm_configuraiton import codellama_llm_config, mistral_llm_config, sqlcoder_llm_config
from postgres_da_ai_agent.modules.data_base_query_prompt import generate_sqlcoder_prompt

dotenv.load_dotenv()

assert os.environ.get("DATABASE_URL") is not None, "POSTGRES_CONNECTION_URL not found in .env file"
#assert os.environ.get("OPENAI_API_KEY") != "", "OPENAI_API_KEY is empty in .env file"

DB_URL = os.environ.get("DATABASE_URL")
#OPEBNAI_API_KEY = os.environ.get("OPENAI_API_KEY")

POSTGRES_TABLE_DEFINITIONS_CAP_REF = "TABLE_DEFINITIONS"
RESPONSE_FORMAT_CAP_REF = "RESPONSE_FORMAT"
SQL_DELIMITER = "----------"

def add_cap_ref(
    prompt: str, prompt_suffix: str, cap_ref: str, cap_ref_content: str
) -> str:
    """
    Attaches a capitalized reference to the prompt.
    Example
        prompt = 'Refactor this code.'
        prompt_suffix = 'Make it more readable using this EXAMPLE.'
        cap_ref = 'EXAMPLE'
        cap_ref_content = 'def foo():\n    return True'
        returns 'Refactor this code. Make it more readable using this EXAMPLE.\n\nEXAMPLE\n\ndef foo():\n    return True'
    """

    new_prompt = f"""{prompt} {prompt_suffix}\n\n{cap_ref}\n\n{cap_ref_content}"""

    return new_prompt


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

        # prompt = add_cap_ref(
        #     prompt,
        #     f"Use this {POSTGRES_TABLE_DEFINITIONS_CAP_REF} to satisfy the database SQL query.",
        #     POSTGRES_TABLE_DEFINITIONS_CAP_REF,
        #     table_definitions,
        # )
        prompt = generate_sqlcoder_prompt(
            prompt, 
            table_definitions
        )

        print("Promopt after adding table definitions:", prompt)

        # build the funcation map
        function_map = {
            "run_sql": db.run_sql,
        }

        # create our terminate msg function
        def is_terminate_msg(content):
            have_content = content.get("content", None) is not None
            if have_content and "APPROVED"  in content["content"]:
                return True
            return False
        
        COMPLETION_PROMPT = "If everything looks good, respond with APPROVED. Otherwise, respond with REJECTED."

        USER_PROXY_PROMPT = (
            "A human admin. Interact with the Product Manager to discuss the plan. Plan execution needs to be approved by this admin."
            + COMPLETION_PROMPT
        )

        DATA_ENGINEER_PROMPT = (
            "A Data Engineer. You follow a approved plan. Generate the initial SQL based on the requirements provided. Send it to the Sr Data Analyst to be executed."
            + COMPLETION_PROMPT
        )

        SR_DATA_ANALYST_PROMPT = (
            "A Sr Data Analyst. You follow an approved plan. You run the SQL query, gererate the response and send it to the product manager for final review."
            + COMPLETION_PROMPT
        )

        PRODUCT_MANAGER_PROMPT = (
            "A Product Manager. Validate the response to make sure it's correct"
            + COMPLETION_PROMPT
        )

        # create a set of agents with specific roles
        # admin user proxy agen - takes in the prompt and manages the group chat
        user_proxy = autogen.UserProxyAgent(
            name="Admin",
            system_message=USER_PROXY_PROMPT,
            code_execution_config=False,
            human_input_mode="NEVER",
            is_termination_msg=is_terminate_msg,
        )

        # data engineer agent - generates the sql query
        data_engineer = autogen.AssistantAgent(
            name="Engineer",
            llm_config=sqlcoder_llm_config,
            system_message=DATA_ENGINEER_PROMPT,
            code_execution_config=False,
            human_input_mode="NEVER",
            is_termination_msg=is_terminate_msg,
        )

        # sr data analyst agent - runs the sql query and generates the response
        sr_data_analyst = autogen.AssistantAgent(
            name="Sr_Data_Analyst",
            llm_config=mistral_llm_config,
            system_message=SR_DATA_ANALYST_PROMPT,
            human_input_mode="NEVER",
            is_termination_msg=is_terminate_msg,
            function_map=function_map,
            code_execution_config={
                "work_dir": "coding",
                "use_docker": False,  # set to True or image name like "python:3" to use docker
            },
        )

        # product manager agent - validates the response to make sure it's correct
        product_manager = autogen.AssistantAgent(
            name="Product_Manager",
            llm_config=mistral_llm_config,
            system_message=PRODUCT_MANAGER_PROMPT,
            code_execution_config=False,
            human_input_mode="NEVER",
            is_termination_msg=is_terminate_msg,
        )

        # create a group chat with the agents and initiate the chat.
        groupchat = autogen.GroupChat(
            agents=[user_proxy, data_engineer, sr_data_analyst, product_manager],
            messages=[],
            max_round=5,
        )
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=mistral_llm_config)
        user_proxy.initiate_chat(manager, clear_history=True, message=prompt)

if __name__ == '__main__':
    main()