from domain.database.validation.model import (
    RAGSystemAnswer,
    RatingGeneral,
    RatingQuery,
    WhatToFetch,
)
from evaluation_service.usecase.evaluation import EvaluationServiceUsecases


auth_fetch_error = "Please select both dataset and system."


async def fetch_ratings_of_answer_system(
    dataset: str | None,
    system_config: str | None,
    number_of_facts_start: int,
    number_of_facts_end: int,
    metadata_attribute: str,
    metadata_attribute_value: str,
) -> tuple[list[RatingGeneral], str]:
    """Human-rated answers from *system_config* inside *dataset*."""

    assert number_of_facts_start >= 0
    assert number_of_facts_end >= number_of_facts_start

    if not dataset or not system_config:
        return [], auth_fetch_error

    uc = EvaluationServiceUsecases.Instance()

    query = RatingQuery(
        dataset_id=dataset,
        system_config=system_config,
        what_to_fetch=WhatToFetch.both,  # human ratings can be stored as user/llm
        metadata=(
            {metadata_attribute: metadata_attribute_value}
            if metadata_attribute and metadata_attribute_value
            else None
        ),
    )

    result = await uc.fetch_ratings(criteria=query)
    if result.is_error():
        return [], str(result.get_error())

    ratings = [
        r
        for r in result.get_ok()
        if len(r.completeness) >= number_of_facts_start
        and len(r.completeness) <= number_of_facts_end
    ]
    return ratings, ""  # type: ignore


async def fetch_ratings_of_multiable_systems_all_agree(
    dataset: str | None,
    system_config: str,
    eval_configs: list[str],
    number_of_facts_start: int,
    number_of_facts_end: int,
    metadata_attribute: str,
    metadata_attribute_value: str,
) -> tuple[list[RatingGeneral], str]:
    assert number_of_facts_start >= 0
    assert number_of_facts_end >= number_of_facts_start

    if not dataset or not system_config or not eval_configs:
        return [], auth_fetch_error

    uc = EvaluationServiceUsecases.Instance()

    queries = [
        RatingQuery(
            dataset_id=dataset,
            system_config=system_config,
            grading_config=eval_config,
            what_to_fetch=WhatToFetch.llm,
            metadata=(
                {metadata_attribute: metadata_attribute_value}
                if metadata_attribute and metadata_attribute_value
                else None
            ),
        )
        for eval_config in eval_configs
    ]

    per_question: dict[str, list[RatingGeneral]] = {}

    # sammeln
    for q in queries:
        result = await uc.fetch_ratings(criteria=q)
        if result.is_error():
            return [], str(result.get_error())

        for r in result.get_ok():
            if (
                len(r.completeness) < number_of_facts_start
                or len(r.completeness) > number_of_facts_end
            ):
                continue
            per_question.setdefault(r.question_id, []).append(r)

    combined: list[RatingGeneral] = []

    # Deine (strikte) Mehrheitsfunktion mit assert auf gleiche Länge
    def compare_bool_lists(bool_value_lists: list[list[bool]]) -> list[bool]:
        if len(bool_value_lists) == 0:
            return []
        size_first_list = len(bool_value_lists[0])
        for list_ in bool_value_lists:
            assert size_first_list == len(list_)
        result_list = [False] * size_first_list
        for i in range(size_first_list):
            votes = sum(1 for lst in bool_value_lists if lst[i])
            result_list[i] = votes == len(bool_value_lists)  # strikte Mehrheit
        return result_list

    for qid, ratings in per_question.items():
        n = len(ratings)
        if n == 0:
            continue

        # ECHTE binäre Mehrheitsabstimmung (Gleichstand -> 0)
        votes_1 = sum(1 for r in ratings if int(r.correctness) == 1)
        majority_correct = 1 if votes_1 == n else 0

        # Elementweise Mehrheit mit deinen asserts
        comp_majority = compare_bool_lists([r.completeness for r in ratings])
        comp_in_data_majority = compare_bool_lists(
            [r.completeness_in_data for r in ratings]
        )

        # getrennte Mittelwerte; Bug fix (nicht überschreiben)
        avg_facts_answer = int(
            round(sum(r.number_of_facts_in_answer for r in ratings) / n)
        )
        avg_facts_context = int(
            round(sum(r.number_of_facts_in_context for r in ratings) / n)
        )

        chunk_counts: dict[int, int] = {}

        for r in ratings:
            for chunk_index in r.relevant_chunks:
                if chunk_index not in chunk_counts.keys():
                    chunk_counts[chunk_index] = 0
                chunk_counts[chunk_index] = chunk_counts[chunk_index] + 1

        relevant_cunkts = [
            c for c in chunk_counts.keys() if chunk_counts[c] == len(ratings)
        ]
        number_of_chunks = ratings[0].number_of_chunks

        combined.append(
            RatingGeneral(
                question_id=qid,
                rationale="",
                source="all-agree",
                source_type="llm",
                correctness=majority_correct,
                completeness=comp_majority,
                completeness_in_data=comp_in_data_majority,
                number_of_chunks=number_of_chunks,
                relevant_chunks=relevant_cunkts,
                number_of_facts_in_answer=avg_facts_answer,
                number_of_facts_in_context=avg_facts_context,
            )
        )

    return combined, ""


