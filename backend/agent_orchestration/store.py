from typing import Dict, List
from uuid import uuid4

from agent_orchestration.schemas import (
    AgentEpisode,
    AgentEpisodeCreate,
    AgentEvent,
    AgentEventCreate,
    AgentEventType,
    EpisodeStatus,
    NextStep,
    utc_now,
)
from realtime import manager as ws_manager


episodes: Dict[str, AgentEpisode] = {}
events_by_episode: Dict[str, List[AgentEvent]] = {}


def _short_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def create_episode(request: AgentEpisodeCreate) -> AgentEpisode:
    episode = AgentEpisode(
        id=_short_id("ep"),
        simulation_id=request.simulation_id,
        status=EpisodeStatus.active,
        trigger=request.trigger,
        user_preferences=request.user_preferences,
    )
    episodes[episode.id] = episode
    events_by_episode[episode.id] = []
    ws_manager.broadcast("episode_created", {"episode": episode.model_dump()})
    return episode


def list_episodes() -> List[AgentEpisode]:
    return sorted(episodes.values(), key=lambda episode: episode.created_at, reverse=True)


def get_episode(episode_id: str) -> AgentEpisode | None:
    return episodes.get(episode_id)


def get_events(episode_id: str) -> List[AgentEvent]:
    return events_by_episode.get(episode_id, [])


def _status_for_event(event_type: AgentEventType) -> EpisodeStatus | None:
    status_map = {
        AgentEventType.RED_PLAN: EpisodeStatus.waiting_for_blue_revised_plan,
        AgentEventType.BLUE_ASSESSMENT: EpisodeStatus.waiting_for_blue_revised_plan,
        AgentEventType.BLUE_REVISED_PLAN: EpisodeStatus.waiting_for_executor_narrator,
        AgentEventType.FINAL_ACTION: EpisodeStatus.waiting_for_executor_narrator,
        AgentEventType.EXECUTOR_ACTION: EpisodeStatus.executed,
        AgentEventType.EXECUTION_RESULT: EpisodeStatus.executed,
        AgentEventType.NARRATION: EpisodeStatus.completed,
        AgentEventType.MEMORY_LESSON: EpisodeStatus.completed,
    }
    return status_map.get(event_type)


def next_step_for_event(event_type: AgentEventType) -> NextStep:
    next_step_map = {
        AgentEventType.RED_PLAN: NextStep(suggested_agent="blue_agent", suggested_event_type=AgentEventType.BLUE_ASSESSMENT),
        AgentEventType.BLUE_ASSESSMENT: NextStep(suggested_agent="blue_agent", suggested_event_type=AgentEventType.BLUE_REVISED_PLAN),
        AgentEventType.BLUE_REVISED_PLAN: NextStep(suggested_agent="executor_narrator_agent", suggested_event_type=AgentEventType.EXECUTOR_ACTION),
        AgentEventType.FINAL_ACTION: NextStep(suggested_agent="executor_narrator_agent", suggested_event_type=AgentEventType.EXECUTOR_ACTION),
        AgentEventType.EXECUTOR_ACTION: NextStep(suggested_agent="executor_narrator_agent", suggested_event_type=AgentEventType.EXECUTION_RESULT),
        AgentEventType.EXECUTION_RESULT: NextStep(suggested_agent="executor_narrator_agent", suggested_event_type=AgentEventType.KPI_EVALUATION),
        AgentEventType.KPI_EVALUATION: NextStep(suggested_agent="executor_narrator_agent", suggested_event_type=AgentEventType.NARRATION),
        AgentEventType.NARRATION: NextStep(suggested_agent="memory_agent", suggested_event_type=AgentEventType.MEMORY_LESSON),
    }
    return next_step_map.get(event_type, NextStep())


def add_event(request: AgentEventCreate) -> tuple[AgentEvent, NextStep]:
    event = AgentEvent(id=_short_id("evt"), **request.model_dump())
    events_by_episode.setdefault(request.episode_id, []).append(event)
    episode = episodes[request.episode_id]
    next_status = _status_for_event(request.event_type)
    if next_status:
        episode.status = next_status
    episode.updated_at = utc_now()
    episodes[request.episode_id] = episode
    next_step = next_step_for_event(request.event_type)
    ws_manager.broadcast("agent_event", {
        "event": event.model_dump(),
        "episode": episode.model_dump(),
        "next_step": next_step.model_dump(),
    })
    return event, next_step


def complete_episode(episode_id: str) -> AgentEpisode:
    episode = episodes[episode_id]
    episode.status = EpisodeStatus.completed
    episode.updated_at = utc_now()
    episodes[episode_id] = episode
    ws_manager.broadcast("episode_completed", {"episode": episode.model_dump()})
    return episode


def latest_final_action_event(episode_id: str) -> AgentEvent | None:
    events = get_events(episode_id)
    for desired_type in (
        AgentEventType.FINAL_ACTION,
        AgentEventType.BLUE_REVISED_PLAN,
        AgentEventType.RED_PLAN,
    ):
        for event in reversed(events):
            if event.event_type == desired_type:
                return event
    return None
