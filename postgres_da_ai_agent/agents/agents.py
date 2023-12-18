import os
from postgres_da_ai_agent.modules.db import PostgresManager
from postgres_da_ai_agent.modules import llm
from postgres_da_ai_agent.modules import orchestrator
from postgres_da_ai_agent.modules import file_util
from postgres_da_ai_agent.agents  import agent_config
import dotenv
import argparse
import autogen

#------------------PROMPTs------------------


# Create terminate msg function
def is_termination_msg(content):
    have_content = content is not None and len(content) > 0
    if have_content and "APPROVED" in content["content"]:
        return True
    else:
        return False
    
COMPLETION_PROMPT = "If everthing looks good, respond with APPROVED. Otherwise, respond with REJECTED."

USER_PROXY_PROMPT = "A human admin. Interact with the Product Manager to discuss the plan. Plan execution needs to be approved by this admin."
DATA_ENGINEER_PROMPT = "A Data Engineer. Generate the initial SQL based on the requirements provided. Send it to the Sr Data Analyst to be executed. "
SR_DATA_ANALYST_PROMPT = "Sr Data Analyst. You run the SQL query using the run_sql function, send the raw response to the data viz team. You use the run_sql function exclusively."
PRODUCT_MANAGER_PROMPT = (
    "Product Manager. Validate the response to make sure it's correct"
    + COMPLETION_PROMPT
)

TEXT_REPORT_ANALYST_PROMPT = "Text File Report Analyst. You exclusively use the write_file function on a summarized report."
JSON_REPORT_ANALYST_PROMPT = "Json Report Analyst. You exclusively use the write_json_file function on the report."
YML_REPORT_ANALYST_PROMPT = "Yaml Report Analyst. You exclusively use the write_yml_file function on the report."


# -----------------AGENTs------------------

# Creating a set of agents with specific roles
# Admin - User Proxy Agent - takes in the prompt and manages the group of chat
user_proxy = autogen.UserProxyAgent(
    name="Admin",
    system_message=USER_PROXY_PROMPT,
    code_execution_config=False,
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg,
)

# Data Engineer Agent - Generates the SQL query
data_engineer = autogen.AssistantAgent(
    name="Engineer",
    llm_config=agent_config.base_config,
    system_message=DATA_ENGINEER_PROMPT,
    code_execution_config=False,
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg,
)

# SR Data Analysit Agent - Runs the SQL query
def build_sr_data_analyst_agent(db: PostgresManager):
    return autogen.AssistantAgent(
        name="Sr Data Analyst",
        llm_config=agent_config.run_sql_config,
        system_message=SR_DATA_ANALYST_PROMPT,
        code_execution_config=False,
        human_input_mode="NEVER",
        function_map=agent_config.build_function_map_run_sql(db),
    )

# Product Manager Agent - Validates the response to make sure it's correct
product_manager = autogen.AssistantAgent(
    name="Product_Manager",
    llm_config=agent_config.base_config,
    system_message=PRODUCT_MANAGER_PROMPT,
    code_execution_config=False,
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg,
)

# Text report analyst agent - Writes the summary report of analysis to a text file
text_report_analyst = autogen.AssistantAgent(
    name="Text_Report_Analyst",
    llm_config=agent_config.write_file_config,
    system_message=TEXT_REPORT_ANALYST_PROMPT,
    human_input_mode="NEVER",
    function_map=agent_config.function_map_write_to_file,
)

# Json report analyst agent - Writes the summary report of analysis to a json file
json_report_analyst = autogen.AssistantAgent(
    name="Json_Report_Analyst",
    llm_config=agent_config.write_json_file_config,
    system_message=JSON_REPORT_ANALYST_PROMPT,
    human_input_mode="NEVER",
    function_map=agent_config.function_map_write_json_file,
)

# Yaml report analyst agent - Writes the summary report of analysis to a yaml file
yaml_report_analyst = autogen.AssistantAgent(
    name="Yml_Report_Analyst",
    llm_config=agent_config.write_yaml_file_config,
    system_message=YML_REPORT_ANALYST_PROMPT,
    human_input_mode="NEVER",
    function_map=agent_config.function_map_write_yaml_file,
)


# -----------------ORCHESTRATOR------------------

def build_team_orchestrator(
    team: str,
    db: PostgresManager,
) -> orchestrator.Orchestrator:
    if team == "data_eng":
        return orchestrator.Orchestrator(
            name="Postgres Data Analytics Multi-Agent ::: Data Engineering Team",
            agents=[
                user_proxy, 
                data_engineer,
                build_sr_data_analyst_agent(db), 
                product_manager,
            ],
        )
    elif team == "data_viz":
        return orchestrator.Orchestrator(
            name="Postgres Data Analytics Multi-Agent ::: Data Viz Team",
            agents=[
                user_proxy,
                text_report_analyst,
                json_report_analyst,
                yaml_report_analyst,
            ],
        )