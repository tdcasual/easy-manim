import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useSession } from "../auth/useSession";
import { ProcessDetailsAccordion } from "./ProcessDetailsAccordion";
import { VideoThreadWorkbench } from "./VideoThreadWorkbench";
import { SelectedVersionHero } from "./SelectedVersionHero";
import { ThreadDiscussionPanel } from "./ThreadDiscussionPanel";
import { useTaskArtifactDownloads } from "./useTaskArtifactDownloads";
import { VersionTimeline } from "./VersionTimeline";
import {
  appendVideoTurn,
  getVideoThreadIteration,
  getVideoThreadSurface,
  removeVideoThreadParticipant,
  requestVideoExplanation,
  requestVideoRevision,
  selectVideoResult,
  upsertVideoThreadParticipant,
  type VideoThreadIterationDetail,
  type VideoThreadSurface,
} from "../../lib/videoThreadsApi";

function taskIdFromVideoResource(resource: string | null | undefined): string | null {
  if (!resource) {
    return null;
  }
  const match = /^video-task:\/\/([^/]+)\//.exec(resource);
  return match?.[1] ?? null;
}

function selectedTaskIdFromSurface(
  surface: VideoThreadSurface | null,
  iterationId: string | null
): string | null {
  if (!surface) {
    return null;
  }

  const activeIterationId = iterationId ?? surface.current_focus.current_iteration_id ?? null;
  if (activeIterationId) {
    const processRunTaskId =
      surface.process.runs.find((run) => run.iteration_id === activeIterationId && run.task_id)
        ?.task_id ?? null;
    if (processRunTaskId) {
      return processRunTaskId;
    }

    const journalTaskId =
      surface.production_journal.entries.find(
        (entry) => entry.iteration_id === activeIterationId && entry.task_id
      )?.task_id ?? null;
    if (journalTaskId) {
      return journalTaskId;
    }
  }

  return null;
}

function defaultSelectedIterationId(surface: VideoThreadSurface): string | null {
  return (
    surface.iteration_detail?.selected_iteration_id ??
    surface.current_focus.current_iteration_id ??
    surface.iteration_workbench.selected_iteration_id ??
    null
  );
}

function resolveSelectedIterationId(
  surface: VideoThreadSurface,
  currentIterationId: string | null,
  options?: { preserveCurrent?: boolean }
): string | null {
  if (
    options?.preserveCurrent !== false &&
    currentIterationId &&
    surface.iteration_workbench.iterations.some((item) => item.iteration_id === currentIterationId)
  ) {
    return currentIterationId;
  }

  return defaultSelectedIterationId(surface);
}

