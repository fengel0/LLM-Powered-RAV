from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute, FileConfigAttribute

SYSTEM_PROMPT_SIMPLE = "SYSTEM_PROMPT"
QUERY_WRAPPER_PROMPT = "QUERY_WRAPPER_PROMPT"
TOP_N_COUNT_DENSE = "TOP_N_COUNT_DENSE"
TOP_N_COUNT_SPARSE = "TOP_N_COUNT_SPARSE"
TOP_N_COUNT_RERANKER = "TOP_N_COUNT_RERANKER"
CONDENSE_QUESTON_PROMPT = "CONDENSE_QUESTON_PROMPT"

SETTINGS_RETRIAVAL: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=TOP_N_COUNT_DENSE, default_value=10, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=TOP_N_COUNT_SPARSE, default_value=10, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=TOP_N_COUNT_RERANKER, default_value=10, value_type=int, is_secret=False
    ),
]

SETTINGS: list[ConfigAttribute[Any]] = [
    FileConfigAttribute(
        name=SYSTEM_PROMPT_SIMPLE,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./prompts/rag_system_prompt_simple.txt",
    ),
    FileConfigAttribute(
        name=QUERY_WRAPPER_PROMPT,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./prompts/query_wrapper_prompt.txt",
    ),
    FileConfigAttribute(
        name=CONDENSE_QUESTON_PROMPT,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./prompts/condense_question_prompt.txt",
    ),
    EnvConfigAttribute(
        name=TOP_N_COUNT_DENSE, default_value=10, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=TOP_N_COUNT_SPARSE, default_value=10, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=TOP_N_COUNT_RERANKER, default_value=10, value_type=int, is_secret=False
    ),
]
