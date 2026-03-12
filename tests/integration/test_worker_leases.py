from video_agent.server.app import create_app_context



def test_worker_claims_queued_task_once(temp_settings) -> None:
    app_context = create_app_context(temp_settings)
    created = app_context.task_service.create_video_task(prompt="draw a circle", idempotency_key="lease")
    processed = app_context.worker.run_once()
    snapshot = app_context.task_service.get_video_task(created.task_id)

    assert processed == 1
    assert snapshot.phase != "queued"
