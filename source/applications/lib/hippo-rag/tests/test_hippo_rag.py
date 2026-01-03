import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from core.result import Result
from domain.rag.model import RoleType
from hippo_rag.implementation import HippoRAG, HippoRAGConfig
from domain_test import AsyncTestBase


# Helpers to make tiny, typed-ish structs without pulling your whole domain in
def sim_node(id, score, payload):
    return SimpleNamespace(id=id, score=score, payload=payload)


def chunk_row(idx, passage, metadata=None):
    return SimpleNamespace(idx=idx, passage=passage, metadata=metadata or {})


def state_doc(idx, passage, triples, metadata=None):
    return SimpleNamespace(
        idx=idx, passage=passage, extracted_triples=triples, metadata=metadata or {}
    )


class TestHippoRAG(AsyncTestBase):
    __test__ = True

    def setup_method_sync(self, test_name: str):
        self.vs_entity = AsyncMock()
        self.vs_chunk = AsyncMock()
        self.vs_fact = AsyncMock()
        self.llm = AsyncMock()
        self.graph = AsyncMock()
        self.reranker = AsyncMock()
        self.state = AsyncMock()

        self.cfg = HippoRAGConfig(
            retrieval_top_k=5,
            linking_top_k=3,
            passage_node_weight=0.05,
            qa_top_k=2,
            damping=0.85,
            system_config="You are a QA system.",
        )

        self.sut = HippoRAG(
            vector_store_entity=self.vs_entity,
            vector_store_chunk=self.vs_chunk,
            vector_store_fact=self.vs_fact,
            llm=self.llm,
            graph=self.graph,
            filter=self.reranker,
            state_store=self.state,
            config=self.cfg,
        )

    def test_top_k_seeds_sparse_and_dense(self):
        weights = {"a": 0.1, "b": 0.9, "c": 0.5}
        top_sparse = self.sut.top_k_seeds(weights, k=2, sparse=True)
        assert set(top_sparse.keys()) == {"b", "c"}
        assert top_sparse["b"] >= top_sparse["c"]

        top_dense = self.sut.top_k_seeds(weights, k=1, sparse=False)
        assert top_dense["b"] == weights["b"]
        assert top_dense["a"] == 0.0
        assert top_dense["c"] == 0.0

    @patch(
        "hippo_rag.implementation.literal_eval",
        side_effect=[("A", "r", "B"), ("C", "r", "D"), ("E", "r", "F")],
    )
    async def test_rerank_facts_parses_and_orders(self, _):
        hits = [
            sim_node("h1", 0.3, "('A','r','B')"),
            sim_node("h2", 0.7, "('C','r','D')"),
            sim_node("h3", 0.9, "('E','r','F')"),
        ]
        self.reranker.rerank.return_value = Result.Ok(
            ([0, 2], [("E", "r", "F"), ("A", "r", "B")], SimpleNamespace())
        )

        top_ids, top_facts, log = (await self.sut._rerank_facts("query", hits)).get_ok()
        assert [t.id for t in top_ids] == ["h3", "h1"]
        assert top_facts == [("E", "r", "F"), ("A", "r", "B")]
        self.reranker.rerank.assert_awaited()

    async def test_retrieve_dpr_fallback_when_no_facts(self):
        with (
            patch(
                "hippo_rag.implementation.compute_mdhash_id",
                side_effect=lambda content, prefix="": f"h:{content}",
            ),
            patch.object(self.sut, "_search_passages") as mock_search_passages,
            patch.object(self.sut, "_rerank_facts") as mock_rerank_facts,
        ):
            triples = [("Alice", "knows", "Bob")]
            docs = [
                state_doc(idx="ch1", passage="P1", triples=triples, metadata={"m": 1}),
                state_doc(idx="ch2", passage="P2", triples=triples, metadata={"m": 2}),
            ]

            self.state.load_openie_info_with_metadata.return_value = Result.Ok(
                SimpleNamespace(docs=docs)
            )
            self.vs_fact.query.return_value = Result.Ok(
                [sim_node("t1", 0.8, "('Alice','knows','Bob')")]
            )
            mock_rerank_facts.return_value = Result.Ok(([], [], SimpleNamespace()))
            mock_search_passages.return_value = Result.Ok({"ch2": 0.9, "ch1": 0.3})
            self.state.fetch_chunks_by_ids.return_value = Result.Ok(
                SimpleNamespace(
                    docs=[
                        chunk_row("ch1", "P1", {"m": 1}),
                        chunk_row("ch2", "P2", {"m": 2}),
                    ]
                )
            )

            res = await self.sut.retrieve(queries=["who"], metadata={"k": ["v"]})
            assert not inspect.iscoroutine(res)
            assert res.is_ok(), res

            sol = res.get_ok()[0]
            assert sol.question == "who"
            assert [d.id for d in sol.docs] == ["ch2", "ch1"]
            assert sol.docs[0].score >= sol.docs[1].score
            mock_search_passages.assert_awaited_once()
            mock_rerank_facts.assert_awaited_once()

    @patch("hippo_rag.implementation.compute_mdhash_id", side_effect=lambda s: f"h:{s}")
    async def test_retrieve_graph_path_with_facts(self, _):
        triples = [("Alice", "knows", "Bob"), ("Bob", "visits", "Rome")]
        docs = [
            state_doc(idx="ch1", passage="P1", triples=triples),
            state_doc(idx="ch2", passage="P2", triples=triples),
        ]
        self.state.load_openie_info_with_metadata.return_value = Result.Ok(
            SimpleNamespace(docs=docs)
        )

        self.vs_fact.query.return_value = Result.Ok(
            [
                sim_node("t1", 0.9, "('Alice','knows','Bob')"),
                sim_node("t2", 0.7, "('Bob','visits','Rome')"),
                sim_node("t3", 0.1, "('noise','r','x')"),
            ]
        )
        self.reranker.rerank.return_value = Result.Ok(
            (
                [0, 1],
                [("Alice", "knows", "Bob"), ("Bob", "visits", "Rome")],
                SimpleNamespace(),
            )
        )
        self.graph.get_node_by_hash.side_effect = lambda hash_id: Result.Ok(
            SimpleNamespace(hash_id=hash_id)
        )
        self.graph.get_chunk_node_connection_for_entity.return_value = Result.Ok(
            [
                SimpleNamespace(hash_id="ch1"),
                SimpleNamespace(hash_id="ch2"),
            ]
        )
        self.vs_chunk.query.return_value = Result.Ok(
            [
                SimpleNamespace(id="ch1", score=0.6),
                SimpleNamespace(id="ch2", score=0.2),
            ]
        )
        self.graph.personalized_pagerank.return_value = Result.Ok(
            {
                "ch2": 0.8,
                "ch1": 0.4,
            }
        )
        self.state.fetch_chunks_by_ids.return_value = Result.Ok(
            SimpleNamespace(
                docs=[
                    chunk_row("ch1", "P1", {"a": 1}),
                    chunk_row("ch2", "P2", {"b": 2}),
                ]
            )
        )

        res = await self.sut.retrieve(queries=["where"], metadata={"k": ["v"]})
        assert res.is_ok(), res
        sol = res.get_ok()[0]
        assert [d.id for d in sol.docs] == ["ch2", "ch1"]
        self.graph.personalized_pagerank.assert_awaited()

    @patch("hippo_rag.implementation.DEFAULT_RAG_QA_SYSTEM", "SYS")
    async def test_request_single_message_happy_path(self):
        from domain.rag.model import Node, Message
        from domain.rag.interface import Conversation

        doc1 = SimpleNamespace(id="ch1", content="P1", score=0.9, metadata={"x": 1})
        doc2 = SimpleNamespace(id="ch2", content="P2", score=0.5, metadata={"y": 2})
        qs = SimpleNamespace(question="q", docs=[doc1, doc2])
        self.sut.retrieve = AsyncMock(return_value=Result.Ok([qs]))
        self.llm.stream_chat.return_value = Result.Ok("STREAM_HANDLE")

        conv = Conversation(
            messages=[Message(role=RoleType.User, message="q")], model="hi"
        )
        out = await self.sut.request(conv)

        assert out.is_ok(), out
        resp = out.get_ok()
        assert [n.id for n in resp.nodes] == ["ch1", "ch2"]
        assert resp.generator == "STREAM_HANDLE"
        called_msgs = self.llm.stream_chat.call_args[0][0]
        assert called_msgs[0].role == "system"
        assert called_msgs[1].role == "user"
        assert "Retrived Information: P1" in called_msgs[1].content
        assert "Retrived Information: P2" in called_msgs[1].content
        assert "Question: q" in called_msgs[1].content
