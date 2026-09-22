async def test_project_transitions_and_assignment_lifecycle(authenticated):
    client = authenticated
    company = (
        await client.post("/api/v1/companies", json={"name": "Projects"})
    ).headers["location"]
    employee = await client.post(
        company + "/employees", json={"full_name": "Worker", "start_date": "2026-01-01"}
    )
    project = await client.post(company + "/projects", json={"name": "Delivery"})
    assert project.status_code == 201, project.text
    path = project.headers["location"]
    assignment = path + "/employees/" + employee.json()["id"]
    assert (await client.put(assignment)).status_code == 201
    assert (await client.put(assignment)).status_code == 200
    assert len((await client.get(path + "/employees")).json()["items"]) == 1
    assert (
        await client.patch(
            path, json={"status": "completed"}, headers={"If-Match": '"v1"'}
        )
    ).status_code == 409
    assert (
        await client.patch(
            path, json={"status": "active"}, headers={"If-Match": '"v1"'}
        )
    ).status_code == 200
    assert (
        await client.patch(
            path, json={"status": "completed"}, headers={"If-Match": '"v2"'}
        )
    ).status_code == 200
    assert (await client.put(assignment)).status_code == 200
    assert (await client.delete(assignment)).status_code == 204
    assert (await client.delete(assignment)).status_code == 204
    assert (await client.put(assignment)).status_code == 409
    assert (await client.delete(path, headers={"If-Match": '"v3"'})).status_code == 204


async def test_termination_removes_assignments(authenticated):
    client = authenticated
    company = (
        await client.post("/api/v1/companies", json={"name": "Termination"})
    ).headers["location"]
    employee = await client.post(
        company + "/employees", json={"full_name": "Worker", "start_date": "2026-01-01"}
    )
    project = await client.post(company + "/projects", json={"name": "Project"})
    path = project.headers["location"]
    assert (
        await client.put(path + "/employees/" + employee.json()["id"])
    ).status_code == 201
    result = await client.patch(
        employee.headers["location"],
        json={"status": "terminated", "end_date": "2026-09-01"},
        headers={"If-Match": '"v1"'},
    )
    assert result.status_code == 200, result.text
    assert (await client.get(path + "/employees")).json()["items"] == []
