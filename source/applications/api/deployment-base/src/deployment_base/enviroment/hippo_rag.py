from typing import Any
from core.config_loader import ConfigAttribute, EnvConfigAttribute, FileConfigAttribute


TOP_N_HIPPO_RAG = "TOP_N_HIPPO_RAG"
TOP_N_LINKINIG = "TOP_N_LINKINIG"
PASSAGE_NODE_WEIGHT = "PASSAGE_NODE_WEIGHT"
QA_TOP_N = "QA_TOP_N"
CHUNKS_TO_RETRIEVE_PPR_SEED = "CHUNKS_TO_RETRIEVE_PPR_SEED"
DAMPING = "DAMPING"
PPR_DIRECTED = "PPR_DIRECTED"
EMBEDDING_SIZE = "EMBEDDING_SIZE"

SYNONYME_EDEGE_TOP_N = "SYNONYME_EDEGE_TOP_N"
SYNONYMY_EDGE_SIM_THRESHOLD = "SYNONYMY_EDGE_SIM_THRESHOLD"

SETTINGS: list[ConfigAttribute[Any]] = [
    EnvConfigAttribute(
        name=EMBEDDING_SIZE,
        default_value=1024,
        value_type=int,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=EMBEDDING_SIZE, default_value=None, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=SYNONYME_EDEGE_TOP_N, default_value=5, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=PPR_DIRECTED, default_value=False, value_type=bool, is_secret=False
    ),
    EnvConfigAttribute(
        name=PASSAGE_NODE_WEIGHT, default_value=0.5, value_type=float, is_secret=False
    ),
    EnvConfigAttribute(
        name=CHUNKS_TO_RETRIEVE_PPR_SEED,
        default_value=100,
        value_type=float,
        is_secret=False,
    ),
    EnvConfigAttribute(
        name=DAMPING, default_value=0.5, value_type=float, is_secret=False
    ),
    EnvConfigAttribute(name=QA_TOP_N, default_value=5, value_type=int, is_secret=False),
    EnvConfigAttribute(
        name=TOP_N_HIPPO_RAG, default_value=5, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=TOP_N_LINKINIG, default_value=5, value_type=int, is_secret=False
    ),
    EnvConfigAttribute(
        name=SYNONYMY_EDGE_SIM_THRESHOLD,
        default_value=0.9,
        value_type=float,
        is_secret=False,
    ),
]
