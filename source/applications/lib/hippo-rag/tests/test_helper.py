import logging
import numpy as np
import pytest
from unittest.mock import patch
from argparse import ArgumentTypeError

from core.logger import init_logging
from hippo_rag.utils.misc_utils import (
    text_processing_word,  # type: ignore
    text_processing,
    reformat_openie_results,
    extract_entity_nodes,
    flatten_facts,
    min_max_normalize,
    string_to_bool,
)
from domain.hippo_rag.model import Document
from domain_test import AsyncTestBase

init_logging("info")
logger = logging.getLogger(__name__)


# ============================== text_processing_* ==============================


class TestTextProcessing(AsyncTestBase):
    __test__ = True

    def test_text_processing_word_basic(self):
        assert text_processing_word("Hello, World!") == "hello world"

    def test_text_processing_word_german(self):
        assert text_processing_word("HÄllo, Wörld!") == "hällo wörld"

    def test_text_processing_word_special_chars(self):
        assert text_processing_word("Test@#$%^&*()_+{}|:<>?[]\\;'\",./") == "test"

    def test_text_processing_word_numbers(self):
        assert (
            text_processing_word("Test123 with 456 numbers")
            == "test123 with 456 numbers"
        )

    def test_text_processing_word_whitespace(self):
        assert text_processing_word("  Multiple   spaces   ") == "multiple spaces"

    def test_text_processing_word_empty_string(self):
        assert text_processing_word("") == ""

    def test_text_processing_triple(self):
        assert text_processing(("Apple Inc.", "is located in", "Cupertino, CA")) == (
            "apple inc",
            "is located in",
            "cupertino ca",
        )

    def test_text_processing_triple_invalid_length(self):
        with pytest.raises(AssertionError):
            text_processing(("only", "two"))  # type: ignore
        with pytest.raises(AssertionError):
            text_processing(("one", "two", "three", "four"))  # type: ignore


# ========================== reformat_openie_results ===========================


class TestReformatOpenieResults(AsyncTestBase):
    __test__ = True

    @patch("hippo_rag.utils.misc_utils.filter_invalid_triples")
    def test_reformat_openie_results_basic(self, mock_filter):  # type: ignore
        mock_filter.return_value = [["apple", "is", "fruit"]]

        docs = [
            Document(
                idx="chunk-1",
                passage="Apple is a fruit",
                extracted_entities=["apple", "fruit", "apple"],
                extracted_triples=[("apple", "is", "fruit")],
                metadata={},
            ),
            Document(
                idx="chunk-2",
                passage="Orange is citrus",
                extracted_entities=["orange", "citrus"],
                extracted_triples=[("orange", "is", "citrus")],
                metadata={},
            ),
        ]

        ner_dict, triple_dict = reformat_openie_results(docs)

        # NER results exist + duplicates removed
        assert "chunk-1" in ner_dict and "chunk-2" in ner_dict
        assert set(ner_dict["chunk-1"].unique_entities) == {"apple", "fruit"}
        assert set(ner_dict["chunk-2"].unique_entities) == {"orange", "citrus"}

        # Triples exist
        assert "chunk-1" in triple_dict and "chunk-2" in triple_dict

        # Filter called per doc
        assert mock_filter.call_count == 2  # type: ignore

    def test_reformat_openie_results_empty(self):
        ner_dict, triple_dict = reformat_openie_results([])
        assert len(ner_dict) == 0
        assert len(triple_dict) == 0


# ============================= extract_entity_nodes ===========================


class TestExtractEntityNodes(AsyncTestBase):
    __test__ = True

    def test_extract_entity_nodes_basic(self):
        chunk_triples = [
            [("apple", "is", "fruit"), ("orange", "is", "citrus")],
            [("fruit", "is", "healthy"), ("apple", "has", "vitamins")],
        ]

        entities, chunk_entities = extract_entity_nodes(chunk_triples)

        expected_entities = {
            "apple",
            "fruit",
            "orange",
            "citrus",
            "healthy",
            "vitamins",
        }
        assert set(entities) == expected_entities

        assert len(chunk_entities) == 2
        assert set(chunk_entities[0]) == {"apple", "fruit", "orange", "citrus"}
        assert set(chunk_entities[1]) == {"fruit", "healthy", "apple", "vitamins"}

    def test_extract_entity_nodes_invalid_triples(self):
        with patch("hippo_rag.utils.misc_utils.logger") as mock_logger:
            chunk_triples = [
                [("apple", "is", "fruit"), ("invalid", "triple")],  # invalid
                [("orange", "is", "citrus")],
            ]

            entities, _ = extract_entity_nodes(chunk_triples)  # type: ignore

            mock_logger.warning.assert_called_once()
            assert "invalid triple" in mock_logger.warning.call_args[0][0].lower()

            expected_entities = {"apple", "fruit", "orange", "citrus"}
            assert set(entities) == expected_entities

    def test_extract_entity_nodes_empty(self):
        entities, chunk_entities = extract_entity_nodes([])
        assert len(entities) == 0
        assert len(chunk_entities) == 0

    def test_extract_entity_nodes_empty_chunks(self):
        chunk_triples = [[], [("apple", "is", "fruit")]]
        _, chunk_entities = extract_entity_nodes(chunk_triples)  # type: ignore

        assert len(chunk_entities) == 2
        assert chunk_entities[0] == []
        assert set(chunk_entities[1]) == {"apple", "fruit"}


