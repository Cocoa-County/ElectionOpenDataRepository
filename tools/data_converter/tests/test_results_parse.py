from pathlib import Path
import json

from data_converter.parser.main import parse_file


def test_results_parse_file_smoke(tmp_path: Path) -> None:
    csv_content = "\n".join(
        [
            "Page: 21 of 42,,,,,,,,,,,2026-06-25 14:56:34.985000",
            "ASSESSOR (Vote for  1) **** - Insufficient Turnout to Protect Voter Privacy",
            ",,,,,,,,,,,",
            "Precinct,Times Cast,Registered Voters,,Precinct,VINCE ROBB,,NICK SPINNER,,Total Votes,Unresolved Write-In",
            "ALHA101,,,,ALHA101,,,,,,",
            "Vote By Mail,40,75,,Vote By Mail,24,75.0,4,12.5,32,0",
            "Election Day,3,75,,Election Day,****,****,****,****,****,****",
            "Total,43,75,,Total,27,77.14,4,11.43,35,0",
            "Contra Costa County - Total,326469,731497,,Contra Costa County - Total,181262,67.07,63177,23.38,270245,0",
            "Cumulative,,,,Cumulative,,,,,,",
            "Vote By Mail,0,0,,Vote By Mail,0,,0,,0,0",
        ]
    )

    csv_path = tmp_path / "results.csv"
    csv_path.write_text(csv_content, encoding="utf-8")

    config_path = (
        Path(__file__).parents[1]
        / "profiles"
        / "contra_costa"
        / "election_results_xlsx"
        / "results.yml"
    )
    parsed = parse_file(str(csv_path), str(config_path))

    assert parsed["meta"]["page"] == 21
    assert parsed["contest"]["contest_name"] == "ASSESSOR"
    assert parsed["options"] == ["VINCE ROBB", "NICK SPINNER"]
    assert parsed["precincts"][0]["precinct"] == "ALHA101"
    assert parsed["precincts"][0]["results"]["Election Day"]["options"]["VINCE ROBB"]["votes"] is None
    assert parsed["summaries"]["rows"][0]["label"] == "Contra Costa County - Total"
    assert parsed["summaries"]["groups"][0]["label"] == "Cumulative"


def test_parse_file_as_object(tmp_path: Path) -> None:
    csv_path = tmp_path / "results_min.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Page: 1 of 1,,,,,,,,,,,2026-06-25 14:56:34.985000",
                "ASSESSOR (Vote for  1)",
                ",,,,,,,,,,,",
                "Precinct,Times Cast,Registered Voters,,Precinct,VINCE ROBB,,Total Votes,Unresolved Write-In",
                "ALHA101,,,,ALHA101,,,,",
                "Vote By Mail,1,2,,Vote By Mail,1,100.0,1,0",
            ]
        ),
        encoding="utf-8",
    )
    config_path = (
        Path(__file__).parents[1]
        / "profiles"
        / "contra_costa"
        / "election_results_xlsx"
        / "results.yml"
    )
    parsed_obj = parse_file(str(csv_path), str(config_path), as_object=True)

    assert parsed_obj.to_dict()["meta"]["page"] == 1
    assert "ASSESSOR" in parsed_obj.to_json()


def test_json_omit_nulls_keeps_dict_complete(tmp_path: Path) -> None:
    csv_path = tmp_path / "results_min.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Page: 1 of 1,,,,,,,,,,,2026-06-25 14:56:34.985000",
                "ASSESSOR (Vote for  1)",
                ",,,,,,,,,,,",
                "Precinct,Times Cast,Registered Voters,,Precinct,VINCE ROBB,,NICK SPINNER,,Total Votes,Unresolved Write-In",
                "ALHA101,,,,ALHA101,,,,,,",
                "Vote By Mail,1,2,,Vote By Mail,1,100.0,0,0.0,1,0",
                "Election Day,0,2,,Election Day,****,****,****,****,****,****",
            ]
        ),
        encoding="utf-8",
    )

    config_path = (
        Path(__file__).parents[1]
        / "profiles"
        / "contra_costa"
        / "election_results_xlsx"
        / "results.yml"
    )
    parsed_obj = parse_file(str(csv_path), str(config_path), as_object=True)

    # In-memory dict remains complete and still contains null fields.
    data = parsed_obj.to_dict()
    assert (
        data["precincts"][0]["results"]["Election Day"]["options"]["VINCE ROBB"]["votes"]
        is None
    )

    # JSON writer can omit null-valued fields.
    json_without_nulls = parsed_obj.to_json(include_nulls=False)
    no_null_payload = json.loads(json_without_nulls)
    assert "votes" not in no_null_payload["precincts"][0]["results"]["Election Day"]["options"]["VINCE ROBB"]


def test_results_parse_handles_shifted_final_candidate_header(tmp_path: Path) -> None:
    csv_path = tmp_path / "results_shifted_header.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Page: 10 of 42,,,,,,,,,,,2026-06-25 14:56:34.985000",
                '"UNITED STATES REPRESENTATIVE, DISTRICT 8 (Vote for  1)"',
                ",,,,,,,,,,,,,,,",
                "Precinct,Times Cast,Registered Voters,,Precinct,RUDY RECILE (REP),,AARON ROWDEN (DEM),,NICOLAS CARJUZAA (DEM),,,JOHN GARAMENDI (DEM),,Total Votes,Unresolved Write-In",
                "TEST101,,,,TEST101,,,,,,,,,,",
                "Vote By Mail,10,20,,Vote By Mail,1,10.00,2,20.00,3,30.00,,4,40.00,10,0",
            ]
        ),
        encoding="utf-8",
    )

    config_path = (
        Path(__file__).parents[1]
        / "profiles"
        / "contra_costa"
        / "election_results_xlsx"
        / "results.yml"
    )
    parsed = parse_file(str(csv_path), str(config_path))

    assert parsed["options"] == [
        "RUDY RECILE (REP)",
        "AARON ROWDEN (DEM)",
        "NICOLAS CARJUZAA (DEM)",
        "JOHN GARAMENDI (DEM)",
    ]
