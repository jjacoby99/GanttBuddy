from __future__ import annotations

import datetime as dt

from models.analytics import parse_normalized_breakdown, parse_normalized_overview


def test_parse_normalized_breakdown_accepts_work_type_component_grouping():
    payload = {
        "project_id": "project-123",
        "as_of": dt.datetime(2026, 4, 30, 12, 0, tzinfo=dt.UTC).isoformat(),
        "grouping": "work_type_component",
        "include_subcomponents": False,
        "allocation_basis": "Actual hours are allocated directly from scoped tasks.",
        "kpis": [
            {"key": "strip_feed_rows", "label": "Strip Feed Rows", "value": 12},
            {"key": "strip_feed_pieces", "label": "Strip Feed Pieces", "value": 96},
        ],
        "rows": [
            {
                "key": "STRIP:FEED",
                "label": "STRIP / FEED",
                "task_count": 2,
                "quantified_task_count": 2,
                "planned_hours": 18.0,
                "actual_hours": 20.0,
                "quantified_actual_hours": 20.0,
                "unquantified_actual_hours": 0.0,
                "quantified_actual_hours_pct": 1.0,
                "planned_rows": 4.0,
                "actual_rows": 4.0,
                "planned_liners": 32.0,
                "actual_liners": 32.0,
                "planned_hours_per_row": 4.5,
                "actual_hours_per_row": 5.0,
                "planned_hours_per_liner": 0.5625,
                "actual_hours_per_liner": 0.625,
                "actual_rows_per_hour": 0.2,
                "actual_liners_per_hour": 1.6,
                "rows_attainment_ratio": 1.0,
                "liners_attainment_ratio": 1.0,
                "rows_variance_pct": 0.0,
                "liners_variance_pct": 0.0,
                "hours_per_row_variance_pct": 0.1111,
                "hours_per_liner_variance_pct": 0.1111,
            }
        ],
    }

    parsed = parse_normalized_breakdown(payload)

    assert parsed.grouping == "work_type_component"
    assert parsed.kpis[0].key == "strip_feed_rows"
    assert parsed.rows[0].label == "STRIP / FEED"
    assert parsed.rows[0].hours_per_row_variance_pct == 0.1111


def test_parse_normalized_overview_preserves_component_kpis():
    payload = {
        "project_id": "project-123",
        "as_of": dt.datetime(2026, 4, 30, 12, 0, tzinfo=dt.UTC).isoformat(),
        "kpis": [
            {"key": "install_shell_rows", "label": "Install Shell Rows", "value": 10},
            {"key": "install_shell_pieces", "label": "Install Shell Pieces", "value": 80},
        ],
        "summary": {
            "task_count": 4,
            "quantified_task_count": 4,
            "planned_hours": 30.0,
            "actual_hours": 28.0,
            "quantified_actual_hours": 28.0,
            "unquantified_actual_hours": 0.0,
            "quantified_actual_hours_pct": 1.0,
            "planned_rows": 10.0,
            "actual_rows": 10.0,
            "planned_liners": 80.0,
            "actual_liners": 80.0,
            "planned_hours_per_row": 3.0,
            "actual_hours_per_row": 2.8,
            "planned_hours_per_liner": 0.375,
            "actual_hours_per_liner": 0.35,
            "actual_rows_per_hour": 0.357,
            "actual_liners_per_hour": 2.857,
            "rows_attainment_ratio": 1.0,
            "liners_attainment_ratio": 1.0,
            "rows_variance_pct": 0.0,
            "liners_variance_pct": 0.0,
            "hours_per_row_variance_pct": -0.0667,
            "hours_per_liner_variance_pct": -0.0667,
        },
    }

    parsed = parse_normalized_overview(payload)

    assert [item.key for item in parsed.kpis] == ["install_shell_rows", "install_shell_pieces"]
    assert parsed.summary.actual_hours_per_row == 2.8
    assert parsed.summary.hours_per_row_variance_pct == -0.0667
