from pathlib import Path

from data_converter.parser.main import parse_file


def test_turnout_parse_file_smoke(tmp_path: Path) -> None:
    csv_content = "\n".join(
        [
            "Page: 1 of 42,,,,,,,2026-06-25 02:56:35 PM",
            ",,,,,,,,",
            ",,Contra Costa County,,,,,,",
            ",,2026-06-02,,,,,,",
            ",,Statewide Direct Primary Election,,,,,,",
            ",,Official Results - Final,,,,,,",
            ",,,,,,,,",
            "Precinct,Registered Voters,,Cards Cast,,Voters Cast,% Turnout,,",
            "WLKN101,,,,,,,,",
            "Vote By Mail,100,,90,,45,45%,,",
            "Election Day,100,,10,,5,5%,,",
            "Total,100,,100,,50,50%,,",
            "Contra Costa County - Total,100,,100,,50,50%,,",
            "Cumulative,,,,,,,,",
            "Vote By Mail,100,,90,,45,45%,,",
        ]
    )

    csv_path = tmp_path / "turnout.csv"
    csv_path.write_text(csv_content, encoding="utf-8")

    config_path = (
        Path(__file__).parents[1]
        / "profiles"
        / "contra_costa"
        / "election_results_xlsx"
        / "turnout_summary.yml"
    )
    parsed = parse_file(str(csv_path), str(config_path))

    assert parsed["meta"]["page"] == 1
    assert parsed["meta"]["county"] == "Contra Costa County"
    assert parsed["precincts"][0]["precinct"] == "WLKN101"
    assert parsed["precincts"][0]["results"]["Total"]["voters_cast"] == 50
    assert parsed["summaries"]["rows"][0]["label"] == "Contra Costa County - Total"
    assert parsed["summaries"]["groups"][0]["label"] == "Cumulative"


def test_turnout_parse_supports_parent_named_total_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "turnout_city.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Page: 1 of 42,,,,,,,2026-06-25 02:56:35 PM",
                ",,,,,,,,",
                ",,Contra Costa County,,,,,,",
                ",,2026-06-02,,,,,,",
                ",,Statewide Direct Primary Election,,,,,,",
                ",,Official Results - Final,,,,,,",
                ",,,,,,,,",
                "District,Registered Voters,,Cards Cast,,Voters Cast,% Turnout,,",
                "City,,,,,,,,",
                "City of Antioch,,,,,,,,",
                "Vote By Mail,67596,,40625,,20366,30.13%,,",
                "Election Day,67596,,4116,,2059,3.05%,,",
                "City of Antioch - Total,67596,,44741,,22425,33.18%,,",
                "Cumulative,,,,,,,,",
                "Cumulative - Total,0,,0,,0,N/A,,",
                "City - Total,67596,,44741,,22425,33.18%,,",
            ]
        ),
        encoding="utf-8",
    )

    config_path = tmp_path / "turnout_city.yml"
    config_path.write_text(
        "\n".join(
            [
                "document:",
                "  type: turnout_summary",
                "  format: csv",
                "normalization:",
                "  newline_replacement: ' '",
                "  collapse_whitespace: true",
                "  trim: true",
                "  strip_wrapping_quotes: true",
                "header:",
                "  page:",
                "    row: 0",
                "    col: 0",
                "    regex: '^Page: (?P<page>\\d+) of (?P<total_pages>\\d+)$'",
                "  report_timestamp:",
                "    row: 0",
                "    scan_row_for_datetime:",
                "      formats:",
                "        - '%m/%d/%Y %I:%M:%S %p'",
                "title_block:",
                "  start_row: 2",
                "  col: 2",
                "  lines:",
                "    - county",
                "    - election_date",
                "    - election_name",
                "    - report_title",
                "table:",
                "  header_row_search:",
                "    max_scan_rows: 10",
                "    required_cells:",
                "      - col: 0",
                "        equals: \"District\"",
                "      - col: 1",
                "        equals: \"Registered Voters\"",
                "      - col: 3",
                "        equals: \"Cards Cast\"",
                "      - col: 5",
                "        equals: \"Voters Cast\"",
                "  columns:",
                "    label: 0",
                "    registered_voters: 1",
                "    cards_cast: 3",
                "    voters_cast: 5",
                "    turnout: 6",
                "precinct_group:",
                "  parent_regex: \"^(?:(?:City|Town) of .+|Unincorporated Contra Costa County)$\"",
                "  child_rows:",
                "    - \"Vote By Mail\"",
                "    - \"Election Day\"",
                "  derived_child_rows:",
                "    - suffix: \" - Total\"",
                "      child_label: \"Total\"",
                "footer:",
                "  summary_rows:",
                "    regex_labels:",
                "      - \"^City - Total$\"",
                "  summary_groups:",
                "    parent_labels:",
                "      - \"Cumulative\"",
                "values:",
                "  integer:",
                "    strip_commas: true",
                "    empty_as_null: true",
                "  percent:",
                "    strip_suffix: \"%\"",
                "    empty_as_null: true",
            ]
        ),
        encoding="utf-8",
    )

    parsed = parse_file(str(csv_path), str(config_path))

    assert parsed["precincts"][0]["precinct"] == "City of Antioch"
    assert parsed["precincts"][0]["results"]["Total"]["voters_cast"] == 22425
    assert parsed["summaries"]["groups"][0]["results"]["Total"]["voters_cast"] == 0
