from video_agent.server.app import create_app_context



def test_list_video_tasks_returns_recent_tasks(temp_settings) -> None:
    app = create_app_context(temp_settings)
    app.task_service.create_video_task(prompt="one", idempotency_key="one")
    app.task_service.create_video_task(prompt="two", idempotency_key="two")

    tasks = app.task_service.list_video_tasks(limit=10)

    assert len(tasks) >= 2
    assert {item["task_id"] for item in tasks}
    assert all("status" in item for item in tasks)



def test_get_task_events_returns_event_history(temp_settings) -> None:
    app = create_app_context(temp_settings)
    created = app.task_service.create_video_task(prompt="one", idempotency_key="events")

    events = app.task_service.get_task_events(created.task_id)

    assert events[0]["event_type"] == "task_created"
    assert events[0]["payload"]["status"] == "queued"
