import { useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";

import { createTask, listTasks } from "../../lib/tasksApi";
import { useSession } from "../auth/useSession";

type TaskListItem = { task_id: string; status: string };

export function TasksPage() {
  const { sessionToken } = useSession();
  const promptId = useId();

  const [prompt, setPrompt] = useState("");
  const [items, setItems] = useState<TaskListItem[]>([]);
  const [loadingState, setLoadingState] = useState<"idle" | "loading" | "error">("idle");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!sessionToken) return;
    setLoadingState("loading");
    setError(null);
    try {
      const response = await listTasks(sessionToken);
      setItems(Array.isArray(response.items) ? response.items : []);
      setLoadingState("idle");
    } catch (err) {
      setLoadingState("error");
      setError(err instanceof Error ? err.message : "task_list_failed");
    }
  }

  useEffect(() => {
    refresh();
    // refresh is intentionally not a dependency; it's stable for our use.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionToken]);

  async function onCreate(event: React.FormEvent) {
    event.preventDefault();
    if (!sessionToken) return;
    const trimmed = prompt.trim();
    if (!trimmed) return;

    setCreating(true);
    setError(null);
    try {
      const created = await createTask(trimmed, sessionToken);
      setPrompt("");
      if (created?.task_id) {
        // Optimistic insert so the operator sees the new id immediately.
        setItems((prev) => [{ task_id: created.task_id, status: "queued" }, ...prev]);
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "task_create_failed");
    } finally {
      setCreating(false);
    }
  }

  if (!sessionToken) {
    return (
      <section>
        <h2>Tasks</h2>
        <p className="muted">Not authenticated.</p>
      </section>
    );
  }

  return (
    <section className="tasksPage">
      <header className="sectionHeader">
        <div>
          <h2>Tasks</h2>
          <p className="muted" style={{ margin: 0 }}>
            Create tasks and review their progress and artifacts.
          </p>
        </div>
        <button className="button buttonQuiet" type="button" onClick={refresh} disabled={loadingState === "loading"}>
          Refresh
        </button>
      </header>

      <div className="tasksGrid">
        <form className="card tasksComposer" onSubmit={onCreate} aria-label="create task form">
          <div className="cardTitle">New task</div>
          <div className="muted small">Write a single prompt. You can iterate in the task detail view.</div>

          <label className="field" htmlFor={promptId}>
            <span className="fieldLabel">Prompt</span>
            <textarea
              id={promptId}
              aria-label="Prompt"
              className="textarea"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder='e.g. "draw a circle", "animate a sine wave", "show a bar chart"'
              rows={5}
              spellCheck={false}
            />
          </label>

          <div className="buttonRow">
            <button className="button buttonPrimary" type="submit" disabled={creating || prompt.trim().length === 0}>
              {creating ? "Creating…" : "Create task"}
            </button>
          </div>

          {error ? (
            <p role="alert" className="alert">
              {error}
            </p>
          ) : null}
        </form>

        <div className="card tasksList" aria-label="task list">
          <div className="cardTitle">Recent</div>
          <div className="muted small">Most recent tasks first.</div>

          {loadingState === "loading" && items.length === 0 ? <p className="muted">Loading…</p> : null}

          {items.length ? (
            <ul className="taskItems">
              {items.map((task) => (
                <li key={task.task_id} className="taskItem">
                  <Link className="taskLink" to={`/tasks/${encodeURIComponent(task.task_id)}`}>
                    <span className="taskId">{task.task_id}</span>
                    <span className={`taskStatus taskStatus_${String(task.status).toLowerCase()}`}>
                      {String(task.status)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : loadingState === "error" ? (
            <p className="muted">Failed to load tasks.</p>
          ) : (
            <p className="muted">No tasks yet. Create one to get started.</p>
          )}
        </div>
      </div>
    </section>
  );
}

