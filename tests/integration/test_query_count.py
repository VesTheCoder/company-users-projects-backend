from sqlalchemy import event


async def test_employee_list_query_count_does_not_grow_with_page_size(
    authenticated, application
):
    company = (
        await authenticated.post("/api/v1/companies", json={"name": "Bounded queries"})
    ).headers["location"]
    for index in range(4):
        await authenticated.post(
            company + "/employees",
            json={"full_name": f"Employee {index}", "start_date": "2026-01-01"},
        )
    statements = []

    def count(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = application.state.engine.sync_engine
    event.listen(engine, "before_cursor_execute", count)
    try:
        assert (
            await authenticated.get(company + "/employees?limit=1")
        ).status_code == 200
        first = len(statements)
        statements.clear()
        assert (
            await authenticated.get(company + "/employees?limit=100")
        ).status_code == 200
        assert len(statements) == first == 4
    finally:
        event.remove(engine, "before_cursor_execute", count)
