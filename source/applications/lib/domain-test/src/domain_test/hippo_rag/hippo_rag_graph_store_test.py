# tests/test_graphdb_neo4j_async.py
import logging

# from neo4j import AsyncGraphDatabase
from domain.hippo_rag.model import Node, Edge
from domain_test import AsyncTestBase

from domain.hippo_rag.interfaces import GraphDBInterface

logger = logging.getLogger(__name__)

NEO4J_USER = "neo4j"
NEO4J_PASS = "ThisIsSomeDummyPassw0rd!"


class TestGraphDB(AsyncTestBase):
    db: GraphDBInterface

    async def test_add_nodes_and_query(self):
        nodes = [
            Node(hash_id="E:apple", content="apple", node_type="entity"),
            Node(hash_id="C:chunk1", content="Apple is a fruit.", node_type="chunk"),
        ]

        hashes = [node.hash_id for node in nodes]

        result = await self.db.get_not_existing_nodes(hashes)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        assert len(result.get_ok()) == 2

        result = await self.db.add_nodes(nodes)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        result_count = await self.db.get_node_count()
        if result_count.is_error():
            logger.error(result_count.get_error())
        assert result_count.is_ok()
        count = result_count.get_ok()
        assert count == 2

        result = await self.db.get_not_existing_nodes(hashes)
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        assert len(result.get_ok()) == 0

        vs_map_result = await self.db.get_vs_map()
        if vs_map_result.is_error():
            logger.error(vs_map_result.get_error())
        assert vs_map_result.is_ok()

        vs_map = vs_map_result.get_ok()
        assert "E:apple" in vs_map
        assert vs_map["E:apple"].content == "apple"

        names_result = await self.db.get_values_from_attributes("hash_id")
        if names_result.is_error():
            logger.error(names_result.get_error())
        assert names_result.is_ok()
        assert sorted(names_result.get_ok()) == ["C:chunk1", "E:apple"]

        idx_result = await self.db.get_vs_map_index()
        if idx_result.is_error():
            logger.error(idx_result.get_error())
        assert idx_result.is_ok()
        idx = idx_result.get_ok()
        assert sorted(idx.keys()) == ["C:chunk1", "E:apple"]
        assert idx["C:chunk1"] == 0
        assert idx["E:apple"] == 1

        result = await self.db.get_node_by_hash(hash_id="E:apple")
        if result.is_error():
            logger.error(result.get_error())
        obj = result.get_ok()
        assert obj is not None and obj.hash_id == "E:apple"

        result = await self.db.get_node_by_hash(hash_id="not-existing")
        if result.is_error():
            logger.error(result.get_error())
        assert result.get_ok() is None

    async def test_add_edges_and_defaults(self):
        result = await self.db.add_nodes(
            [
                Node(hash_id="A", content="A", node_type="entity"),
                Node(hash_id="B", content="B", node_type="entity"),
            ]
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        # No weight provided -> defaults to 1.0
        result = await self.db.add_edges([Edge(src="A", dst="B", weight=0.0)])
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        # Verify via direct Cypher

        result = await self.db.get_edges_of_node(hash_id="A")
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        edges = result.get_ok()
        assert len(edges) > 0
        edge = edges[0]

        assert abs(edge.weight) < 1e-9

        # Now with weight set in props
        result = await self.db.add_edges([Edge(src="A", dst="B", weight=2.5)])
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        result = await self.db.get_edges_of_node(hash_id="A")
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()
        edges = result.get_ok()
        assert len(edges) > 0
        edge = edges[0]

        assert edge.weight == 2.5  # type: ignore

    async def test_delete_vertices(self):
        result = await self.db.add_nodes(
            [
                Node(hash_id="X", content="X", node_type="entity"),
                Node(hash_id="Y", content="Y", node_type="entity"),
            ]
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        count_result = await self.db.get_node_count()
        if count_result.is_error():
            logger.error(count_result.get_error())
        assert count_result.is_ok()
        assert count_result.get_ok() == 2

        result = await self.db.delete_vertices(["X"])
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        count_result = await self.db.get_node_count()
        if count_result.is_error():
            logger.error(count_result.get_error())
        assert count_result.is_ok()
        assert count_result.get_ok() == 1

        remaining_result = await self.db.get_values_from_attributes("hash_id")
        if remaining_result.is_error():
            logger.error(remaining_result.get_error())
        assert remaining_result.is_ok()
        assert remaining_result.get_ok() == ["Y"]

    async def test_pagerank_gds_personalized(self):
        result = await self.db.add_nodes(
            [
                Node(hash_id="A", content="A", node_type="chunk"),
                Node(hash_id="B", content="B", node_type="chunk"),
                Node(hash_id="C", content="C", node_type="chunk"),
            ]
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        result = await self.db.add_edges(
            [
                Edge(src="A", dst="B", weight=1.0),
                Edge(src="B", dst="C", weight=1.0),
            ]
        )
        if result.is_error():
            logger.error(result.get_error())
        assert result.is_ok()

        pr_result = await self.db.personalized_pagerank(
            seeds={"A": 1.0},
            damping=0.85,
            top_k=10,
            directed=True,
        )
        if pr_result.is_error():
            logger.error(pr_result.get_error())
        assert pr_result.is_ok()
        pr = pr_result.get_ok()
        assert len(pr) == 3 and all(p >= 0 for p in pr.values())  # type: ignore

        pr_result = await self.db.personalized_pagerank(
            seeds={"A": 1.0},
            damping=0.85,
            top_k=10,
            directed=False,
        )
        if pr_result.is_error():
            logger.error(pr_result.get_error())
        assert pr_result.is_ok()
        pr = pr_result.get_ok()
        assert len(pr) == 3 and all(p >= 0 for p in pr.values())  # type: ignore

    # ---------------- new tests for get_chunk_node_connection_for_entity ---------------- #

    async def test_chunk_connections_for_entity_mixed_directions(self):
        nodes = [
            Node(hash_id="E:apple", content="apple", node_type="entity"),
            Node(hash_id="C:1", content="c1", node_type="chunk"),
            Node(hash_id="C:2", content="c2", node_type="chunk"),
        ]
        res = await self.db.add_nodes(nodes)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        res = await self.db.add_edges(
            [
                Edge(src="E:apple", dst="C:1", weight=1.0),
                Edge(src="C:2", dst="E:apple", weight=1.0),
            ]
        )
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        nodes_res = await self.db.get_chunk_node_connection_for_entity("E:apple")
        if nodes_res.is_error():
            logger.error(nodes_res.get_error())
        assert nodes_res.is_ok()
        chunks = nodes_res.get_ok()
        assert isinstance(chunks, list)
        assert [n.hash_id for n in chunks] == ["C:1", "C:2"]
        assert all(n.node_type == "chunk" for n in chunks)

    async def test_chunk_connections_for_entity_none(self):
        nodes = [Node(hash_id="E:solo", content="solo", node_type="entity")]
        res = await self.db.add_nodes(nodes)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        nodes_res = await self.db.get_chunk_node_connection_for_entity("E:solo")
        if nodes_res.is_error():
            logger.error(nodes_res.get_error())
        assert nodes_res.is_ok()
        assert nodes_res.get_ok() == []

    async def test_chunk_connections_for_entity_missing_entity(self):
        nodes_res = await self.db.get_chunk_node_connection_for_entity("E:none")
        if nodes_res.is_error():
            logger.error(nodes_res.get_error())
        assert nodes_res.is_ok()
        assert nodes_res.get_ok() == []

    # ---------------- tests for allowed_chunks filter ---------------- #

    async def test_chunk_connections_for_entity_allowed_filter_subset(self):
        nodes = [
            Node(hash_id="E:banana", content="banana", node_type="entity"),
            Node(hash_id="C:10", content="c10", node_type="chunk"),
            Node(hash_id="C:20", content="c20", node_type="chunk"),
        ]
        res = await self.db.add_nodes(nodes)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        res = await self.db.add_edges(
            [
                Edge(src="E:banana", dst="C:10", weight=1),
                Edge(src="C:20", dst="E:banana", weight=1),
            ]
        )
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        nodes_res = await self.db.get_chunk_node_connection_for_entity(
            "E:banana", allowed_chunks=["C:20"]
        )
        if nodes_res.is_error():
            logger.error(nodes_res.get_error())
        assert nodes_res.is_ok()
        chunks = nodes_res.get_ok()
        assert [n.hash_id for n in chunks] == ["C:20"]
        assert all(n.node_type == "chunk" for n in chunks)

    async def test_chunk_connections_for_entity_allowed_filter_empty_is_all(self):
        nodes = [
            Node(hash_id="E:cherry", content="cherry", node_type="entity"),
            Node(hash_id="C:100", content="c100", node_type="chunk"),
            Node(hash_id="C:200", content="c200", node_type="chunk"),
        ]
        res = await self.db.add_nodes(nodes)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        res = await self.db.add_edges(
            [
                Edge(src="E:cherry", dst="C:100", weight=1.0),
                Edge(src="C:200", dst="E:cherry", weight=1.0),
            ]
        )
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        nodes_res = await self.db.get_chunk_node_connection_for_entity(
            "E:cherry", allowed_chunks=[]
        )
        if nodes_res.is_error():
            logger.error(nodes_res.get_error())
        assert nodes_res.is_ok()
        chunks = nodes_res.get_ok()
        assert [n.hash_id for n in chunks] == ["C:100", "C:200"]

    async def test_chunk_connections_for_entity_allowed_filter_no_match(self):
        nodes = [
            Node(hash_id="E:date", content="date", node_type="entity"),
            Node(hash_id="C:xyz", content="cxyz", node_type="chunk"),
        ]
        res = await self.db.add_nodes(nodes)
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        res = await self.db.add_edges([Edge(src="E:date", dst="C:xyz", weight=1.0)])
        if res.is_error():
            logger.error(res.get_error())
        assert res.is_ok()

        nodes_res = await self.db.get_chunk_node_connection_for_entity(
            "E:date", allowed_chunks=["C:not-here"]
        )
        if nodes_res.is_error():
            logger.error(nodes_res.get_error())
        assert nodes_res.is_ok()
        assert nodes_res.get_ok() == []

    # ---------------- personalized_pagerank: allowed set & edge cases ---------------- #

    async def test_pagerank_gds_allowed_subset(self):
        # self.db = Neo4jGraphDB(
        # Neo4jConfig(
        # database="neo4j",
        # node_label="Node",
        # rel_type="LINKS",
        # ppr_implementation="neo4j-gds",
        # )
        # )
        # await self.db.start()

        res = await self.db.add_nodes(
            [
                Node(hash_id="H", content="H", node_type="chunk"),
                Node(hash_id="I", content="I", node_type="chunk"),
                Node(hash_id="J", content="J", node_type="chunk"),
            ]
        )
        assert res.is_ok()
        res = await self.db.add_edges(
            [
                Edge(src="H", dst="I", weight=1.0),
                Edge(src="I", dst="J", weight=1.0),
            ]
        )
        assert res.is_ok()

        pr_res = await self.db.personalized_pagerank(
            seeds={"H": 1.0},
            damping=0.85,
            directed=True,
            top_k=10,
            allowed_hash_ids=["H", "I"],
        )
        assert pr_res.is_ok(), pr_res.get_error() if pr_res.is_error() else ""
        pr = pr_res.get_ok()
        assert [h for h in pr.keys()] == ["H", "I"]
        assert all(s >= 0 for s in pr.values())

    async def test_pagerank_gds_allowed_empty_means_all(self):
        res = await self.db.add_nodes(
            [
                Node(hash_id="K", content="K", node_type="chunk"),
                Node(hash_id="L", content="L", node_type="chunk"),
                Node(hash_id="M", content="M", node_type="chunk"),
            ]
        )
        assert res.is_ok()
        res = await self.db.add_edges(
            [
                Edge(src="K", dst="L", weight=1.0),
                Edge(src="L", dst="M", weight=1.0),
            ]
        )
        assert res.is_ok()

        pr_res = await self.db.personalized_pagerank(
            seeds={"K": 1.0},
            damping=0.85,
            directed=True,
            top_k=10,
            allowed_hash_ids=[],  # empty -> no filter
        )
        assert pr_res.is_ok(), pr_res.get_error() if pr_res.is_error() else ""
        pr = pr_res.get_ok()
        assert [h for h in pr.keys()] == ["K", "L", "M"]
