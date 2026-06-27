from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any


def build_election_data(
    parsed_results: list[dict[str, Any]],
    *,
    precinct_result_scope: str = "Total",
) -> dict[str, Any]:
    turnout_by_precinct = _build_turnout_index(parsed_results)
    contests: list[dict[str, Any]] = []

    contest_records = [
        item for item in parsed_results if item.get("ok") and isinstance(item.get("data"), dict) and "contest" in item["data"]
    ]

    for contest_index, record in enumerate(contest_records):
        payload = record["data"]
        contest = payload.get("contest", {})
        contest_name = str(contest.get("contest_name", f"Contest {contest_index + 1}")).strip()
        option_labels = [str(opt) for opt in payload.get("options", [])]

        precincts_map: dict[str, dict[str, Any]] = {}
        choice_totals = [0 for _ in option_labels]

        for precinct in payload.get("precincts", []):
            precinct_id = str(precinct.get("precinct", "")).strip()
            if not precinct_id:
                continue

            results_block = precinct.get("results", {}).get(precinct_result_scope, {})
            option_block = results_block.get("options", {}) if isinstance(results_block, dict) else {}

            vote_results: list[int] = []
            percent_results: list[float] = []
            has_percent = False

            for idx, option_label in enumerate(option_labels):
                opt_data = option_block.get(option_label, {}) if isinstance(option_block, dict) else {}
                votes = _to_int(opt_data.get("votes"), default=0)
                vote_results.append(votes)
                choice_totals[idx] += votes

                pct_raw = opt_data.get("percent")
                if pct_raw is None:
                    percent_results.append(0.0)
                else:
                    has_percent = True
                    percent_results.append(_normalize_percent(pct_raw))

            total_votes = _to_int(results_block.get("total_votes"), default=sum(vote_results))
            winner = _winner_index(vote_results)

            turnout_row = turnout_by_precinct.get(precinct_id, {})
            registered_voters = _to_int(
                turnout_row.get("registeredVoters", results_block.get("registered_voters")),
                default=0,
            )
            total_voters = _to_int(
                turnout_row.get("totalVoters", results_block.get("times_cast", total_votes)),
                default=0,
            )

            precinct_entry: dict[str, Any] = {
                "label": precinct_id,
                "registeredVoters": registered_voters,
                "totalVoters": total_voters,
                "total": total_votes,
                "results": vote_results,
            }
            if winner is not None:
                precinct_entry["winner"] = winner
            if has_percent:
                precinct_entry["percentage"] = percent_results

            precincts_map[precinct_id] = precinct_entry

        choices = [
            {
                "index": idx,
                "id": idx,
                "label": label,
                "votes": choice_totals[idx],
            }
            for idx, label in enumerate(option_labels)
        ]

        contests.append(
            {
                "index": contest_index,
                "id": _contest_id(contest_name, contest_index),
                "label": contest_name,
                "voteFor": _to_int(contest.get("vote_for"), default=1),
                "choices": choices,
                "precincts": precincts_map,
            }
        )

    return {"contests": contests}


def build_metadata_payload(
    *,
    source_kind: str,
    source_value: str,
    election_id: str,
    run_started: datetime,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "generated": datetime.now(timezone.utc).date().isoformat(),
        "electionId": election_id,
        "source": {
            "kind": source_kind,
            "value": source_value,
        },
        "run": {
            "startedAt": run_started.isoformat(),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        },
    }


def _build_turnout_index(parsed_results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for item in parsed_results:
        if not item.get("ok"):
            continue
        payload = item.get("data")
        if not isinstance(payload, dict):
            continue
        if "contest" in payload:
            continue
        for precinct in payload.get("precincts", []):
            precinct_id = str(precinct.get("precinct", "")).strip()
            if not precinct_id:
                continue
            total_block = precinct.get("results", {}).get("Total", {})
            out[precinct_id] = {
                "registeredVoters": _to_int(total_block.get("registered_voters"), default=0),
                "totalVoters": _to_int(total_block.get("voters_cast"), default=0),
            }
    return out


def _contest_id(label: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    if not slug:
        slug = f"contest-{index + 1}"
    return slug


def _winner_index(results: list[int]) -> int | None:
    if not results:
        return None
    high = max(results)
    if high <= 0:
        return None
    if results.count(high) > 1:
        return None
    return results.index(high)


def _normalize_percent(value: Any) -> float:
    numeric = float(value)
    if numeric > 1:
        return numeric / 100.0
    return numeric


def _to_int(value: Any, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
