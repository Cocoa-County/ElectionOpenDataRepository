from __future__ import annotations

import pytest

from data_converter.cli import build_parser


def test_split_subcommand_parses_expected_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["split", "--xlsx", "in.xlsx", "--output-dir", "out", "--create-dirs"]
    )

    assert args.command == "split"
    assert args.xlsx == "in.xlsx"
    assert args.output_dir == "out"
    assert args.create_dirs is True


def test_parse_subcommand_requires_one_input_mode() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "parse",
                "--config",
                "profiles/contra_costa/election_results_xlsx/results.yml",
            ]
        )


def test_pipeline_subcommand_accepts_config_only() -> None:
    parser = build_parser()
    args = parser.parse_args(["pipeline", "--config", "pipeline.yml"])

    assert args.command == "pipeline"
    assert args.config == "pipeline.yml"
