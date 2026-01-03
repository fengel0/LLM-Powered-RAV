from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute, FileConfigAttribute


SUB_SYSTEM_PROMPT = "SUB_SYSTEM_PROMPT"
SUB_QUER_PROMPT = "SUB_QUER_PROMPT"
CONDENSE_QUESTON_PROMPT = "CONDENSE_QUESTON_PROMPT"
QA_PROMPT = "QA_PROMPT"
QUERY_WRAPPER_PROMPT = "QUERY_WRAPPER_PROMPT"

TOP_N_COUNT_DENSE = "TOP_N_COUNT_DENSE"
TOP_N_COUNT_SPARSE = "TOP_N_COUNT_SPARSE"
TOP_N_COUNT_RERANKER = "TOP_N_COUNT_RERANKER"
SETTINGS: list[ConfigAttribute[Any]] = [
    FileConfigAttribute(
        name=SUB_SYSTEM_PROMPT,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./prompts/sub_rag_system_prompt.txt",
    ),
    FileConfigAttribute(
        name=SUB_QUER_PROMPT,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./prompts/sub_query_prompt.txt",
    ),
    FileConfigAttribute(
        name=CONDENSE_QUESTON_PROMPT,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./prompts/condense_question_prompt.txt",
    ),
    FileConfigAttribute(
        name=QA_PROMPT,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./prompts/qa_prompt.txt",
    ),
    FileConfigAttribute(
        name=QUERY_WRAPPER_PROMPT,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./prompts/query_wrapper_prompt.txt",
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
