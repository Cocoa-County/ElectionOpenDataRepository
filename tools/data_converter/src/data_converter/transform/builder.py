from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any


_MAX_PALETTE_SHADES = 4
_YES_NO_COLORS = {
    "yes": "green1",
    "no": "red1",
}
_PARTY_PALETTES = {
    "dem": "blue",
    "rep": "red",
}
_PARTY_ALIASES = {
    "dem": "dem",
    "democrat": "dem",
    "democratic": "dem",
    "rep": "rep",
    "republican": "rep",
    "gop": "rep",
}


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

    grouped_contests: list[dict[str, Any]] = []
    grouped_lookup: dict[tuple[str, int], dict[str, Any]] = {}

    for record in contest_records:
        payload = record["data"]
        contest = payload.get("contest", {})
        contest_name = str(contest.get("contest_name", "")).strip()
        if not contest_name:
            continue
        vote_for = _to_int(contest.get("vote_for"), default=1)
        key = (contest_name, vote_for)
        if key not in grouped_lookup:
            grouped_lookup[key] = {
                "contest_name": contest_name,
                "vote_for": vote_for,
                "records": [],
            }
            grouped_contests.append(grouped_lookup[key])
        grouped_lookup[key]["records"].append(payload)

    for contest_index, group in enumerate(grouped_contests):
        contest_name = str(group["contest_name"])
        vote_for = int(group["vote_for"])

        option_labels: list[str] = []
        seen_options: set[str] = set()
        for payload in group["records"]:
            for opt in payload.get("options", []):
                label = str(opt)
                if label and label not in seen_options:
                    option_labels.append(label)
                    seen_options.add(label)

        precincts_map: dict[str, dict[str, Any]] = {}
        precinct_votes: dict[str, dict[str, int]] = {}
        precinct_percentages: dict[str, dict[str, float]] = {}
        precinct_registered: dict[str, int] = {}
        precinct_total_voters: dict[str, int] = {}
        precinct_total_votes: dict[str, int] = {}

        for payload in group["records"]:
            for precinct in payload.get("precincts", []):
                precinct_id = str(precinct.get("precinct", "")).strip()
                if not precinct_id:
                    continue

                results_block = precinct.get("results", {}).get(precinct_result_scope, {})
                if not isinstance(results_block, dict):
                    continue
                option_block = results_block.get("options", {})
                if not isinstance(option_block, dict):
                    option_block = {}

                vote_bucket = precinct_votes.setdefault(precinct_id, {})
                percent_bucket = precinct_percentages.setdefault(precinct_id, {})

                for option_label in option_labels:
                    opt_data = option_block.get(option_label, {})
                    if not isinstance(opt_data, dict):
                        continue
                    votes = _to_int(opt_data.get("votes"), default=0)
                    if option_label in vote_bucket:
                        vote_bucket[option_label] = max(vote_bucket[option_label], votes)
                    else:
                        vote_bucket[option_label] = votes

                    pct_raw = opt_data.get("percent")
                    if pct_raw is None:
                        continue
                    pct = _normalize_percent(pct_raw)
                    if option_label in percent_bucket:
                        percent_bucket[option_label] = max(percent_bucket[option_label], pct)
                    else:
                        percent_bucket[option_label] = pct

                parsed_total_votes = _to_int(results_block.get("total_votes"), default=0)
                precinct_total_votes[precinct_id] = max(
                    precinct_total_votes.get(precinct_id, 0),
                    parsed_total_votes,
                )

                parsed_registered = _to_int(results_block.get("registered_voters"), default=0)
                precinct_registered[precinct_id] = max(
                    precinct_registered.get(precinct_id, 0),
                    parsed_registered,
                )

                parsed_total_voters = _to_int(
                    results_block.get("times_cast", parsed_total_votes),
                    default=0,
                )
                precinct_total_voters[precinct_id] = max(
                    precinct_total_voters.get(precinct_id, 0),
                    parsed_total_voters,
                )

        choice_totals = [0 for _ in option_labels]

        for precinct_id, vote_bucket in precinct_votes.items():
            vote_results = [vote_bucket.get(option_label, 0) for option_label in option_labels]
            for idx, votes in enumerate(vote_results):
                choice_totals[idx] += votes

            percent_bucket = precinct_percentages.get(precinct_id, {})
            has_percent = bool(percent_bucket)
            percent_results = [percent_bucket.get(option_label, 0.0) for option_label in option_labels]

            total_votes = precinct_total_votes.get(precinct_id, 0)
            if total_votes <= 0:
                total_votes = sum(vote_results)

            turnout_row = turnout_by_precinct.get(precinct_id, {})
            registered_voters = _to_int(
                turnout_row.get("registeredVoters", precinct_registered.get(precinct_id, 0)),
                default=0,
            )
            total_voters = _to_int(
                turnout_row.get("totalVoters", precinct_total_voters.get(precinct_id, total_votes)),
                default=0,
            )

            winner_indexes = _winner_indexes(vote_results)

            precinct_entry: dict[str, Any] = {
                "label": precinct_id,
                "registeredVoters": registered_voters,
                "totalVoters": total_voters,
                "total": total_votes,
                "results": vote_results,
            }
            if winner_indexes:
                precinct_entry["winner"] = winner_indexes
            if has_percent:
                precinct_entry["percentage"] = percent_results

            precincts_map[precinct_id] = precinct_entry

        choice_order = sorted(
            range(len(option_labels)),
            key=lambda idx: (-choice_totals[idx], option_labels[idx]),
        )

        color_counts: dict[str, int] = {"dem": 0, "rep": 0}

        for precinct_entry in precincts_map.values():
            old_results = precinct_entry.get("results", [])
            precinct_entry["results"] = [old_results[idx] for idx in choice_order]

            if "percentage" in precinct_entry:
                old_percentages = precinct_entry.get("percentage", [])
                precinct_entry["percentage"] = [old_percentages[idx] for idx in choice_order]

            winner_indexes = _winner_indexes(precinct_entry["results"])
            if not winner_indexes:
                precinct_entry.pop("winner", None)
            else:
                precinct_entry["winner"] = winner_indexes

        choices = []
        for idx, source_idx in enumerate(choice_order):
            label = option_labels[source_idx]
            choice = {
                "index": idx,
                "id": idx,
                "label": label,
                "votes": choice_totals[source_idx],
            }
            color = _choice_color(label, color_counts)
            if color is not None:
                choice["color"] = color
            choices.append(choice)

        contests.append(
            {
                "index": contest_index,
                "id": _contest_id(contest_name, contest_index),
                "label": contest_name,
                "voteFor": vote_for,
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


def _choice_color(label: str, color_counts: dict[str, int]) -> str | None:
    normalized = _normalize_choice_label(label)
    if normalized in _YES_NO_COLORS:
        return _YES_NO_COLORS[normalized]

    party = _choice_party_family(normalized)
    if party is None:
        return None

    next_shade = color_counts.get(party, 0) + 1
    if next_shade > _MAX_PALETTE_SHADES:
        return None

    color_counts[party] = next_shade
    shade = next_shade
    return f"{_PARTY_PALETTES[party]}{shade}"


def _normalize_choice_label(label: str) -> str:
    return label.strip().lower()


def _choice_party_family(normalized_label: str) -> str | None:
    if normalized_label in _PARTY_ALIASES:
        return _PARTY_ALIASES[normalized_label]

    # Alameda-style labels use a leading party token, e.g. "DEM - Name".
    prefix_match = re.match(r"^([a-z]+)\s*-\s+", normalized_label)
    if prefix_match:
        party_prefix = prefix_match.group(1).strip()
        if party_prefix:
            mapped = _PARTY_ALIASES.get(party_prefix)
            if mapped is not None:
                return mapped

    if not normalized_label.endswith(")"):
        return None

    open_paren = normalized_label.rfind("(")
    if open_paren == -1:
        return None

    party_label = normalized_label[open_paren + 1 : -1].strip()
    if not party_label:
        return None
    return _PARTY_ALIASES.get(party_label)


def _winner_indexes(results: list[int]) -> list[int]:
    if not results:
        return []
    high = max(results)
    if high <= 0:
        return []
    return [idx for idx, value in enumerate(results) if value == high]


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
