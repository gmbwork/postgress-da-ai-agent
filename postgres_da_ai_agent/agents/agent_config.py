import os
from postgres_da_ai_agent.modules.db import PostgresManager
from postgres_da_ai_agent.modules import llm
from postgres_da_ai_agent.modules import orchestrator
from postgres_da_ai_agent.modules import file_util
import dotenv
import argparse
import autogen

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

# Configuration with "run_sql"
run_sql_config = {
    **base_config,  # Inherit base configuration
    "functions": [
        {
            "name": "run_sql",
            "description": "Run a SQL query against the postgres database",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The SQL query to run",
                    }
                },
                "required": ["sql"],
            },
        }
    ],
}

# Confdiguration with "write_file"
write_file_config = {
    **base_config, #Insert base configuration
    "functions": [
        {
          "name": "write_file",
          "description": "Write a file to the local filesystem",
          "parameters": {
              "type": "object",
              "properties": {
                  "filename": {
                      "type": "string",
                      "description": "Name of the file to write"
                  },
                  "content": {
                      "type": "string",
                      "description": "Content to write to the file"
                  },
              },
              "required": ["filename", "content"],
          },            
        },
    ],
}

# Configuration with "write_json_file"
write_json_file_config = {
    **base_config, #Insert base configuration
    "functions": [
        {
            "name": "write_json_file",
            "description": "Write a JSON file to the local filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to write"
                    },
                    "json_str": {
                      "type": "string",
                      "description": "JSON string to write to the file"
                    },
                },
                "required": ["filename", "json_str"],
            }
        }
    ],
}

# Configuraton with "write_yaml_file"
write_yaml_file_config = {
    **base_config, #Insert base configuration
    "functions": [
        {
            "name": "write_yaml_file",
            "description": "Write a YAML file to the local filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to write"
                    },
                    "json_str": {
                        "type": "string",
                        "description": "JSON string to write to the file"
                    },
                },
                "required": ["filename", "json_str"],
            },
        },
    ],
}

def create_func_map(name: str, func: callable):
    return {
        name: func,
    }

def build_function_map_run_sql(db: PostgresManager):
    return create_func_map("run_sql", db.run_sql)
    
function_map_write_to_file = create_func_map("write_file", file_util.write_to_file)
function_map_write_json_file = create_func_map("write_json_file", file_util.write_to_json_file)
function_map_write_yaml_file = create_func_map("write_yaml_file", file_util.write_to_yaml_file)