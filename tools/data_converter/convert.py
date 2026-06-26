"""Compatibility wrapper for the YAML-driven parser CLI.

Examples:
    python convert.py --config results.yml --csv output/Sheet2.csv --output parsed.json
    python convert.py --config turnout_summary.yml --input-dir output --glob "Sheet*.csv"
"""

from parser.main import cli_main


def main() -> None:
    cli_main()


if __name__ == "__main__":
    main()
