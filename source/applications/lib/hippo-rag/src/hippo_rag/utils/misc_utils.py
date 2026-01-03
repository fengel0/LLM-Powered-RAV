import logging
from argparse import ArgumentTypeError
import regex

from domain.hippo_rag.model import NerRawOutput, TripleRawOutput
from domain.hippo_rag.model import Document, Triple
from hippo_rag.utils.llm_utils import filter_invalid_triples

logger = logging.getLogger(__name__)


def text_processing_word(text: str) -> str:
    cleaned = regex.sub(r"[^\p{L}\p{N} ]+", " ", text.lower())
    text = regex.sub(r"\s+", " ", cleaned).strip()
    if not text:
        logger.error(f"text is empty input was: {text}")
    return text


def text_processing(text: Triple) -> Triple:
    text_list = list(text)
    assert len(text_list) == 3
    text_list[0] = text_processing_word(text=text_list[0])
    text_list[1] = text_processing_word(text=text_list[1])
    text_list[2] = text_processing_word(text=text_list[2])

    return (text_list[0], text_list[1], text_list[2])


def reformat_openie_results(
    corpus_openie_results: list[Document],
) -> tuple[dict[str, NerRawOutput], dict[str, TripleRawOutput]]:
    ner_output_dict = {
        chunk_item.idx: NerRawOutput(
            chunk_id=chunk_item.idx,
            response=None,
            metadata={},
            unique_entities=list(set(chunk_item.extracted_entities)),
        )
        for chunk_item in corpus_openie_results
    }
    triple_output_dict = {
        chunk_item.idx: TripleRawOutput(
            chunk_id=chunk_item.idx,
            response=None,
            metadata={},
            triples=filter_invalid_triples(
                triples=[list(triple) for triple in chunk_item.extracted_triples]
            ),
        )
        for chunk_item in corpus_openie_results
    }

    return ner_output_dict, triple_output_dict


def extract_entity_nodes(
    chunk_triples: list[list[Triple]],
) -> tuple[list[str], list[list[str]]]:
    """
    erzeugt eine liste mit entityies -> jede entity kommt nur einmal vor und
    liste von enties pro chunk
    """
    chunk_triple_entities: list[
        list[str]
    ] = []  # a list of lists of unique entities from each chunk's triples
    for triples in chunk_triples:
        triple_entities: set[str] = set()
        for t in triples:
            if len(t) == 3:
                triple_entities.update([t[0], t[2]])
            else:
                logger.warning(
                    f"During graph construction, invalid triple is found: {t}"
                )
        chunk_triple_entities.append(list(triple_entities))

    graph_nodes = list(set([ent for ents in chunk_triple_entities for ent in ents]))
    return graph_nodes, chunk_triple_entities


def flatten_facts(chunk_triples: list[list[Triple]]) -> list[Triple]:
    graph_triples: list[
        Triple
    ] = []  # a list of unique relation triple (in tuple) from all chunks
    for triples in chunk_triples:
        graph_triples.extend(triples)
    graph_triples = list(set(graph_triples))
    return graph_triples


def min_max_normalize(scores: list[float]) -> list[float]:
    if not scores:
        return []
    lo = min(scores)
    hi = max(scores)
    if hi == lo:
        return [1.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


# def all_values_of_same_length(data: dict) -> bool:
# """
# Return True if all values in 'data' have the same length or data is an empty dict,
# otherwise return False.
# """
# # Get an iterator over the dictionary's values
# value_iter = iter(data.values())

# # Get the length of the first sequence (handle empty dict case safely)
# try:
# first_length = len(next(value_iter))
# except StopIteration:
# # If the dictionary is empty, treat it as all having "the same length"
# return True

# # Check that every remaining sequence has this same length
# return all(len(seq) == first_length for seq in value_iter)


def string_to_bool(v: str | bool) -> bool:
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise ArgumentTypeError(
            f"Truthy value expected: got {v} but expected one of yes/no, true/false, t/f, y/n, 1/0 (case insensitive)."
        )