export function VideoThreadPage() {
  const { threadId } = useParams();
  const { sessionToken } = useSession();
  const [surface, setSurface] = useState<VideoThreadSurface | null>(null);
  const [iterationDetail, setIterationDetail] = useState<VideoThreadIterationDetail | null>(null);
  const [selectedIterationId, setSelectedIterationId] = useState<string | null>(null);
  const [iterationLoading, setIterationLoading] = useState(false);
  const [draft, setDraft] = useState("");
  const [activeActionId, setActiveActionId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [selectingResultId, setSelectingResultId] = useState<string | null>(null);
  const [participantSubmitting, setParticipantSubmitting] = useState(false);
  const [participantDraft, setParticipantDraft] = useState({
    agentId: "",
    displayName: "",
    role: "reviewer",
  });
  const [error, setError] = useState<string | null>(null);
  const activeComposerTarget = iterationDetail?.composer_target ?? surface?.composer.target ?? null;
  const selectedResult =
    iterationDetail?.results.find((result) => result.selected) ??
    iterationDetail?.results.find(
      (result) => result.result_id === surface?.current_focus.current_result_id
    ) ??
    null;
  const selectedTaskId =
    taskIdFromVideoResource(selectedResult?.video_resource) ??
    iterationDetail?.runs.find((run) => run.task_id)?.task_id ??
    selectedTaskIdFromSurface(surface, selectedIterationId) ??
    null;
  const { downloads, error: downloadError } = useTaskArtifactDownloads(
    selectedTaskId,
    sessionToken
  );

  useEffect(() => {
    if (!threadId || !sessionToken) {
      return;
    }

    let cancelled = false;
    getVideoThreadSurface(threadId, sessionToken)
      .then((nextSurface) => {
        if (cancelled) {
          return;
        }
        setSurface(nextSurface);
        setActiveActionId(nextSurface.actions.items[0]?.action_id ?? null);
        setSelectedIterationId(
          resolveSelectedIterationId(nextSurface, null, { preserveCurrent: false })
        );
        setParticipantDraft((current) => ({
          ...current,
          role: current.role || nextSurface.participants.management.default_role || "reviewer",
        }));
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load video thread");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [sessionToken, threadId]);

  useEffect(() => {
    if (!threadId || !sessionToken || !selectedIterationId) {
      setIterationDetail(null);
      return;
    }

    let cancelled = false;
    setIterationLoading(true);
    getVideoThreadIteration(threadId, selectedIterationId, sessionToken)
      .then((detail) => {
        if (!cancelled) {
          setIterationDetail(detail);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load iteration detail");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIterationLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedIterationId, sessionToken, threadId]);

  async function refreshIterationDetail(iterationId: string) {
    if (!threadId || !sessionToken) {
      return;
    }
    setIterationLoading(true);
    try {
      const detail = await getVideoThreadIteration(threadId, iterationId, sessionToken);
      setIterationDetail(detail);
    } finally {
      setIterationLoading(false);
    }
  }

  async function refreshSurface(options?: { preserveCurrentIteration?: boolean }) {
    if (!threadId || !sessionToken) {
      return;
    }
    const nextSurface = await getVideoThreadSurface(threadId, sessionToken);
    const nextSelectedIterationId = resolveSelectedIterationId(nextSurface, selectedIterationId, {
      preserveCurrent: options?.preserveCurrentIteration !== false,
    });
    setSurface(nextSurface);
    setSelectedIterationId(nextSelectedIterationId);
    setActiveActionId((current) =>
      current && nextSurface.actions.items.some((item) => item.action_id === current)
        ? current
        : (nextSurface.actions.items[0]?.action_id ?? null)
    );
    setParticipantDraft((current) => ({
      ...current,
      role: current.role || nextSurface.participants.management.default_role || "reviewer",
    }));
    return nextSelectedIterationId;
  }

  async function onSubmit() {
    if (!threadId || !sessionToken || !surface) {
      return;
    }
    const iterationId =
      selectedIterationId ??
      surface.iteration_detail?.selected_iteration_id ??
      surface.current_focus.current_iteration_id ??
      surface.iteration_workbench.selected_iteration_id;
    if (!iterationId) {
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const preserveCurrentIteration = activeActionId !== "request_revision";
      if (activeActionId === "request_revision") {
        await requestVideoRevision(
          threadId,
          iterationId,
          { summary: draft, preserve_working_parts: true },
          sessionToken
        );
      } else if (activeActionId === "request_explanation") {
        await requestVideoExplanation(threadId, iterationId, { summary: draft }, sessionToken);
      } else {
        await appendVideoTurn(
          threadId,
          {
            iteration_id: iterationId,
            title: draft,
            summary: draft,
            addressed_participant_id: activeComposerTarget?.addressed_participant_id ?? undefined,
            reply_to_turn_id: iterationDetail?.execution_summary.reply_to_turn_id ?? undefined,
            related_result_id:
              iterationDetail?.execution_summary.result_id ??
              activeComposerTarget?.result_id ??
              undefined,
          },
          sessionToken
        );
      }
      setDraft("");
      const nextIterationId = await refreshSurface({
        preserveCurrentIteration,
      });
      if (!nextIterationId) {
        setIterationDetail(null);
      } else if (nextIterationId === selectedIterationId) {
        await refreshIterationDetail(nextIterationId);
      } else {
        setIterationDetail(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update thread");
    } finally {
      setSubmitting(false);
    }
  }

  async function onInviteParticipant() {
    if (!threadId || !sessionToken || !surface) {
      return;
    }
    const agentId = participantDraft.agentId.trim();
    if (!agentId) {
      return;
    }
    const management = surface.participants.management;

    setParticipantSubmitting(true);
    setError(null);
    try {
      await upsertVideoThreadParticipant(
        threadId,
        {
          participant_id: agentId,
          participant_type: "agent",
          agent_id: agentId,
          role: participantDraft.role.trim() || management.default_role || "reviewer",
          display_name: participantDraft.displayName.trim() || agentId,
          capabilities: management.default_capabilities,
        },
        sessionToken
      );
      setParticipantDraft({
        agentId: "",
        displayName: "",
        role: management.default_role || "reviewer",
      });
      await refreshSurface();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update thread participants");
    } finally {
      setParticipantSubmitting(false);
    }
  }

  async function onRemoveParticipant(participantId: string) {
    if (!threadId || !sessionToken) {
      return;
    }

    setParticipantSubmitting(true);
    setError(null);
    try {
      await removeVideoThreadParticipant(threadId, participantId, sessionToken);
      await refreshSurface();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update thread participants");
    } finally {
      setParticipantSubmitting(false);
    }
  }

  async function onSelectResult(resultId: string) {
    if (!threadId || !sessionToken || !selectedIterationId) {
      return;
    }

    setSelectingResultId(resultId);
    setError(null);
    try {
      await selectVideoResult(threadId, selectedIterationId, { result_id: resultId }, sessionToken);
      await refreshSurface();
      await refreshIterationDetail(selectedIterationId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to select version");
    } finally {
      setSelectingResultId(null);
    }
  }

  if (!threadId) {
    return <div className="page-v2">Missing thread id.</div>;
  }

  if (!surface) {
    return (
      <div className="page-v2">
        <div className="page-header-v2">
          <div className="page-header-content-v2">
            <Link to="/videos" className="back-link">
              Back to videos
            </Link>
          </div>
        </div>
        {error ? <div role="alert">{error}</div> : <div>Loading video thread…</div>}
      </div>
    );
  }

  return (
    <div className="page-v2">
      <div className="page-header-v2">
        <div className="page-header-content-v2">
          <Link to="/videos" className="back-link">
            Back to videos
          </Link>
          <h1 className="page-title-v2">{surface.thread_header.title}</h1>
          <p className="page-description-v2">{surface.thread_header.thread_id}</p>
        </div>
      </div>
      {error ? <div role="alert">{error}</div> : null}
      <SelectedVersionHero
        surface={surface}
        selectedIterationId={selectedIterationId}
        selectedResult={selectedResult}
        selectedTaskId={selectedTaskId}
        downloads={downloads}
        downloadError={downloadError}
      />
      <ThreadDiscussionPanel
        surface={surface}
        activeActionId={activeActionId}
        activeComposerTarget={activeComposerTarget}
        replyToTurnId={
          surface.discussion_runtime?.default_reply_to_turn_id ??
          iterationDetail?.execution_summary.reply_to_turn_id ??
          null
        }
        draft={draft}
        submitting={submitting}
        onDraftChange={setDraft}
        onSelectAction={setActiveActionId}
        onSubmit={onSubmit}
      />
      <VersionTimeline
        results={iterationDetail?.results ?? []}
        selectedResultId={
          selectedResult?.result_id ?? surface.current_focus.current_result_id ?? null
        }
        selectingResultId={selectingResultId}
        onSelectResult={onSelectResult}
      />
      <ProcessDetailsAccordion
        iterationCount={surface.iteration_workbench.iterations.length}
        participantCount={surface.participants.items.length}
        runCount={surface.process.runs.length}
      >
        <VideoThreadWorkbench
          surface={surface}
          iterationDetail={iterationDetail}
          selectedIterationId={selectedIterationId}
          iterationLoading={iterationLoading}
          showThreadHeader={false}
          participantSubmitting={participantSubmitting}
          participantDraft={participantDraft}
          onSelectIteration={setSelectedIterationId}
          onParticipantDraftChange={(field, value) =>
            setParticipantDraft((current) => ({ ...current, [field]: value }))
          }
          onInviteParticipant={onInviteParticipant}
          onRemoveParticipant={onRemoveParticipant}
        />
      </ProcessDetailsAccordion>
    </div>
  );
}