async def fetch_ratings_of_multiable_systems_most_agree(
    dataset: str | None,
    system_config: str,
    eval_configs: list[str],
    number_of_facts_start: int,
    number_of_facts_end: int,
    metadata_attribute: str,
    metadata_attribute_value: str,
) -> tuple[list[RatingGeneral], str]:
    assert number_of_facts_start >= 0
    assert number_of_facts_end >= number_of_facts_start

    if not dataset or not system_config or not eval_configs:
        return [], auth_fetch_error

    uc = EvaluationServiceUsecases.Instance()

    queries = [
        RatingQuery(
            dataset_id=dataset,
            system_config=system_config,
            grading_config=eval_config,
            what_to_fetch=WhatToFetch.llm,
            metadata=(
                {metadata_attribute: metadata_attribute_value}
                if metadata_attribute and metadata_attribute_value
                else None
            ),
        )
        for eval_config in eval_configs
    ]

    per_question: dict[str, list[RatingGeneral]] = {}

    # sammeln
    for q in queries:
        result = await uc.fetch_ratings(criteria=q)
        if result.is_error():
            return [], str(result.get_error())

        for r in result.get_ok():
            if (
                len(r.completeness) < number_of_facts_start
                or len(r.completeness) > number_of_facts_end
            ):
                continue
            per_question.setdefault(r.question_id, []).append(r)

    combined: list[RatingGeneral] = []

    # Deine (strikte) Mehrheitsfunktion mit assert auf gleiche Länge
    def compare_bool_lists(bool_value_lists: list[list[bool]]) -> list[bool]:
        if len(bool_value_lists) == 0:
            return []
        size_first_list = len(bool_value_lists[0])
        for list_ in bool_value_lists:
            assert size_first_list == len(list_)
        result_list = [False] * size_first_list
        for i in range(size_first_list):
            votes = sum(1 for lst in bool_value_lists if lst[i])
            result_list[i] = votes > (len(bool_value_lists) / 2)  # strikte Mehrheit
        return result_list

    for qid, ratings in per_question.items():
        n = len(ratings)
        if n == 0:
            continue

        # ECHTE binäre Mehrheitsabstimmung (Gleichstand -> 0)
        votes_1 = sum(1 for r in ratings if int(r.correctness) == 1)
        majority_correct = 1 if votes_1 > n / 2 else 0

        # Elementweise Mehrheit mit deinen asserts
        comp_majority = compare_bool_lists([r.completeness for r in ratings])
        comp_in_data_majority = compare_bool_lists(
            [r.completeness_in_data for r in ratings]
        )

        # getrennte Mittelwerte; Bug fix (nicht überschreiben)
        avg_facts_answer = int(
            round(sum(r.number_of_facts_in_answer for r in ratings) / n)
        )
        avg_facts_context = int(
            round(sum(r.number_of_facts_in_context for r in ratings) / n)
        )

        chunk_counts: dict[int, int] = {}
        for r in ratings:
            for chunk_index in r.relevant_chunks:
                if chunk_index not in chunk_counts.keys():
                    chunk_counts[chunk_index] = 0
                chunk_counts[chunk_index] = chunk_counts[chunk_index] + 1

        relevant_cunkts = [
            c for c in chunk_counts.keys() if chunk_counts[c] == len(ratings)
        ]

        number_of_chunks = ratings[0].number_of_chunks

        combined.append(
            RatingGeneral(
                question_id=qid,
                rationale="",
                source="most-agree",
                source_type="llm",
                correctness=majority_correct,
                completeness=comp_majority,
                completeness_in_data=comp_in_data_majority,
                number_of_chunks=number_of_chunks,
                relevant_chunks=relevant_cunkts,
                number_of_facts_in_answer=avg_facts_answer,
                number_of_facts_in_context=avg_facts_context,
            )
        )

    return combined, ""


