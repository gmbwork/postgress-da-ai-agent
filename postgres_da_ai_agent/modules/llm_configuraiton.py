import os
import autogen

codellama_config_list = autogen.config_list_from_json(
    env_or_file="OAI_CONFIG_LIST",
    filter_dict={
        "model": ["codellama"],
    },
)

mistral_config_list = autogen.config_list_from_json(
    env_or_file="OAI_CONFIG_LIST",
    filter_dict={
        "model": ["mistral"],
    },
)

sqlcoder_config_list = autogen.config_list_from_json(
    env_or_file="OAI_CONFIG_LIST",
    filter_dict={
        "model": ["sqlcoder"],
    },
)

# build the gpt_configuration object
codellama_llm_config = {
    "cache_seed": None,
    "temperature": 0,
    "config_list": codellama_config_list,
    "timeout": 120,
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
                    }
                },
                "required": ["sql"],
            },
        },
    ],
}

mistral_llm_config = {
    "cache_seed": None,
    "temperature": 0,
    "config_list": mistral_config_list,
    "timeout": 120,    
}

sqlcoder_llm_config = {
    "cache_seed": None,
    "temperature": 0,
    "config_list": sqlcoder_config_list,
    "timeout": 120,    
}
