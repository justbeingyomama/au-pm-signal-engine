"""
dashboard.py — Rich CLI dashboard showing engine status.

Usage:
    python dashboard.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

load_dotenv()

console = Console()


def run_dashboard():
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_JSON", "credentials.json")
    spreadsheet_id = os.getenv("SPREADSHEET_ID", "")

    if not spreadsheet_id or not os.path.isfile(credentials_path):
        console.print("[bold red]ERROR:[/] Missing credentials or SPREADSHEET_ID. Check your .env file.")
        sys.exit(1)

    from sheets.client import SheetsClient
    sheets = SheetsClient(credentials_path, spreadsheet_id)

    console.rule("[bold cyan]AU PM Hiring Signal Engine — Dashboard[/]")
    console.print()

    # ── Collector State ────────────────────────────────────────────────────────
    try:
        states = sheets.get_all_collector_states()
        state_table = Table(
            title="Collector Status",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )
        state_table.add_column("Source", style="cyan", no_wrap=True)
        state_table.add_column("Key", max_width=40)
        state_table.add_column("Last Run", style="yellow")
        state_table.add_column("Last Success", style="green")
        state_table.add_column("Last Error", style="red", max_width=40)

        for s in states:
            state_table.add_row(
                s.get("source", ""),
                s.get("key", "")[:40],
                s.get("last_run_time", "")[:19],
                s.get("last_success_time", "")[:19],
                (s.get("last_error", "") or "—")[:40],
            )

        if not states:
            console.print("[dim]No collector state data yet. Run main.py first.[/]")
        else:
            console.print(state_table)
    except Exception as e:
        console.print(f"[red]Could not load collector state: {e}[/]")

    console.print()

    # ── Signals Today ──────────────────────────────────────────────────────────
    try:
        today_signals = sheets.get_signals_today()
        all_signals = sheets.get_all_signal_rows()

        now = datetime.now(timezone.utc)
        high_priority_24h = []
        for row in all_signals:
            if len(row) > 11 and row[11] == "TRUE":
                disc = row[9] if len(row) > 9 else ""
                try:
                    dt = datetime.fromisoformat(disc.replace("Z", "+00:00"))
                    if (now - dt).total_seconds() < 86400:
                        high_priority_24h.append(row)
                except Exception:
                    pass

        summary_table = Table(box=box.SIMPLE, show_header=False)
        summary_table.add_column("Metric", style="bold")
        summary_table.add_column("Value", style="cyan")
        summary_table.add_row("Total signals in sheet", str(len(all_signals)))
        summary_table.add_row("New signals today (UTC)", str(len(today_signals)))
        summary_table.add_row("High-priority in last 24h", str(len(high_priority_24h)))

        console.print(Panel(summary_table, title="Signal Summary", border_style="green"))

        # High-priority signals table
        if high_priority_24h:
            console.print()
            hp_table = Table(
                title=f"🔥 High-Priority Signals (last 24h) — {len(high_priority_24h)} found",
                box=box.ROUNDED,
                header_style="bold yellow",
            )
            hp_table.add_column("#", style="dim", width=3)
            hp_table.add_column("Company", style="cyan")
            hp_table.add_column("Role Title", max_width=40)
            hp_table.add_column("Location")
            hp_table.add_column("Remote?")
            hp_table.add_column("Score", style="bold green")
            hp_table.add_column("Source")
            hp_table.add_column("Status")

            for i, row in enumerate(high_priority_24h[:20], 1):
                # Columns: signal_id, dedupe_hash, source, signal_type, company,
                #          role_title, location, url, posted_time, discovered_time,
                #          score, is_high_priority, remote_likelihood, raw_text, notes, status

                remote_val = row[12] if len(row) > 12 else ""
                if remote_val == "High":
                    remote_fmt = "🟢 High"
                elif remote_val == "Med":
                    remote_fmt = "🟡 Med"
                elif remote_val == "Low":
                    remote_fmt = "⚪ Low"
                else:
                    remote_fmt = "—"
                    
                hp_table.add_row(
                    str(i),
                    row[4] if len(row) > 4 else "",
                    row[5] if len(row) > 5 else "",
                    row[6] if len(row) > 6 else "",
                    remote_fmt,
                    row[10] if len(row) > 10 else "",
                    row[2] if len(row) > 2 else "",
                    row[15] if len(row) > 15 else (row[14] if len(row) > 14 else ""),
                )
            console.print(hp_table)
        else:
            console.print("[dim]No high-priority signals in the last 24 hours.[/]")

    except Exception as e:
        console.print(f"[red]Could not load signal data: {e}[/]")

    console.print()
    console.print(
        f"[dim]Sheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit[/]"
    )


if __name__ == "__main__":
    run_dashboard()
