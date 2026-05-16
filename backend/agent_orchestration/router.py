from fastapi import APIRouter, HTTPException

from agent_orchestration.schemas import (
    AgentEpisodeCreate,
    AgentEventAccepted,
    AgentEventCreate,
    EpisodeTimeline,
)
from agent_orchestration.store import (
    add_event,
    complete_episode,
    create_episode,
    get_episode,
    get_events,
    latest_final_action_event,
    list_episodes,
)
from simulation.kpi_engine import calculate_kpis
from simulation.state import get_world_state


router = APIRouter()


AVAILABLE_ACTION_ENDPOINTS = [
    {"action_type": "transfer_inventory", "simulate_endpoint": "/simulate/transfer-inventory", "execute_endpoint": "/execute/transfer-inventory"},
    {"action_type": "update_production_schedule", "simulate_endpoint": "/simulate/update-production-schedule", "execute_endpoint": "/execute/update-production-schedule"},
    {"action_type": "update_lane", "simulate_endpoint": None, "execute_endpoint": "/execute/update-lane"},
    {"action_type": "update_supplier_allocation", "simulate_endpoint": "/simulate/update-supplier-allocation", "execute_endpoint": "/execute/update-supplier-allocation"},
    {"action_type": "update_reorder_point", "simulate_endpoint": "/simulate/update-reorder-point", "execute_endpoint": "/execute/update-reorder-point"},
]


OUTPUT_CONTRACT = {
    "submit_to": "/api/agent/events",
    "required_fields": ["episode_id", "agent_id", "event_type", "title", "summary", "payload"],
    "workflow": [
        "RED_PLAN",
        "BLUE_ASSESSMENT",
        "BLUE_REVISED_PLAN",
        "EXECUTOR_ACTION",
        "EXECUTION_RESULT",
        "KPI_EVALUATION",
        "NARRATION",
    ],
    "notes": [
        "Blue is both critic and reviser.",
        "Executor-Narrator should normally execute BLUE_REVISED_PLAN.",
        "RED_PLAN is only a latest-final-action fallback if Blue has not revised yet.",
    ],
    "final_action_payload_example": {
        "action_type": "transfer_inventory",
        "execute_endpoint": "/execute/transfer-inventory",
        "request": {
            "product_id": "sku_standard",
            "from_node": "chicago_hub",
            "to_node": "west_coast_dc",
            "units": 500,
            "lane_id": "chicago_to_west_rail",
        },
        "reasoning": [
            "West Coast DC has rising stockout risk.",
            "Chicago Hub has enough inventory.",
            "Blue revised the plan to use rail because it balances service improvement with lower cost than air.",
        ],
        "expected_tradeoffs": {
            "improves": ["west_coast_service", "stockout_risk"],
            "worsens": ["transport_cost", "emissions", "chicago_inventory"],
            "neutral": [],
        },
    },
}


def _require_episode(episode_id: str):
    episode = get_episode(episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail=f"Agent episode {episode_id} was not found.")
    return episode


@router.post("/episodes")
def create_agent_episode(request: AgentEpisodeCreate):
    return create_episode(request)


@router.get("/episodes")
def get_agent_episodes():
    return list_episodes()


@router.get("/episodes/{episode_id}")
def get_agent_episode(episode_id: str):
    return _require_episode(episode_id)


@router.get("/episodes/{episode_id}/context")
def get_agent_context(episode_id: str):
    episode = _require_episode(episode_id)
    state = get_world_state()
    kpis = calculate_kpis(state)
    return {
        "episode": episode,
        "current_state": state,
        "current_kpis": kpis,
        "recent_alerts": state.get("alert_history", [])[-20:],
        "recent_event_history": state.get("event_history", [])[-20:],
        "action_history": state.get("action_history", [])[-20:],
        "prior_agent_events": get_events(episode_id),
        "user_preferences": episode.user_preferences,
        "available_action_endpoints": AVAILABLE_ACTION_ENDPOINTS,
        "output_contract": OUTPUT_CONTRACT,
    }


@router.post("/events", response_model=AgentEventAccepted)
def submit_agent_event(request: AgentEventCreate):
    _require_episode(request.episode_id)
    event, next_step = add_event(request)
    return AgentEventAccepted(event=event, next_step=next_step)


@router.get("/episodes/{episode_id}/timeline", response_model=EpisodeTimeline)
def get_agent_timeline(episode_id: str):
    episode = _require_episode(episode_id)
    return EpisodeTimeline(episode=episode, events=get_events(episode_id))


@router.get("/episodes/{episode_id}/latest-final-action")
def get_latest_final_action(episode_id: str):
    _require_episode(episode_id)
    event = latest_final_action_event(episode_id)
    if not event:
        raise HTTPException(
            status_code=404,
            detail="No FINAL_ACTION, BLUE_REVISED_PLAN, or fallback RED_PLAN event exists for this episode yet.",
        )
    return {
        "episode_id": episode_id,
        "event_id": event.id,
        "event_type": event.event_type,
        "payload": event.payload,
    }


@router.post("/episodes/{episode_id}/complete")
def complete_agent_episode(episode_id: str):
    _require_episode(episode_id)
    return complete_episode(episode_id)
