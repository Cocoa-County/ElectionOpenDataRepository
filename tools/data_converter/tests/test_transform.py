from __future__ import annotations

from data_converter.transform.builder import build_election_data


def test_build_election_data_basic_shape() -> None:
    parsed_results = [
        {
            "ok": True,
            "sheet": "Sheet2",
            "data": {
                "contest": {"contest_name": "ASSESSOR", "vote_for": 1},
                "options": ["A", "B"],
                "precincts": [
                    {
                        "precinct": "P1",
                        "results": {
                            "Total": {
                                "registered_voters": 100,
                                "times_cast": 60,
                                "options": {
                                    "A": {"votes": 40, "percent": 66.67},
                                    "B": {"votes": 20, "percent": 33.33},
                                },
                                "total_votes": 60,
                            }
                        },
                    }
                ],
            },
        }
    ]

    out = build_election_data(parsed_results)
    assert "contests" in out
    assert len(out["contests"]) == 1
    contest = out["contests"][0]
    assert contest["label"] == "ASSESSOR"
    assert contest["choices"][0]["votes"] == 40
    assert contest["precincts"]["P1"]["results"] == [40, 20]
    assert contest["precincts"]["P1"]["winner"] == 0


def test_build_election_data_turnout_merge() -> None:
    parsed_results = [
        {
            "ok": True,
            "sheet": "Sheet1",
            "data": {
                "precincts": [
                    {
                        "precinct": "P1",
                        "results": {
                            "Total": {
                                "registered_voters": 120,
                                "voters_cast": 77,
                            }
                        },
                    }
                ]
            },
        },
        {
            "ok": True,
            "sheet": "Sheet2",
            "data": {
                "contest": {"contest_name": "CLERK", "vote_for": 1},
                "options": ["A", "B"],
                "precincts": [
                    {
                        "precinct": "P1",
                        "results": {
                            "Total": {
                                "registered_voters": 100,
                                "times_cast": 60,
                                "options": {
                                    "A": {"votes": 30, "percent": 50.0},
                                    "B": {"votes": 30, "percent": 50.0},
                                },
                                "total_votes": 60,
                            }
                        },
                    }
                ],
            },
        },
    ]

    out = build_election_data(parsed_results)
    precinct = out["contests"][0]["precincts"]["P1"]
    assert precinct["registeredVoters"] == 120
    assert precinct["totalVoters"] == 77
