def parse_pg_bool_array(value: str) -> list[bool]:
    value = value.strip().strip('"')  # remove wrapping quotes if present
    if value.startswith("{") and value.endswith("}"):
        inner = value[1:-1]  # strip { }
        if inner.strip() == "":
            return []
        return [v.lower() == "t" for v in inner.split(",")]

    return []


def compare_bool_lists_most_agree(bool_value_lists: list[list[bool]]) -> list[bool]:
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


def compare_bool_lists_all_agree(bool_value_lists: list[list[bool]]) -> list[bool]:
    if len(bool_value_lists) == 0:
        return []
    size_first_list = len(bool_value_lists[0])
    for list_ in bool_value_lists:
        assert size_first_list == len(list_)
    result_list = [False] * size_first_list
    for i in range(size_first_list):
        votes = sum(1 for lst in bool_value_lists if lst[i])
        result_list[i] = votes == len(bool_value_lists)
    return result_list
