import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useSession } from "../auth/useSession";
import { VideoThreadWorkbench } from "./VideoThreadWorkbench";
import { SelectedVersionHero } from "./SelectedVersionHero";
import { ThreadDiscussionPanel } from "./ThreadDiscussionPanel";
import { useTaskArtifactDownloads } from "./useTaskArtifactDownloads";
import {
  appendVideoTurn,
  getVideoThreadIteration,
  getVideoThreadSurface,
  removeVideoThreadParticipant,
  requestVideoExplanation,
  requestVideoRevision,
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

function selectedTaskIdFromSurface(surface: VideoThreadSurface | null, iterationId: string | null): string | null {
  if (!surface) {
    return null;
  }

  const activeIterationId = iterationId ?? surface.current_focus.current_iteration_id ?? null;
  if (activeIterationId) {
    const processRunTaskId =
      surface.process.runs.find((run) => run.iteration_id === activeIterationId && run.task_id)?.task_id ?? null;
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
    iterationDetail?.results.find((result) => result.result_id === surface?.current_focus.current_result_id) ??
    null;
  const selectedTaskId =
    selectedTaskIdFromSurface(surface, selectedIterationId) ??
    iterationDetail?.runs.find((run) => run.task_id)?.task_id ??
    taskIdFromVideoResource(selectedResult?.video_resource) ??
    null;
  const { downloads, error: downloadError } = useTaskArtifactDownloads(selectedTaskId, sessionToken);

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
          nextSurface.iteration_detail?.selected_iteration_id ??
            nextSurface.current_focus.current_iteration_id ??
            nextSurface.iteration_workbench.selected_iteration_id ??
            null
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

  async function refreshSurface() {
    if (!threadId || !sessionToken) {
      return;
    }
    const nextSurface = await getVideoThreadSurface(threadId, sessionToken);
    setSurface(nextSurface);
    setSelectedIterationId((current) =>
      current && nextSurface.iteration_workbench.iterations.some((item) => item.iteration_id === current)
        ? current
        : nextSurface.iteration_detail?.selected_iteration_id ??
          nextSurface.current_focus.current_iteration_id ??
          nextSurface.iteration_workbench.selected_iteration_id ??
          null
    );
    setActiveActionId((current) =>
      current && nextSurface.actions.items.some((item) => item.action_id === current)
        ? current
        : nextSurface.actions.items[0]?.action_id ?? null
    );
    setParticipantDraft((current) => ({
      ...current,
      role: current.role || nextSurface.participants.management.default_role || "reviewer",
    }));
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
      await refreshSurface();
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
      <VideoThreadWorkbench
        surface={surface}
        iterationDetail={iterationDetail}
        selectedIterationId={selectedIterationId}
        iterationLoading={iterationLoading}
        participantSubmitting={participantSubmitting}
        participantDraft={participantDraft}
        onSelectIteration={setSelectedIterationId}
        onParticipantDraftChange={(field, value) =>
          setParticipantDraft((current) => ({ ...current, [field]: value }))
        }
        onInviteParticipant={onInviteParticipant}
        onRemoveParticipant={onRemoveParticipant}
      />
    </div>
  );
}
