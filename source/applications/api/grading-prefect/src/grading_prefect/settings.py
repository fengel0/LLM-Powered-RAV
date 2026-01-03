from core.config_loader import ConfigAttribute, EnvConfigAttribute, FileConfigAttribute
from rest_client.async_client import Any

SYSTEM_PROMPT_COMPLETENESS = "SYSTEM_PROMPT_COMPLETNESS"
SYSTEM_PROMPT_COMPLETENESS_CONTEXT = "SYSTEM_PROMPT_COMPLETNESS_CONTEXT"
SYSTEM_PROMPT_CORRECTNESS = "SYSTEM_PROMPT_CORRECTNES"
GRADING_CONFIG = "GRADING_CONFIG"
PROMPT = "PROMPT"

FACT_MODEL = "FACT_MODEL"
PARALLEL_REQUESTS = "PARALLEL_REQUESTS"
PARALLEL_LLM_CALLS = "PARALLEL_LLM_CALLS"

SYSTEM_NAME = "SYSTEM_NAME"


EVAL_TYPE = "EVAL_TYPE"

API_VERSION = "0.2.0"
API_NAME = "grading-prefrect-deployment"


SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=EVAL_TYPE, default_value="local", value_type=str, is_secret=False
    ),
    EnvConfigAttribute(
        name=PARALLEL_REQUESTS, default_value=1, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=PARALLEL_LLM_CALLS, default_value=1, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=FACT_MODEL, default_value=None, value_type=str, is_secret=False
    ),
    #
    FileConfigAttribute(
        name=SYSTEM_PROMPT_COMPLETENESS,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./prompts/grading_system_prompt.txt",
    ),
    FileConfigAttribute(
        name=SYSTEM_PROMPT_COMPLETENESS_CONTEXT,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./prompts/grading_system_prompt_context.txt",
    ),
    FileConfigAttribute(
        name=SYSTEM_PROMPT_CORRECTNESS,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./prompts/grading_system_prompt_correctness.txt",
    ),
    FileConfigAttribute(
        name=GRADING_CONFIG,
        default_value="",
        value_type=str,
        is_secret=False,
        file_location="./config/grading_config.json",
    ),
]
