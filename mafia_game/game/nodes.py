"""
게임 로직 노드 (LLM 미사용)
"""
import random
from collections import Counter

from game.state import GameState


def setup_node(state: GameState) -> dict:
    players = [
        {"name": "Marcus",  "role": "mafia",     "alive": True},
        {"name": "Diana",   "role": "detective",  "alive": True},
        {"name": "Alice",   "role": "citizen",    "alive": True},
        {"name": "Bob",     "role": "citizen",    "alive": True},
        {"name": "Charlie", "role": "citizen",    "alive": True},
    ]
    return {
        "round":        1,
        "phase":        "day",
        "players":      players,
        "messages":     [{
            "player": "🎮 System", "role": "system", "round": 0,
            "content": (
                "게임 시작! 총 5명 (마피아 1, 탐정 1, 시민 3)\n"
                "Agent A: Marcus (mistral)  |  Agent B~E: Diana·Alice·Bob·Charlie (deepseek-r1)\n"
                "마피아를 찾아 마을을 구하세요!"
            ),
        }],
        "votes":        {},
        "eliminated":   [],
        "winner":       None,
        "last_killed":  None,
        "_night_target": None,
    }


def day_intro_node(state: GameState) -> dict:
    alive = [p for p in state["players"] if p["alive"]]
    names = ", ".join(p["name"] for p in alive)

    killed_msg = (
        f"간밤에 [{state['last_killed']}]이(가) 마피아에게 희생되었습니다. "
        if state.get("last_killed") else ""
    )

    return {
        "phase": "day",
        "votes": {},          # 라운드 시작 시 투표 초기화
        "_night_target": None,
        "messages": [{
            "player": "🎮 System", "role": "system", "round": state["round"],
            "content": f"{killed_msg}[Round {state['round']}] 낮이 밝았습니다. 생존자: {names}",
        }],
    }


def tally_votes_node(state: GameState) -> dict:
    """현재 생존자 중 투표하지 않은 플레이어는 랜덤 처리 후 집계"""
    votes = dict(state.get("votes", {}))
    alive = [p for p in state["players"] if p["alive"]]

    # 미투표 시 랜덤 처리 (예외 방지)
    for p in alive:
        if p["name"] not in votes:
            others = [x["name"] for x in alive if x["name"] != p["name"]]
            if others:
                votes[p["name"]] = random.choice(others)

    counts = Counter(votes.values())
    top_cnt = counts.most_common(1)[0][1]
    tied    = [name for name, cnt in counts.items() if cnt == top_cnt]
    out     = random.choice(tied)

    new_players = [
        {**p, "alive": False} if p["name"] == out else p
        for p in state["players"]
    ]
    out_role = next(p["role"] for p in state["players"] if p["name"] == out)
    summary  = " | ".join(f"{k}→{v}" for k, v in sorted(votes.items()))

    return {
        "players":   new_players,
        "votes":     votes,
        "eliminated": state["eliminated"] + [out],
        "phase":     "night",
        "messages":  [{
            "player": "🎮 System", "role": "system", "round": state["round"],
            "content": (
                f"투표 결과: {summary}\n"
                f"→ [{out}] 탈락! (정체: {out_role})"
            ),
        }],
    }


def apply_night_kill_node(state: GameState) -> dict:
    target = state.get("_night_target")
    if not target:
        return {"phase": "day", "round": state["round"] + 1, "last_killed": None}

    new_players = [
        {**p, "alive": False} if p["name"] == target else p
        for p in state["players"]
    ]
    return {
        "players":    new_players,
        "eliminated": state["eliminated"] + [target],
        "last_killed": target,
        "_night_target": None,
        "phase":      "day",
        "round":      state["round"] + 1,
        "messages":   [{
            "player": "🌙 System", "role": "system", "round": state["round"],
            "content": f"밤이 지났습니다... [{target}]이(가) 마피아에게 제거되었습니다.",
        }],
    }


def check_winner_node(state: GameState) -> dict:
    alive         = [p for p in state["players"] if p["alive"]]
    mafia_alive   = [p for p in alive if p["role"] == "mafia"]
    others_alive  = [p for p in alive if p["role"] != "mafia"]

    if not mafia_alive:
        return {
            "winner": "citizens", "phase": "end",
            "messages": [{"player": "🎮 System", "role": "system", "round": state["round"],
                          "content": "🏆 시민 승리! 마피아가 제거되었습니다!"}],
        }
    if len(mafia_alive) >= len(others_alive):
        return {
            "winner": "mafia", "phase": "end",
            "messages": [{"player": "🎮 System", "role": "system", "round": state["round"],
                          "content": "💀 마피아 승리! 마을이 점령되었습니다!"}],
        }
    return {}
