import { useCallback, useEffect, useState } from "react";
import { getAgentEpisodeTimeline, listAgentEpisodes, safeCall } from "../api/client";
import { connectRealtime } from "../api/realtime";
import type { AgentEpisode, AgentEvent } from "../api/types";

export function useAgentData() {
  const [episodes, setEpisodes] = useState<AgentEpisode[]>([]);
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<string>();
  const [timelineEvents, setTimelineEvents] = useState<AgentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const refresh = useCallback(async () => {
    const episodesResult = await safeCall("agent episodes", listAgentEpisodes);
    let episodeId = selectedEpisodeId;
    if (episodesResult.data) {
      const nextEpisodes = episodesResult.data;
      setEpisodes(nextEpisodes);
      episodeId = nextEpisodes.some((episode) => episode.id === selectedEpisodeId)
        ? selectedEpisodeId
        : nextEpisodes[0]?.id;
      setSelectedEpisodeId(episodeId);
    }

    if (episodeId) {
      const timelineResult = await safeCall("agent timeline", () => getAgentEpisodeTimeline(episodeId));
      if (timelineResult.data) setTimelineEvents(timelineResult.data.events || []);
      setError([episodesResult.error, timelineResult.error].filter(Boolean).join(" | ") || undefined);
    } else {
      setTimelineEvents([]);
      setError(episodesResult.error);
    }
    setLoading(false);
  }, [selectedEpisodeId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const dispose = connectRealtime((message) => {
      const { type, payload } = message;
      if (type === "episode_created") {
        const ep = payload?.episode as AgentEpisode | undefined;
        if (!ep) return;
        setEpisodes((prev) => [ep, ...prev.filter((e) => e.id !== ep.id)]);
        setSelectedEpisodeId((current) => current || ep.id);
      } else if (type === "agent_state_reset") {
        setEpisodes([]);
        setSelectedEpisodeId(undefined);
        setTimelineEvents([]);
        setError(undefined);
      } else if (type === "episode_completed") {
        const ep = payload?.episode as AgentEpisode | undefined;
        if (!ep) return;
        setEpisodes((prev) => prev.map((e) => (e.id === ep.id ? ep : e)));
      } else if (type === "agent_event") {
        const evt = payload?.event as AgentEvent | undefined;
        const ep = payload?.episode as AgentEpisode | undefined;
        if (ep) setEpisodes((prev) => prev.map((e) => (e.id === ep.id ? ep : e)));
        if (!evt) return;
        setSelectedEpisodeId((current) => {
          const target = current || ep?.id;
          if (target && evt.episode_id === target) {
            setTimelineEvents((events) =>
              events.some((e) => e.id === evt.id) ? events : [...events, evt],
            );
          }
          return target;
        });
      }
    });
    return dispose;
  }, []);

  return {
    episodes,
    selectedEpisodeId,
    setSelectedEpisodeId,
    timelineEvents,
    loading,
    error,
    refresh,
  };
}
