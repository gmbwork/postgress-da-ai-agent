"""
Purpose:
    Interact with the OpenAI API.
    Provide supporting prompt engineering functions.
"""

import sys
from dotenv import load_dotenv
import os
from typing import Any, Dict
import openai
import tiktoken

# load .env file
load_dotenv()

assert os.environ.get("OPENAI_API_KEY")

# get openai api key
openai.api_key = os.environ.get("OPENAI_API_KEY")

# ------------------ helpers ------------------


def safe_get(data, dot_chained_keys):
    """
    {'a': {'b': [{'c': 1}]}}
    safe_get(data, 'a.b.0.c') -> 1
    """
    keys = dot_chained_keys.split(".")
    for key in keys:
        try:
            if isinstance(data, list):
                data = data[int(key)]
            else:
                data = data[key]
        except (KeyError, TypeError, IndexError):
            return None
    return data


def response_parser(response: Dict[str, Any]):
    return safe_get(response, "choices.0.message.content")


# ------------------ content generators ------------------


def prompt(prompt: str, model: str = "gpt-4") -> str:
    # validate the openai api key - if it's not valid, raise an error
    if not openai.api_key:
        sys.exit(
            """
ERORR: OpenAI API key not found. Please export your key to OPENAI_API_KEY
Example bash command:
    export OPENAI_API_KEY=<your openai apikey>
            """
        )

    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    return response_parser(response)


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

# def count_tokens_left():
#     """
#     Count the number of tokens left in the OpenAI API key
#     """
#     return openai.Account.retrieve().data["max_tokens"]

# def count_tokens_total_used():
#     """
#     Count the number of tokens used in the OpenAI API key
#     """
#     return openai.Account.retrieve().data["total_used_tokens"]

def count_token_run_used(text: str):
    """
    Count the number of tokens used in the OpenAI API key for the current run.
    """
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

def estimate_price_and_tokens(text):
    """
    Estimate the price and tokens used for a given text
    """
    COST_PER_1K_TOKENS = 0.0020
    
    tokens = count_token_run_used(text)
    
    estimated_cost = (tokens / 1000) * COST_PER_1K_TOKENS
    
    # round
    estimated_cost = round(estimated_cost, 4)
    
    return estimated_cost, tokens