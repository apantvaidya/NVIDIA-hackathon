from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class EpisodeStatus(str, Enum):
    active = "active"
    waiting_for_red_plan = "waiting_for_red_plan"
    waiting_for_blue_revised_plan = "waiting_for_blue_revised_plan"
    waiting_for_executor_narrator = "waiting_for_executor_narrator"
    executed = "executed"
    completed = "completed"


class AgentEventType(str, Enum):
    RED_PLAN = "RED_PLAN"
    BLUE_ASSESSMENT = "BLUE_ASSESSMENT"
    BLUE_REVISED_PLAN = "BLUE_REVISED_PLAN"
    FINAL_ACTION = "FINAL_ACTION"
    EXECUTOR_ACTION = "EXECUTOR_ACTION"
    EXECUTION_RESULT = "EXECUTION_RESULT"
    KPI_EVALUATION = "KPI_EVALUATION"
    NARRATION = "NARRATION"
    MEMORY_LESSON = "MEMORY_LESSON"


class AgentEpisodeCreate(BaseModel):
    simulation_id: str = "default"
    trigger: Dict[str, Any] = Field(default_factory=dict)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)


class AgentEpisode(BaseModel):
    id: str
    simulation_id: str = "default"
    status: EpisodeStatus = EpisodeStatus.active
    trigger: Dict[str, Any] = Field(default_factory=dict)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class AgentEventCreate(BaseModel):
    episode_id: str
    agent_id: str
    event_type: AgentEventType
    title: str
    summary: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    target_event_id: Optional[str] = None


class AgentEvent(BaseModel):
    id: str
    episode_id: str
    agent_id: str
    event_type: AgentEventType
    title: str
    summary: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    target_event_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now)


class NextStep(BaseModel):
    suggested_agent: Optional[str] = None
    suggested_event_type: Optional[AgentEventType] = None


class AgentEventAccepted(BaseModel):
    status: str = "accepted"
    event: AgentEvent
    next_step: NextStep


class EpisodeTimeline(BaseModel):
    episode: AgentEpisode
    events: List[AgentEvent]
