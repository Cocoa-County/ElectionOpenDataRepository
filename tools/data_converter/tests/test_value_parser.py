from data_converter.parser.value_parser import parse_integer, parse_percent


def test_parse_integer_with_commas() -> None:
    assert parse_integer("1,234", {"strip_commas": True, "empty_as_null": True}) == 1234


def test_parse_integer_masked_to_none() -> None:
    assert (
        parse_integer(
            "****",
            {"masked_as_null": True, "empty_as_null": True},
            masked_tokens={"****"},
        )
        is None
    )


def test_parse_percent_handles_suffix_and_empty() -> None:
    assert parse_percent("53.33%", {"strip_suffix": "%", "empty_as_null": True}) == 53.33
    assert parse_percent("", {"strip_suffix": "%", "empty_as_null": True}) is None
