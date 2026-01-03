from core.config_loader import ConfigLoader
from deployment_base.enviroment.simple_rag import SYSTEM_PROMPT_SIMPLE
from deployment_base.enviroment.vllm_reranker import RERANK_MODEL
from deployment_base.enviroment import simple_rag, vllm_reranker, sub_question_rag
from domain.database.config.model import RagRetrievalConfig
from deployment_base.enviroment.sub_question_rag import (
    CONDENSE_QUESTON_PROMPT,
    QA_PROMPT,
    QUERY_WRAPPER_PROMPT,
    SUB_QUER_PROMPT,
    SUB_SYSTEM_PROMPT,
)


def update_graph(
    config: RagRetrievalConfig, config_loader: ConfigLoader
) -> RagRetrievalConfig:
    return config


def update_naive(
    config: RagRetrievalConfig, config_loader: ConfigLoader
) -> RagRetrievalConfig:
    result = config_loader.load_values([*simple_rag.SETTINGS, *vllm_reranker.SETTINGS])
    if result.is_error():
        raise result.get_error()

    rerank_model = config_loader.get_str(RERANK_MODEL)
    config.addition_information[RERANK_MODEL] = rerank_model

    keys = list(config.prompts.keys())
    for item in keys:
        config.prompts.pop(item)

    prompt_keys = [SYSTEM_PROMPT_SIMPLE, QUERY_WRAPPER_PROMPT, CONDENSE_QUESTON_PROMPT]
    for key in prompt_keys:
        config.prompts[key] = config_loader.get_str(key)

    return config


def update_sub(
    config: RagRetrievalConfig, config_loader: ConfigLoader
) -> RagRetrievalConfig:
    result = config_loader.load_values(
        [*sub_question_rag.SETTINGS, *vllm_reranker.SETTINGS]
    )
    if result.is_error():
        raise result.get_error()

    rerank_model = config_loader.get_str(RERANK_MODEL)
    config.addition_information[RERANK_MODEL] = rerank_model

    system_prompt = config_loader.get_str(SUB_SYSTEM_PROMPT)
    sub_query_prompt = config_loader.get_str(SUB_QUER_PROMPT)
    condense_question_prompt = config_loader.get_str(CONDENSE_QUESTON_PROMPT)
    qa_prompt = config_loader.get_str(QA_PROMPT)
    query_wrapper_prompt = config_loader.get_str(QUERY_WRAPPER_PROMPT)
    prompt_keys = [
        SUB_SYSTEM_PROMPT,
        SUB_QUER_PROMPT,
        CONDENSE_QUESTON_PROMPT,
        QA_PROMPT,
        QUERY_WRAPPER_PROMPT,
    ]
    prompts = [
        (system_prompt, SUB_SYSTEM_PROMPT),
        (sub_query_prompt, SUB_QUER_PROMPT),
        (condense_question_prompt, CONDENSE_QUESTON_PROMPT),
        (qa_prompt, QA_PROMPT),
        (query_wrapper_prompt, QUERY_WRAPPER_PROMPT),
    ]

    keys = list(config.prompts.keys())
    for key in keys:
        if key not in prompt_keys:
            config.prompts.pop(key)

    for prompt, key in prompts:
        if prompt != "":
            config.prompts[key] = prompt

    return config
