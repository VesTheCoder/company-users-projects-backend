from datetime import UTC, datetime

from scripts.load_dataset import PROFILES, dataset_rows, employee_company, load_id


def test_load_profile_counts_skew_and_assignment_integrity():
    counts = PROFILES["small"]
    assert (
        sum(employee_company(i, counts) == 0 for i in range(counts["employees"]))
        == 1000
    )
    rows = list(
        dataset_rows("project_employees", counts, "hash", "secret", datetime.now(UTC))
    )
    assert len(rows) == counts["assignments"]
    assert len({row[:3] for row in rows}) == len(rows)
    employees = {
        load_id(3, i): load_id(2, employee_company(i, counts))
        for i in range(counts["employees"])
    }
    projects = {
        load_id(4, i): load_id(2, i % counts["companies"])
        for i in range(counts["projects"])
    }
    assert all(employees[row[2]] == projects[row[1]] == row[0] for row in rows)