# ================================ flatten_facts ===============================


class TestFlattenFacts(AsyncTestBase):
    __test__ = True

    def test_flatten_facts_basic(self):
        chunk_triples = [
            [("apple", "is", "fruit"), ("orange", "is", "citrus")],
            [("apple", "is", "fruit"), ("fruit", "is", "healthy")],  # duplicate
        ]

        result = flatten_facts(chunk_triples)

        expected = [
            ("apple", "is", "fruit"),
            ("orange", "is", "citrus"),
            ("fruit", "is", "healthy"),
        ]
        assert len(result) == 3
        assert set(result) == set(expected)

    def test_flatten_facts_empty(self):
        assert flatten_facts([]) == []

    def test_flatten_facts_empty_chunks(self):
        chunk_triples = [[], [("apple", "is", "fruit")], []]
        result = flatten_facts(chunk_triples)
        assert result == [("apple", "is", "fruit")]


# ============================== min_max_normalize =============================


class TestMinMaxNormalize(AsyncTestBase):
    __test__ = True

    def test_min_max_normalize_basic(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = min_max_normalize(x)
        expected = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_min_max_normalize_same_values(self):
        x = [5.0, 5.0, 5.0, 5.0]
        result = min_max_normalize(x)
        expected = np.array([1.0, 1.0, 1.0, 1.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_min_max_normalize_single_value(self):
        x = [42.0]
        result = min_max_normalize(x)
        expected = np.array([1.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_min_max_normalize_negative_values(self):
        x = [-2.0, -1.0, 0.0, 1.0, 2.0]
        result = min_max_normalize(x)
        expected = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        np.testing.assert_array_almost_equal(result, expected)


# ============================== string_to_bool ================================


class TestStringToBool(AsyncTestBase):
    __test__ = True

    @pytest.mark.parametrize(
        "value", ["yes", "true", "t", "y", "1", "YES", "TRUE", "T", "Y"]
    )
    def test_string_to_bool_true_values(self, value):
        assert string_to_bool(value) is True

    @pytest.mark.parametrize(
        "value", ["no", "false", "f", "n", "0", "NO", "FALSE", "F", "N"]
    )
    def test_string_to_bool_false_values(self, value):
        assert string_to_bool(value) is False

    @pytest.mark.parametrize("value,expected", [(True, True), (False, False)])
    def test_string_to_bool_boolean_input(self, value, expected):
        assert string_to_bool(value) is expected

    @pytest.mark.parametrize("value", ["maybe", "2", "invalid", "", "none"])
    def test_string_to_bool_invalid_values(self, value):
        with pytest.raises(ArgumentTypeError):
            string_to_bool(value)

    @pytest.mark.parametrize(
        "value,expected",
        [("TrUe", True), ("fAlSe", False), ("YeS", True), ("nO", False)],
    )
    def test_string_to_bool_case_insensitive(self, value, expected):
        assert string_to_bool(value) is expected


# ================================ integration =================================


class TestIntegration(AsyncTestBase):
    __test__ = True

    @patch("hippo_rag.utils.misc_utils.filter_invalid_triples")
    def test_full_pipeline(self, mock_filter):  # type: ignore
        mock_filter.side_effect = lambda triples: triples  # type: ignore

        doc = Document(
            idx="test-chunk",
            passage="Apple Inc. is located in Cupertino, CA",
            extracted_entities=["Apple Inc.", "Cupertino, CA"],
            extracted_triples=[("Apple Inc.", "is located in", "Cupertino, CA")],
            metadata={},
        )

        ner_dict, triple_dict = reformat_openie_results([doc])

        processed_triples = [
            [text_processing(t) for t in triple_dict["test-chunk"].triples]
        ]

        entities, _ = extract_entity_nodes(processed_triples)
        facts = flatten_facts(processed_triples)

        assert "test-chunk" in ner_dict
        assert len(processed_triples[0]) == 1
        assert processed_triples[0][0] == ("apple inc", "is located in", "cupertino ca")
        assert set(entities) == {"apple inc", "cupertino ca"}
        assert facts == [("apple inc", "is located in", "cupertino ca")]

