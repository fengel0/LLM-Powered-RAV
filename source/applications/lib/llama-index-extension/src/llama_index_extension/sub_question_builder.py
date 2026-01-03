from dataclasses import dataclass
import logging
from domain.rag.model import (
    AsyncRerankerClient,
    EmbeddClient,
)
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.base.llms.base import BaseLLM
from llama_index.core.chat_engine import CondenseQuestionChatEngine
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.prompts import PromptType
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.query_engine import SubQuestionQueryEngine
from llama_index.core.question_gen.llm_generators import LLMQuestionGenerator
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.tools.query_engine import QueryEngineTool
from llama_index.core.tools.types import ToolMetadata
from llama_index.core.vector_stores.types import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)

from llama_index.core.chat_engine.types import (
    BaseChatEngine,
    ChatResponseMode,
)
from llama_index_extension.build_components import LLamaIndexHolder
from llama_index_extension.mock_llm import MockLLM
from llama_index_extension.embedding import CustomEmbedding


from llama_index.core import (
    ChatPromptTemplate,
    PromptTemplate,
    SelectorPromptTemplate,
    get_response_synthesizer,  # type: ignore
)

from llama_index_extension.prompts import (
    DEFAULT_CONDENSE_TEMPLATE,
    DEFAULT_SUB_PROMPT,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEXT_QA_PROMPT_TMPL,
    DEFAULT_TEXT_WRAPPER_TMPL,
)

logger = logging.getLogger(__name__)


@dataclass
class LlamaIndexSubQuestionBuilderConfig:
    reranker: AsyncRerankerClient
    embedding: EmbeddClient

    top_n_count_dens: int
    top_n_count_sparse: int
    top_n_count_reranker: int

    context_window: int
    llm_model: str
    temperatur: float
    sparse_model: str = "Qdrant/bm25"

    sub_query_prompt: str = DEFAULT_SUB_PROMPT
    condense_question_prompt: str = DEFAULT_CONDENSE_TEMPLATE
    qa_prompt: str = DEFAULT_TEXT_QA_PROMPT_TMPL
    query_wrapper_prompt: str = DEFAULT_TEXT_WRAPPER_TMPL
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


class LlamaIndexSubQuestionBuilder:
    reranker: BaseNodePostprocessor
    embedding: BaseEmbedding
    llm: FunctionCallingLLM

    def __init__(self, config: LlamaIndexSubQuestionBuilderConfig) -> None:
        self.config = config
        self.reranker = LLamaIndexHolder.Instance().get_custom_reranker(
            self.config.reranker, self.config.top_n_count_reranker
        )
        self.embedding = CustomEmbedding(self.config.embedding)
        self.llm = LLamaIndexHolder.Instance().get_llm(
            self.config.llm_model, self.config.temperatur, self.config.context_window
        )

    def get_decompose_engine(
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

        sub_query_prompt = self.config.sub_query_prompt
        condense_question_prompt = self.config.condense_question_prompt
        qa_prompt = self.config.qa_prompt
        system_prompt = self.config.system_prompt
        query_wrapper_prompt = self.config.query_wrapper_prompt

        reranker = self.reranker
        embbedder = self.embedding

        chat_history = [
            ChatMessage(content=system_prompt, role=MessageRole.SYSTEM),
            ChatMessage(content=query_wrapper_prompt, role=MessageRole.USER),
        ]

        def is_chat_model(llm: BaseLLM) -> bool:
            return True

        default_text_qa_conditionals = [
            (is_chat_model, ChatPromptTemplate(message_templates=chat_history))
        ]
        prompt_template = SelectorPromptTemplate(
            default_template=PromptTemplate(
                query_wrapper_prompt, prompt_type=PromptType.QUESTION_ANSWER
            ),
            conditionals=default_text_qa_conditionals,
        )

        temperatur = self.config.temperatur

        if model:
            llm = LLamaIndexHolder.Instance().get_llm(
                model=model,
                temperatur=temperatur,
                context_window=self.config.context_window,
            )
        else:
            llm = self.llm

        query_engine = (
            LLamaIndexHolder.Instance()
            .get_index(
                collection=collection,
                embedding_model=embbedder,
                sparse_model=self.config.sparse_model,
                top_k_sparse=top_k_sparse,
                top_k_dense=top_k_dens,
            )
            .as_query_engine(  # type: ignore
                # llm=llm,
                MockLLM(
                    context_window=self.config.context_window
                ),  # nessary to let the query_engine know that the llm can handle the context
                similarity_top_k=top_k_dens,
                sparse_top_k=top_k_sparse,
                node_postprocessors=[reranker],
                vector_store_query_mode="hybrid",
                filters=filters,
                use_async=True,
                text_qa_template=PromptTemplate(qa_prompt),
            )
        )  # type: ignore
        query_engine_tools = [
            QueryEngineTool(
                query_engine=query_engine,
                metadata=ToolMetadata(
                    name="Vektor Store",
                    description="Containing all Documents",
                ),
            )
        ]

        decompose_engine = SubQuestionQueryEngine.from_defaults(
            query_engine_tools=query_engine_tools,
            question_gen=LLMQuestionGenerator.from_defaults(
                llm=llm,
                prompt_template_str=sub_query_prompt,
            ),
            response_synthesizer=get_response_synthesizer(
                llm=llm,
                text_qa_template=prompt_template,
                response_mode=ResponseMode.SIMPLE_SUMMARIZE,
                use_async=True,
                streaming=True,
                verbose=True,
            ),
            llm=llm,
            use_async=True,
            verbose=True,
        )
        chat_engine = CondenseQuestionChatEngine.from_defaults(
            query_engine=decompose_engine,
            condense_question_prompt=PromptTemplate(template=condense_question_prompt),
            llm=llm,
            chat_response_mode=ChatResponseMode.STREAM,
            use_async=True,
            verbose=True,
            is_dummy_stream=True,
            # system_prompt=system_prompt, -> not Supported
        )
        return chat_engine
