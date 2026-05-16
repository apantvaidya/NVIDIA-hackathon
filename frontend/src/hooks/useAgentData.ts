import { useCallback, useEffect, useState } from "react";
import { getAgentEpisodeTimeline, listAgentEpisodes, safeCall } from "../api/client";
import type { AgentEpisode, AgentEvent } from "../api/types";

export function useAgentData() {
  const [episodes, setEpisodes] = useState<AgentEpisode[]>([]);
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<string>();
  const [timelineEvents, setTimelineEvents] = useState<AgentEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const refresh = useCallback(async () => {
    const episodesResult = await safeCall("agent episodes", listAgentEpisodes);
    if (episodesResult.data) {
      setEpisodes(episodesResult.data);
      setSelectedEpisodeId((current) => current || episodesResult.data?.[0]?.id);
    }

    const episodeId = selectedEpisodeId || episodesResult.data?.[0]?.id;
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
    const interval = window.setInterval(refresh, 3000);
    return () => window.clearInterval(interval);
  }, [refresh]);

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
