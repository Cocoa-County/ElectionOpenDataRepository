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
