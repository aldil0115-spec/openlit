"""
AI 마피아 게임 엔트리포인트
  - Ollama 로컬 모델 사용 (인터넷 불필요)
      Agent A : Marcus  (마피아)   → mistral:latest
      Agent B : Diana   (탐정)    → deepseek-r1:7b
      Agent C : Alice   (시민)    → deepseek-r1:7b
      Agent D : Bob     (시민)    → deepseek-r1:7b
      Agent E : Charlie (시민)    → mistral:latest
  - OpenLit 으로 토큰 자동 모니터링 → http://localhost:3000
  - 시작 메시지는 OpenLit PromptHub ("prompthubtest") 에서 로드
"""
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich import box

load_dotenv()

# ── OpenLit 초기화 ────────────────────────────────────────────
import openlit
openlit.init(
    otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"),
    application_name="mafia-game",
    environment="dev",
    collect_gpu_stats=True        # GPU 메트릭 수집
)

from game.graph import build_graph

console = Console()

ROLE_COLORS = {
    "system":   "bright_black",
    "mafia":    "red",
    "detective":"cyan",
    "citizen":  "green",
}

ROLE_ICONS = {
    "system":   "⚙",
    "mafia":    "🔪",
    "detective":"🔍",
    "citizen":  "👤",
}


def fetch_start_message() -> str:
    """OpenLit PromptHub 에서 시작 메시지를 가져옴.
    실패 시 기본 메시지로 폴백."""
    try:
        result = openlit.get_prompt(
            url=os.getenv("OPENLIT_URL", "http://localhost:3000"),
            api_key=os.getenv("OPENLIT_API_KEY", ""),
            name="prompthubtest",
        )
        if result and result.get("res") and result["res"].get("prompt"):
            return result["res"]["prompt"]
        console.print("[yellow]⚠ PromptHub 응답이 비어있습니다. 기본 메시지를 사용합니다.[/yellow]")
    except Exception as e:
        console.print(f"[yellow]⚠ PromptHub 연결 실패: {e}\n  기본 메시지를 사용합니다.[/yellow]")

    # 폴백 기본 메시지
    return (
        "🎭 AI 마피아 게임\n"
        "Marcus (마피아) vs Diana (탐정) + 시민 3명\n"
        "토큰 모니터링 → http://localhost:3000"
    )


def print_message(msg: dict) -> None:
    role    = msg.get("role", "system")
    player  = msg.get("player", "?")
    content = msg.get("content", "")
    color   = ROLE_COLORS.get(role, "white")
    icon    = ROLE_ICONS.get(role, "•")

    label = f"[{color}]{icon} {player}[/{color}]"
    if role == "system":
        console.print(Panel(content, style="bright_black", box=box.SIMPLE))
    else:
        console.print(f"  {label}  {content}")


def run() -> None:
    # ── PromptHub 에서 시작 메시지 로드 ──────────────────────────
    start_msg = fetch_start_message()
    console.print(Panel.fit(start_msg, box=box.DOUBLE, style="bold red"))

    graph = build_graph()
    printed_count = 0

    for step in graph.stream({}, stream_mode="values"):
        new_messages = step.get("messages", [])[printed_count:]
        for msg in new_messages:
            print_message(msg)
        printed_count += len(new_messages)

    # ── 게임 종료 요약 ──────────────────────────────────────────
    console.rule("[bold]게임 종료[/bold]")
    winner    = step.get("winner", "unknown")
    eliminated = step.get("eliminated", [])

    if winner == "citizens":
        console.print("[bold cyan]🏆 시민 팀 승리![/bold cyan]")
    elif winner == "mafia":
        console.print("[bold red]💀 마피아 승리![/bold red]")

    console.print(f"탈락 순서: {' → '.join(eliminated)}")
    console.print("\n[dim]토큰 사용량 상세: http://localhost:3000 (OpenLit)[/dim]")
    console.print("[dim]메트릭 대시보드:  http://localhost:3001 (Grafana)[/dim]")
    console.print("[dim]로그 탐색:        http://localhost:5601 (Kibana)[/dim]")


if __name__ == "__main__":
    run()
