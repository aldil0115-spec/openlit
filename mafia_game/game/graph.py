"""
LangGraph 그래프

낮 발언 순서 (토론 누적):
  day_intro → marcus_speak → diana_speak → alice_speak → bob_speak → charlie_speak

투표 순서 (순차 누적):
  marcus_vote → diana_vote → alice_vote → bob_vote → charlie_vote → tally_votes

야간:
  marcus_night → apply_night_kill

승리 판정: check_after_vote / check_after_night
"""
from langgraph.graph import StateGraph, END

from game.state import GameState
from game.agents import (
    mafia_agent,       detective_agent,
    alice_agent,       bob_agent,        charlie_agent,
    mafia_vote_agent,  detective_vote_agent,
    alice_vote_agent,  bob_vote_agent,   charlie_vote_agent,
    mafia_night_agent,
)
from game.nodes import (
    setup_node,
    day_intro_node,
    tally_votes_node,
    apply_night_kill_node,
    check_winner_node,
)


def _is_over(state: GameState) -> str:
    if state.get("winner") or state["round"] > 6:
        return "end"
    return "continue"


def _skip_if_dead(name: str, next_node: str, fallback: str):
    """해당 플레이어가 탈락했으면 발언/투표 건너뜀"""
    def router(state: GameState) -> str:
        alive_names = [p["name"] for p in state["players"] if p["alive"]]
        return next_node if name in alive_names else fallback
    return router


def build_graph():
    g = StateGraph(GameState)

    # ── 노드 등록 ──────────────────────────────────────────────
    g.add_node("setup",             setup_node)
    g.add_node("day_intro",         day_intro_node)

    # 낮 발언
    g.add_node("marcus_speak",      mafia_agent)
    g.add_node("diana_speak",       detective_agent)
    g.add_node("alice_speak",       alice_agent)
    g.add_node("bob_speak",         bob_agent)
    g.add_node("charlie_speak",     charlie_agent)

    # 투표
    g.add_node("marcus_vote",       mafia_vote_agent)
    g.add_node("diana_vote",        detective_vote_agent)
    g.add_node("alice_vote",        alice_vote_agent)
    g.add_node("bob_vote",          bob_vote_agent)
    g.add_node("charlie_vote",      charlie_vote_agent)

    g.add_node("tally_votes",       tally_votes_node)
    g.add_node("check_after_vote",  check_winner_node)

    # 야간
    g.add_node("marcus_night",      mafia_night_agent)
    g.add_node("apply_night_kill",  apply_night_kill_node)
    g.add_node("check_after_night", check_winner_node)

    # ── 엣지: 초기화 ──────────────────────────────────────────
    g.set_entry_point("setup")
    g.add_edge("setup", "day_intro")

    # ── 엣지: 낮 발언 (생존자만 발언, 탈락자 스킵) ───────────
    g.add_conditional_edges("day_intro",    _skip_if_dead("Marcus",  "marcus_speak",  "diana_speak"),   {"marcus_speak": "marcus_speak",   "diana_speak": "diana_speak"})
    g.add_conditional_edges("marcus_speak", _skip_if_dead("Diana",   "diana_speak",   "alice_speak"),   {"diana_speak":  "diana_speak",    "alice_speak":  "alice_speak"})
    g.add_conditional_edges("diana_speak",  _skip_if_dead("Alice",   "alice_speak",   "bob_speak"),     {"alice_speak":  "alice_speak",    "bob_speak":    "bob_speak"})
    g.add_conditional_edges("alice_speak",  _skip_if_dead("Bob",     "bob_speak",     "charlie_speak"), {"bob_speak":    "bob_speak",      "charlie_speak":"charlie_speak"})
    g.add_conditional_edges("bob_speak",    _skip_if_dead("Charlie", "charlie_speak", "marcus_vote"),   {"charlie_speak":"charlie_speak",  "marcus_vote":  "marcus_vote"})
    g.add_edge("charlie_speak", "marcus_vote")

    # ── 엣지: 투표 (순차 누적) ────────────────────────────────
    g.add_conditional_edges("marcus_vote",  _skip_if_dead("Diana",   "diana_vote",   "alice_vote"),    {"diana_vote":   "diana_vote",     "alice_vote":   "alice_vote"})
    g.add_conditional_edges("diana_vote",   _skip_if_dead("Alice",   "alice_vote",   "bob_vote"),      {"alice_vote":   "alice_vote",     "bob_vote":     "bob_vote"})
    g.add_conditional_edges("alice_vote",   _skip_if_dead("Bob",     "bob_vote",     "charlie_vote"),  {"bob_vote":     "bob_vote",       "charlie_vote": "charlie_vote"})
    g.add_conditional_edges("bob_vote",     _skip_if_dead("Charlie", "charlie_vote", "tally_votes"),   {"charlie_vote": "charlie_vote",   "tally_votes":  "tally_votes"})
    g.add_edge("charlie_vote", "tally_votes")

    # ── 엣지: 낮 판정 ─────────────────────────────────────────
    g.add_edge("tally_votes", "check_after_vote")
    g.add_conditional_edges("check_after_vote", _is_over,
                            {"end": END, "continue": "marcus_night"})

    # ── 엣지: 야간 ────────────────────────────────────────────
    g.add_edge("marcus_night",      "apply_night_kill")
    g.add_edge("apply_night_kill",  "check_after_night")
    g.add_conditional_edges("check_after_night", _is_over,
                            {"end": END, "continue": "day_intro"})

    return g.compile()
