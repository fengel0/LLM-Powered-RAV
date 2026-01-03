from __future__ import annotations
import random
import asyncio
import uuid
from opentelemetry import trace
from core.result import Result
import logging
from typing import Any, Literal

from core.singelton import BaseSingleton
from domain.hippo_rag.interfaces import GraphDBInterface
from domain.hippo_rag.model import Edge, Node
from neo4j import AsyncDriver, AsyncGraphDatabase
from pydantic import BaseModel

from hippo_rag_graph.queries import (
    fetch_sorted_ids_query,
    get_add_edges_query,
    get_add_nodes_query,
    get_chunk_node_connection_query,
    get_delete_nodes_query,
    get_edges_of_node_query,
    get_ensure_contrains_query,
    get_missing_hash_ids_query,
    get_node_by_hash_query,
    get_node_count_query,
    get_values_from_attribute_query,
    get_vs_map_ids_query,
    get_vs_map_query,
)

logger = logging.getLogger(__name__)


class Neo4jSessionConfig(BaseModel):
    uri: str
    user: str
    password: str


class Neo4jConfig(BaseModel):
    database: str = "neo4j"
    node_label: str = "Node"
    rel_type: str = "LINKS"
    ppr_implementation: Literal["neo4j-gds"] = "neo4j-gds"
    retries: int = 3


class Neo4jSession(BaseSingleton):
    _driver: AsyncDriver | None = None

    def _init_once(self, config: Neo4jSessionConfig):
        self._config = config

    def get_driver(self) -> AsyncDriver:
        assert self._driver, "connection not established"
        return self._driver

    async def start(self):
        self._driver = AsyncGraphDatabase.driver(
            self._config.uri, auth=(self._config.user, self._config.password)
        )

    async def shutdown(self) -> None:
        assert self._driver, "connection not established"
        await self._driver.close()


