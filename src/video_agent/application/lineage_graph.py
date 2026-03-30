from __future__ import annotations

from collections.abc import Sequence

from video_agent.domain.models import VideoTask


def reachable_lineage_tasks(*, lineage_tasks: Sequence[VideoTask], root_task_id: str) -> list[VideoTask]:
    root_task = next((task for task in lineage_tasks if task.task_id == root_task_id), None)
    if root_task is None:
        return []

    reachable: list[VideoTask] = [root_task]
    reachable_ids = {root_task_id}
    for task in lineage_tasks:
        if task.task_id == root_task_id:
            continue
        if task.parent_task_id in reachable_ids:
            reachable.append(task)
            reachable_ids.add(task.task_id)
    return reachable


def orphaned_lineage_tasks(*, lineage_tasks: Sequence[VideoTask], root_task_id: str) -> list[VideoTask]:
    reachable_ids = {
        task.task_id
        for task in reachable_lineage_tasks(lineage_tasks=lineage_tasks, root_task_id=root_task_id)
    }
    return [task for task in lineage_tasks if task.task_id not in reachable_ids]
