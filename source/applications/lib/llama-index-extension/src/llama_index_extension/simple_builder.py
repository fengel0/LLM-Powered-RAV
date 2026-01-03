from dataclasses import dataclass
import logging
from domain.rag.model import (
    AsyncRerankerClient,
)
from domain.text_embedding.interface import EmbeddClient
from llama_index.core import (
    ChatPromptTemplate,
    PromptTemplate,
    SelectorPromptTemplate,
    get_response_synthesizer,  # type: ignore
)
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.base.llms.base import BaseLLM
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.prompts import ChatMessage, MessageRole, PromptType
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.vector_stores.types import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)

from llama_index.core.chat_engine.types import (
    BaseChatEngine,
    ChatMode,
)
from llama_index_extension.build_components import LLamaIndexHolder
from llama_index_extension.embedding import CustomEmbedding


from llama_index_extension.prompts import (
    DEFAULT_CONDENSE_TEMPLATE,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEXT_WRAPPER_TMPL,
)

logger = logging.getLogger(__name__)


@dataclass
class LlamaIndexSimpleBuilderConfig:
    reranker: AsyncRerankerClient
    embedding: EmbeddClient

    top_n_count_reranker: int
    top_n_count_dens: int
    top_n_count_sparse: int

    context_window: int
    llm_model: str
    temperatur: float
    sparse_model: str = "Qdrant/bm25"

    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    query_wrapper_prompt: str = DEFAULT_TEXT_WRAPPER_TMPL
    condense_question_prompt: str = DEFAULT_CONDENSE_TEMPLATE


class LlamaIndexSimpleBuilder:
    reranker: BaseNodePostprocessor
    embedding: BaseEmbedding
    llm: FunctionCallingLLM

    def __init__(self, config: LlamaIndexSimpleBuilderConfig) -> None:
        self.config = config
        self.reranker = LLamaIndexHolder.Instance().get_custom_reranker(
            self.config.reranker, self.config.top_n_count_reranker
        )
        self.embedding = CustomEmbedding(self.config.embedding)
        self.llm = LLamaIndexHolder.Instance().get_llm(
            self.config.llm_model, self.config.temperatur, self.config.context_window
        )

    def get_chat_enging(
        self,
        model: str | None,
        metadata_filters: dict[str, list[str] | list[int] | list[float]] | None = None,
        collection: str | None = None,
    ) -> BaseChatEngine:
        metadata_filters = metadata_filters if metadata_filters else {}
        filters = MetadataFilters(filters=[])
        for key in metadata_filters.keys():
            for value in metadata_filters[key]:
                filters.filters.append(
                    MetadataFilter(key=key, value=value, operator=FilterOperator.EQ)
                )
        filters.condition = FilterCondition.OR

        top_k_dens = self.config.top_n_count_dens
        top_k_sparse = self.config.top_n_count_sparse

        reranker = self.reranker
        embbedder = self.embedding
        temperatur = self.config.temperatur

        chat_history = [
            ChatMessage(content=self.config.system_prompt, role=MessageRole.SYSTEM),
            ChatMessage(
                content=self.config.query_wrapper_prompt, role=MessageRole.USER
            ),
        ]

        def is_chat_model(llm: BaseLLM) -> bool:
            return True

        default_text_qa_conditionals = [
            (is_chat_model, ChatPromptTemplate(message_templates=chat_history))
        ]
        prompt_template = SelectorPromptTemplate(
            default_template=PromptTemplate(
                self.config.query_wrapper_prompt, prompt_type=PromptType.QUESTION_ANSWER
            ),
            conditionals=default_text_qa_conditionals,
        )

        if model:
            llm = LLamaIndexHolder.Instance().get_llm(
                model=model,
                temperatur=temperatur,
                context_window=self.config.context_window,
            )
        else:
            llm = self.llm

        return (
            LLamaIndexHolder.Instance()
            .get_index(
                collection=collection,
                embedding_model=embbedder,
                sparse_model=self.config.sparse_model,
                top_k_sparse=top_k_sparse,
                top_k_dense=top_k_dens,
            )
            .as_chat_engine(  # type: ignore
                llm=llm,
                chat_mode=ChatMode.CONDENSE_QUESTION,
                similarity_top_k=top_k_dens,
                sparse_top_k=top_k_sparse,
                condense_question_prompt=PromptTemplate(
                    template=self.config.condense_question_prompt
                ),
                response_synthesizer=get_response_synthesizer(
                    llm=llm,
                    text_qa_template=prompt_template,
                    response_mode=ResponseMode.SIMPLE_SUMMARIZE,
                    use_async=True,
                    verbose=True,
                ),
                node_postprocessors=[reranker],
                vector_store_query_mode="hybrid",
                filters=filters,
                use_async=True,
            )
        )