class Neo4jGraphDB(GraphDBInterface):
    _config: Neo4jConfig
    _driver: AsyncDriver

    def __init__(self, config: Neo4jConfig) -> None:
        self._config = config
        self._driver = Neo4jSession.Instance().get_driver()
        self.tracer = trace.get_tracer("Neo4jGraphDB")
        self._existing_dbs: set[str] = set()

    async def start(self):
        await self._ensure_constraints()
        await self._ensure_indices()

    # -------- tiny helpers so you don't copy-paste boilerplate -------- #

    async def _run_query(
        self, query: str, **params: Any
    ) -> Result[list[dict[str, Any]]]:
        delay = 0.1
        last_exception: Exception | None = None
        for _ in range(self._config.retries):
            try:
                with self.tracer.start_as_current_span("run-query"):
                    async with self._driver.session(
                        database=self._config.database
                    ) as session:
                        logger.debug(f"run query \n {query} with parameters {params}")
                        result = await session.run(query, **params)  # type: ignore
                        return Result.Ok(await result.data())  # list[dict[str, Any]]
            except Exception as e:
                # Only retry on transient errors (e.g., deadlocks)
                logger.warning(f"request {query} failed error{e}")
                await asyncio.sleep(delay + random.random() * 0.05)
                last_exception = e
                delay *= 2

        assert last_exception, "should never happend"
        return Result.Err(last_exception)

    async def _run_single_value(
        self, query: str, key: str, **params: Any
    ) -> Result[Any | None]:
        try:
            async with self._driver.session(database=self._config.database) as session:
                logger.debug(f"run query \n {query} with parameters {params}")
                result = await session.run(query, **params)  # type: ignore
                rec = await result.single()
                return Result.Ok(rec[key] if rec else None)
        except Exception as e:
            logger.error(e, exc_info=True)
            return Result.Err(e)

    async def _ensure_constraints(self) -> None:
        with self.tracer.start_as_current_span("ensure-constraints"):
            result = await self._run_query(
                get_ensure_contrains_query(self._config.node_label),
                label=self._config.node_label,
            )
            if result.is_error():
                raise result.get_error()

    async def _ensure_indices(self) -> None:
        """Erstellt notwendige Indices für bessere Performance und Schema-Awareness"""
        with self.tracer.start_as_current_span("ensure-indices"):
            # Index für node_type (löst Warning)
            index_result = await self._run_query(f"""
                CREATE INDEX node_type_index IF NOT EXISTS 
                FOR (n:{self._config.node_label}) ON (n.node_type)
            """)
            if index_result.is_error():
                logger.warning(
                    f"Could not create node_type index: {index_result.get_error()}"
                )

            # Index für hash_id (falls noch nicht da)
            hash_index_result = await self._run_query(f"""
                CREATE INDEX hash_id_index IF NOT EXISTS 
                FOR (n:{self._config.node_label}) ON (n.hash_id)
            """)
            if hash_index_result.is_error():
                logger.warning(
                    f"Could not create hash_id index: {hash_index_result.get_error()}"
                )
            warmup_result = await self._run_query(f"""
                MATCH ()-[r:{self._config.rel_type}]-() 
                RETURN count(r) AS rel_count LIMIT 1
            """)
            if warmup_result.is_error():
                logger.info(
                    "No relationships found yet - this is normal for empty databases"
                )

        logger.info("Schema indices and constraints ensured")

    # --------------- interface methods ---------------

    async def get_node_by_hash(
        self,
        hash_id: str,
    ) -> Result[Node | None]:
        with self.tracer.start_as_current_span("get-node-by-hash"):
            rows_result = await self._run_query(
                query=get_node_by_hash_query(self._config.node_label),
                hash_id=hash_id,
            )
            if rows_result.is_error():
                return rows_result.propagate_exception()
            rows = rows_result.get_ok()
            if len(rows) == 0:
                return Result.Ok(None)
            return Result.Ok(Node(**rows[0]))

    async def get_not_existing_nodes(
        self,
        hash_ids: list[str],
    ) -> Result[list[str]]:
        with self.tracer.start_as_current_span("get-not-existing-hosts"):
            rows_result = await self._run_query(
                query=get_missing_hash_ids_query(self._config.node_label),
                hash_ids=hash_ids,
            )
            if rows_result.is_error():
                return rows_result.propagate_exception()
            rows = rows_result.get_ok()
            return Result.Ok([row["hash_id"] for row in rows])  # type: ignore

    async def get_chunk_node_connection_for_entity(
        self,
        hash_id: str,
        allowed_chunks: list[str] | None = None,
    ) -> Result[list[Node]]:
        with self.tracer.start_as_current_span("get-chunk-nodes-for-entity"):
            if allowed_chunks is None:
                allowed_chunks = []
            rows_result = await self._run_query(
                get_chunk_node_connection_query(
                    self._config.node_label, self._config.rel_type
                ),
                hid=hash_id,
                allowed=allowed_chunks,
            )
            if rows_result.is_error():
                return rows_result.propagate_exception()

            rows = rows_result.get_ok() or []
            # If entity doesn't exist or has no chunk neighbors, this is just [].
            return Result.Ok([Node(**r) for r in rows])

    async def delete_vertices(self, verticies: list[str]) -> Result[None]:
        with self.tracer.start_as_current_span("delete-vertices"):
            if not verticies:
                return Result.Ok()
            result = await self._run_query(
                get_delete_nodes_query(self._config.node_label), ids=verticies
            )
            if result.is_error():
                return result.propagate_exception()
            return Result.Ok()

    async def get_values_from_attributes(
        self,
        key: str,
    ) -> Result[list[str]]:
        with self.tracer.start_as_current_span("get-values-from-attributes"):
            prop = key
            if prop not in {"hash_id", "content", "chunk", "node_type"}:
                return Result.Err(
                    ValueError(f"Unsupported property for retrieval: {key}")
                )
            query = get_values_from_attribute_query(self._config.node_label, prop)
            rows_result = await self._run_query(query)
            if rows_result.is_error():
                return rows_result.propagate_exception()
            rows = rows_result.get_ok()
            return Result.Ok([r["v"] for r in rows])

    async def get_vs_map(
        self,
    ) -> Result[dict[str, Node]]:
        with self.tracer.start_as_current_span("get-vs-map"):
            rows_result = await self._run_query(
                get_vs_map_query(self._config.node_label)
            )
            if rows_result.is_error():
                return rows_result.propagate_exception()
            rows = rows_result.get_ok()
            return Result.Ok({r["hash_id"]: Node(**r) for r in rows})

    async def get_vs_map_index(
        self,
    ) -> Result[dict[str, int]]:
        with self.tracer.start_as_current_span("get-vs-map-index"):
            rows_result = await self._run_query(
                get_vs_map_ids_query(self._config.node_label)
            )
            if rows_result.is_error():
                return rows_result.propagate_exception()
            rows = rows_result.get_ok()
            ids = [r["id"] for r in rows]
            return Result.Ok({hid: i for i, hid in enumerate(ids)})

    async def add_nodes(self, nodes: list[Node]) -> Result[None]:
        with self.tracer.start_as_current_span("add-nodes"):
            if not nodes:
                return Result.Ok()
            rows = [n.model_dump() for n in nodes]
            result = await self._run_query(
                get_add_nodes_query(self._config.node_label), rows=rows
            )
            if result.is_error():
                return result.propagate_exception()
            return Result.Ok()

    async def get_edges_of_node(self, hash_id: str) -> Result[list[Edge]]:
        """
        Return all incident edges (both outgoing and incoming) for the node with the given hash_id.
        Each edge is represented as (src, dst, weight), where src/dst are hash_ids.
        """
        with self.tracer.start_as_current_span("get-edges-of-node"):
            query = get_edges_of_node_query(self._config.node_label)
            rows_result = await self._run_query(query, hid=hash_id)
            if rows_result.is_error():
                return rows_result.propagate_exception()

            rows = rows_result.get_ok() or []
            try:
                edges = [
                    Edge(src=row["src"], dst=row["dst"], weight=float(row["weight"]))
                    for row in rows
                ]
            except Exception as e:
                logger.error(
                    f"Failed to parse edges for node {hash_id}: {e}", exc_info=True
                )
                return Result.Err(e)

            return Result.Ok(edges)

    async def add_edges(self, edges: list[Edge]) -> Result[None]:
        with self.tracer.start_as_current_span("add-edges"):
            if not edges:
                return Result.Ok()
            payload = [
                e.model_dump() if hasattr(e, "model_dump") else e.__dict__
                for e in edges
            ]

            result = await self._run_query(
                get_add_edges_query(self._config.node_label, self._config.rel_type),
                edges=payload,
            )
            if result.is_error():
                return result.propagate_exception()
            return Result.Ok()

    async def get_node_count(
        self,
    ) -> Result[int]:
        with self.tracer.start_as_current_span("get-node-count"):
            result = await self._run_single_value(
                get_node_count_query(self._config.node_label),
                "c",
            )
            if result.is_error():
                return result.propagate_exception()
            return Result.Ok(int(result.get_ok() or 0))

    # --------------- PageRank ---------------

    async def personalized_pagerank(
        self,
        seeds: dict[str, float],
        damping: float,
        top_k: int,
        directed: bool = True,
        allowed_hash_ids: list[str] | None = None,
    ) -> Result[dict[str, float]]:
        return await self._personalized_pagerank_gds(
            seeds, damping, top_k, directed, allowed_hash_ids
        )

    async def _fetch_sorted_ids(
        self, allowed: list[str] | None = None
    ) -> Result[list[str]]:
        allowed = allowed or []
        rows_res = await self._run_query(
            fetch_sorted_ids_query(self._config.node_label),
            allowed=allowed,
        )
        if rows_res.is_error():
            return rows_res.propagate_exception()
        rows = rows_res.get_ok() or []
        return Result.Ok([r["id"] for r in rows])

    async def _personalized_pagerank_gds(
        self,
        seeds: dict[str, float],  # hash_id -> weight
        damping: float,
        top_k: int,
        directed: bool = True,
        allowed_hash_ids: list[str] | None = None,
    ) -> Result[dict[str, float]]:
        if allowed_hash_ids is None:
            allowed_hash_ids = []
        graph_name = f"tmp_pr_{uuid.uuid4().hex[:8]}"
        try:
            async with self._driver.session(database=self._config.database) as session:
                # 1. Graph projizieren mit Gewichten - UPDATED with directed/undirected support
                if allowed_hash_ids:
                    # For custom node/relationship filtering, we need to use cypher projection
                    if directed:
                        await session.run(
                            f""" 
                                MATCH (n:{self._config.node_label})
                                WHERE size($allowed) = 0 OR n.hash_id IN $allowed
                                OPTIONAL MATCH (n:{self._config.node_label})-[r:{self._config.rel_type}]->(m:{self._config.node_label})
                                WHERE size($allowed) = 0 OR m.hash_id IN $allowed
                                WITH gds.graph.project(
                                    $graphName, 
                                    n, 
                                    m, 
                                    {{
                                        relationshipProperties: {{
                                            weight: coalesce(r.weight, 1.0)
                                        }}
                                    }}
                                ) AS g
                                RETURN g.graphName AS graphName, g.nodeCount AS nodeCount, g.relationshipCount AS relationshipCount
                                """,
                            graphName=graph_name,
                            allowed=allowed_hash_ids,
                        )
                    else:
                        # For undirected, we need to match relationships in both directions
                        await session.run(
                            f"""
                                MATCH (n:{self._config.node_label})
                                WHERE size($allowed) = 0 OR n.hash_id IN $allowed
                                OPTIONAL MATCH (n:{self._config.node_label})-[r:{self._config.rel_type}]-(m:{self._config.node_label})
                                WHERE size($allowed) = 0 OR m.hash_id IN $allowed
                                WITH gds.graph.project(
                                    $graphName, 
                                    n, 
                                    m, 
                                    {{
                                        relationshipProperties: {{
                                            weight: coalesce(r.weight, 1.0)
                                        }}
                                    }}
                                ) AS g
                                RETURN g.graphName AS graphName, g.nodeCount AS nodeCount, g.relationshipCount AS relationshipCount
                                """,
                            graphName=graph_name,
                            allowed=allowed_hash_ids,
                        )
                else:
                    # Standard-Projektion mit Gewichten und Orientierung
                    if directed:
                        await session.run(
                            """
                                CALL gds.graph.project(
                                    $graphName, 
                                    $nodeLabel, 
                                    $relType,
                                    {
                                        relationshipProperties: {
                                            weight: {
                                                property: 'weight',
                                                defaultValue: 1.0
                                            }
                                        }
                                    }
                                )
                                """,
                            graphName=graph_name,
                            nodeLabel=self._config.node_label,
                            relType=self._config.rel_type,
                        )
                    else:
                        # For undirected relationships, use the extended syntax with orientation
                        await session.run(
                            """
                                CALL gds.graph.project(
                                    $graphName, 
                                    $nodeLabel, 
                                    {
                                        REL_TYPE: {
                                            type: $relType,
                                            orientation: 'UNDIRECTED',
                                            properties: {
                                                weight: {
                                                    property: 'weight',
                                                    defaultValue: 1.0
                                                }
                                            }
                                        }
                                    }
                                )
                                """.replace("REL_TYPE", self._config.rel_type),
                            graphName=graph_name,
                            nodeLabel=self._config.node_label,
                            relType=self._config.rel_type,
                        )

                # 2. PageRank mit Gewichten ausführen - No changes needed here
                result = await session.run(
                    f"""
                        WITH $seeds AS seedsParam
                        UNWIND keys(seedsParam) AS hashId
                        MATCH (n:{self._config.node_label}) WHERE n.hash_id = hashId
                        WITH collect([n, toFloat(seedsParam[hashId])]) AS sourceNodes
                        
                        CALL gds.pageRank.stream($graphName, {{
                            dampingFactor: $damping,
                            sourceNodes: sourceNodes,
                            relationshipWeightProperty: 'weight'
                        }})
                        YIELD nodeId, score 
                        WITH gds.util.asNode(nodeId) AS n, score
                        WHERE n.node_type = 'chunk'
                        RETURN  n.hash_id AS hash_id,
                                n.node_type AS node_type, 
                                score 
                        ORDER BY score DESC
                        LIMIT $limit
                    """,
                    seeds=seeds,
                    graphName=graph_name,
                    damping=damping,
                    limit=top_k,
                )
                records = await result.data()
                scores = {str(r["hash_id"]): float(r["score"]) for r in records}
                return Result.Ok(scores)
        except Exception as e:
            logger.error(f"PageRank error: {e}", exc_info=True)
            return Result.Err(e)
        finally:
            try:
                async with self._driver.session(
                    database=self._config.database
                ) as session:
                    await session.run(
                        "CALL gds.graph.drop($graphName) YIELD graphName",
                        graphName=graph_name,
                    )
            except Exception as e:
                logger.warning(
                    f"failed to remove tmp graph {graph_name} \n Error:{e}",
                    exc_info=True,
                )
                pass