async def fetch_ratings_of_answer_system_by_system(
    dataset: str | None,
    system_config: str | None,
    eval_config: str | None,
    number_of_facts_start: int,
    number_of_facts_end: int,
    metadata_attribute: str,
    metadata_attribute_value: str,
) -> tuple[list[RatingGeneral], str]:
    """Answers from *system_config* evaluated by another LLM (*eval_config*)."""

    assert number_of_facts_start >= 0
    assert number_of_facts_end >= number_of_facts_start

    if not dataset or not system_config or not eval_config:
        return [], auth_fetch_error

    uc = EvaluationServiceUsecases.Instance()

    query = RatingQuery(
        dataset_id=dataset,
        system_config=system_config,
        grading_config=eval_config,
        what_to_fetch=WhatToFetch.llm,
        metadata=(
            {metadata_attribute: metadata_attribute_value}
            if metadata_attribute and metadata_attribute_value
            else None
        ),
    )

    result = await uc.fetch_ratings(criteria=query)
    if result.is_error():
        return [], str(result.get_error())

    ratings = [
        r
        for r in result.get_ok()
        if len(r.completeness) >= number_of_facts_start
        and len(r.completeness) <= number_of_facts_end
    ]
    return ratings, ""  # type: ignore


async def fetch_ratings_eval_system(
    dataset: str | None,
    system_config: str | None,
    number_of_facts_start: int,
    number_of_facts_end: int,
    metadata_attribute: str,
    metadata_attribute_value: str,
) -> tuple[list[RatingGeneral], str]:
    """LLM-based *evaluation* ratings (grading_config = system_config)."""

    if not dataset or not system_config:
        return [], auth_fetch_error

    uc = EvaluationServiceUsecases.Instance()

    query = RatingQuery(
        dataset_id=dataset,
        grading_config=system_config,
        what_to_fetch=WhatToFetch.llm,
        metadata=(
            {metadata_attribute: metadata_attribute_value}
            if metadata_attribute and metadata_attribute_value
            else None
        ),
    )

    result = await uc.fetch_ratings(criteria=query)
    if result.is_error():
        return [], str(result.get_error())

    ratings = [
        r
        for r in result.get_ok()
        if len(r.completeness) >= number_of_facts_start
        and len(r.completeness) <= number_of_facts_end
    ]
    return ratings, ""  # type: ignore


async def fetch_anwers(
    dataset: str | None,
    system_config: str,
) -> tuple[list[RAGSystemAnswer], str]:
    """LLM-based *evaluation* ratings (grading_config = system_config)."""

    uc = EvaluationServiceUsecases.Instance()
    anwers_result = await uc.get_anwers_by_config(
        config_id=system_config, dataset_option=dataset
    )

    if anwers_result.is_error():
        return [], f"{anwers_result.get_error()}"
    return anwers_result.get_ok(), ""
