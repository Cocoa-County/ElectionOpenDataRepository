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
    assert contest["precincts"]["P1"]["winner"] == [0]


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


def test_build_election_data_sorts_choices_by_votes_desc() -> None:
    parsed_results = [
        {
            "ok": True,
            "sheet": "Sheet2",
            "data": {
                "contest": {"contest_name": "TREASURER", "vote_for": 1},
                "options": ["A", "B", "C"],
                "precincts": [
                    {
                        "precinct": "P1",
                        "results": {
                            "Total": {
                                "registered_voters": 100,
                                "times_cast": 70,
                                "options": {
                                    "A": {"votes": 10, "percent": 14.29},
                                    "B": {"votes": 50, "percent": 71.43},
                                    "C": {"votes": 10, "percent": 14.29},
                                },
                                "total_votes": 70,
                            }
                        },
                    }
                ],
            },
        }
    ]

    out = build_election_data(parsed_results)
    contest = out["contests"][0]

    assert [choice["label"] for choice in contest["choices"]] == ["B", "A", "C"]
    assert [choice["votes"] for choice in contest["choices"]] == [50, 10, 10]
    assert contest["precincts"]["P1"]["results"] == [50, 10, 10]
    assert contest["precincts"]["P1"]["winner"] == [0]


def test_build_election_data_tie_still_sets_winner_index() -> None:
    parsed_results = [
        {
            "ok": True,
            "sheet": "Sheet2",
            "data": {
                "contest": {"contest_name": "GOVERNOR", "vote_for": 1},
                "options": ["A", "B", "C"],
                "precincts": [
                    {
                        "precinct": "P1",
                        "results": {
                            "Total": {
                                "registered_voters": 100,
                                "times_cast": 80,
                                "options": {
                                    "A": {"votes": 30, "percent": 37.5},
                                    "B": {"votes": 30, "percent": 37.5},
                                    "C": {"votes": 20, "percent": 25.0},
                                },
                                "total_votes": 80,
                            }
                        },
                    }
                ],
            },
        }
    ]

    out = build_election_data(parsed_results)
    contest = out["contests"][0]
    assert contest["precincts"]["P1"]["winner"] == [0, 1]


def test_build_election_data_merges_duplicate_contest_sheets() -> None:
    parsed_results = [
        {
            "ok": True,
            "sheet": "Sheet2",
            "data": {
                "contest": {"contest_name": "GOVERNOR", "vote_for": 1},
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
        },
        {
            "ok": True,
            "sheet": "Sheet3",
            "data": {
                "contest": {"contest_name": "GOVERNOR", "vote_for": 1},
                "options": ["C"],
                "precincts": [
                    {
                        "precinct": "P1",
                        "results": {
                            "Total": {
                                "registered_voters": 100,
                                "times_cast": 60,
                                "options": {
                                    "C": {"votes": 5, "percent": 8.33},
                                },
                                "total_votes": 65,
                            }
                        },
                    }
                ],
            },
        },
    ]

    out = build_election_data(parsed_results)

    assert len(out["contests"]) == 1
    contest = out["contests"][0]
    assert contest["label"] == "GOVERNOR"
    assert sorted(choice["label"] for choice in contest["choices"]) == ["A", "B", "C"]

    precinct = contest["precincts"]["P1"]
    labels_by_index = {choice["index"]: choice["label"] for choice in contest["choices"]}
    votes_by_label = {
        labels_by_index[idx]: value
        for idx, value in enumerate(precinct["results"])
    }
    assert votes_by_label == {"A": 40, "B": 20, "C": 5}


def test_build_election_data_assigns_party_colors_for_prefix_labels() -> None:
    parsed_results = [
        {
            "ok": True,
            "sheet": "Sheet2",
            "data": {
                "contest": {"contest_name": "GOVERNOR", "vote_for": 1},
                "options": ["DEM - A", "REP - B", "NPP - C"],
                "precincts": [
                    {
                        "precinct": "P1",
                        "results": {
                            "Total": {
                                "registered_voters": 100,
                                "times_cast": 60,
                                "options": {
                                    "DEM - A": {"votes": 30, "percent": 50.0},
                                    "REP - B": {"votes": 20, "percent": 33.33},
                                    "NPP - C": {"votes": 10, "percent": 16.67},
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
    contest = out["contests"][0]
    color_by_label = {
        choice["label"]: choice.get("color")
        for choice in contest["choices"]
    }

    assert color_by_label["DEM - A"] == "blue1"
    assert color_by_label["REP - B"] == "red1"
    assert color_by_label["NPP - C"] is None
