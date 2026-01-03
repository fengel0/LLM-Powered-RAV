rel_type: str = "LINKS"


def get_ensure_contrains_query(node_label: str) -> str:
    return f"CREATE CONSTRAINT node_hash_id_unique IF NOT EXISTS FOR (n:{node_label}) REQUIRE n.hash_id IS UNIQUE"


def get_node_by_hash_query(node_label: str) -> str:
    return f"""
    MATCH (n:{node_label} {{hash_id: $hash_id}}) 
    RETURN n.hash_id AS hash_id, n.content AS content, n.node_type AS node_type
    LIMIT 1
    """


def get_missing_hash_ids_query(node_label: str) -> str:
    return f"""
    UNWIND $hash_ids AS hash_id
    OPTIONAL MATCH (n:{node_label} {{hash_id: hash_id}})
    WITH hash_id, n
    WHERE n IS NULL
    RETURN hash_id
    """


def get_nodes_by_hash_query(node_label: str) -> str:
    return f"""
    MATCH (n:{node_label})
    WHERE n.hash_id IN $hash_ids
    RETURN n.hash_id AS hash_id, n.content AS content, n.node_type AS node_type
    """


def get_edges_of_node_query(node_label: str) -> str:
    return f"""
           MATCH (n:{node_label} {{hash_id: $hid}})
                WITH n,
                     [(n)-[r:{rel_type}]->(m:{node_label}) |
                        {{ src: n.hash_id, dst: m.hash_id, weight: coalesce(r.weight, 1.0) }}
                     ] AS outEdges,
                     [ (p:{node_label})-[r2:{rel_type}]->(n) |
                        {{ src: p.hash_id, dst: n.hash_id, weight: coalesce(r2.weight, 1.0) }}
                     ] AS inEdges
                WITH outEdges + inEdges AS allEdges
                UNWIND allEdges AS e
                RETURN e.src AS src, e.dst AS dst, e.weight AS weight
    """


def get_chunk_node_connection_query(node_label: str, rel_type: str) -> str:
    return f"""
    MATCH (e:{node_label} {{hash_id: $hid, node_type:'entity'}})
    MATCH (e)-[:{rel_type}]-(c:{node_label} {{node_type:'chunk'}})
    WHERE size($allowed) = 0 OR c.hash_id IN $allowed
    RETURN DISTINCT
        c.hash_id   AS hash_id,
        c.content   AS content,
        c.node_type AS node_type
    ORDER BY hash_id
    """


def get_delete_nodes_query(node_label: str) -> str:
    return f"""
    UNWIND $ids AS id
    MATCH (n:{node_label} {{hash_id: id}})
    DETACH DELETE n
    """


def get_values_from_attribute_query(node_label: str, prop: str) -> str:
    return f"MATCH (n:{node_label}) RETURN n.{prop} AS v ORDER BY v"


def get_vs_map_query(node_label: str) -> str:
    return f"""
            MATCH (n:{node_label})
            RETURN n.hash_id AS hash_id, n.content AS content, n.node_type AS node_type
            ORDER BY hash_id
            """


def get_vs_map_ids_query(node_label: str) -> str:
    return f"""MATCH (n:{node_label}) RETURN n.hash_id AS id ORDER BY id"""


def get_add_nodes_query(node_label: str) -> str:
    return f"""
            UNWIND $rows AS row
            MERGE (n:{node_label} {{hash_id: row.hash_id}})
            SET n.content = row.content,
                n.chunk = row.chunk,
                n.node_type = row.node_type
            FOREACH (_ IN CASE WHEN row.node_type = 'entity' THEN [1] ELSE [] END | SET n:Entity)
            FOREACH (_ IN CASE WHEN row.node_type = 'chunk'  THEN [1] ELSE [] END | SET n:Chunk)
            """


def get_add_edges_query(node_label: str, rel_type: str) -> str:
    return f"""
            UNWIND $edges AS e
            MATCH (s:{node_label} {{hash_id: e.src}})
            MATCH (t:{node_label} {{hash_id: e.dst}})
            MERGE (s)-[r:{rel_type}]->(t)
            SET r += coalesce(e.props, {{}}),
                r.weight = coalesce(e.weight, r.weight, 1.0)
            """


def get_node_count_query(node_label: str) -> str:
    return f"MATCH (n:{node_label}) RETURN count(n) AS c"


def fetch_sorted_ids_query(node_label: str) -> str:
    return f"""
            MATCH (n:{node_label})
            WHERE size($allowed) = 0 OR n.hash_id IN $allowed
            RETURN n.hash_id AS id
            ORDER BY id
            """


def get_gds_query(node_label: str, rel_type: str, weights_attribute: str) -> str:
    return f"""
MATCH (source:{node_label})-[r:{rel_type}]->(target:{node_label})
WHERE size($allowed) = 0 OR (source.hash_id IN $allowed AND target.hash_id IN $allowed)
WITH source, target, r
WITH gds.graph.project(
  $g,
  source,
  target,
  {{
    relationshipProperties: r {{ .{weights_attribute} }}
  }}
) AS g
RETURN g.graphName AS graphName, g.nodeCount AS nodeCount, g.relationshipCount AS relationshipCount
"""
