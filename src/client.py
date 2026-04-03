"""
CMPT 371 A3 - Competitive Trivia Quiz System (Client)
Architecture : TCP Socket Client with a colourful CLI interface
Protocol : Newline-delimited JSON messages over TCP

How it works
============
1. Connects to the server and sends a CONNECT handshake with the player's name.
2. Waits in the matchmaking queue until the server pairs it with an opponent.
3. For each round:
   a. Receives a QUESTION message and displays it with a live countdown timer.
   b. Sends an ANSWER message with the player's choice (A / B / C / D).
   c. Receives a ROUND_RESULT message and displays the outcome.
4. Displays the final scoreboard on GAME_OVER.
"""

import socket
import threading
import json
import sys
import time

HOST = "127.0.0.1"
PORT = 5050

# ANSI colour codes
RESET   = "\033[0m"
BOLD    = "\033[1m"
GREEN   = "\033[92m"
RED     = "\033[91m"
YELLOW  = "\033[93m"
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
WHITE   = "\033[97m"
DIM     = "\033[2m"


def send_msg(conn: socket.socket, payload: dict) -> None:
    """Serialise payload to JSON, append the \\n delimiter, and send."""
    raw = json.dumps(payload) + "\n"
    conn.sendall(raw.encode("utf-8"))


def recv_msg(conn: socket.socket, buffer: list) -> dict | None:
    """
    Read from the socket into a persistent buffer list.
    Returns the next complete JSON object (delimited by \\n) or None on error.
    """
    while "\n" not in buffer[0]:
        try:
            chunk = conn.recv(4096).decode("utf-8")
            if not chunk:
                return None
            buffer[0] += chunk
        except (OSError, ConnectionResetError):
            return None
    raw_msg, _, buffer[0] = buffer[0].partition("\n")
    try:
        return json.loads(raw_msg)
    except json.JSONDecodeError:
        return None


def print_banner() -> None:
    """Print the welcome ASCII-art banner."""
    print(f"""
{CYAN}{BOLD}
  ████████╗██████╗ ██╗██╗   ██╗██╗ █████╗      ██████╗ ██╗   ██╗██╗███████╗
     ██╔══╝██╔══██╗██║██║   ██║██║██╔══██╗    ██╔═══██╗██║   ██║██║╚══███╔╝
     ██║   ██████╔╝██║██║   ██║██║███████║    ██║   ██║██║   ██║██║  ███╔╝ 
     ██║   ██╔══██╗██║╚██╗ ██╔╝██║██╔══██║    ██║▄▄ ██║██║   ██║██║ ███╔╝  
     ██║   ██║  ██║██║ ╚████╔╝ ██║██║  ██║    ╚██████╔╝╚██████╔╝██║███████╗
     ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝  ╚═╝╚═╝  ╚═╝     ╚══▀▀═╝  ╚═════╝ ╚═╝╚══════╝
{RESET}
{YELLOW}            Competitive Trivia Quiz — CMPT 371 A3 Socket Programming{RESET}
""")


def print_divider(char: str = "─", width: int = 60) -> None:
    """Print a decorative horizontal divider."""
    print(f"{DIM}{char * width}{RESET}")


def display_question(msg: dict, my_role: str) -> None:
    """Pretty-print the question card with round info, scores, and options."""
    scores = msg["scores"]
    print_divider()
    print(f"{CYAN}{BOLD}  Round {msg['round']}/{msg['total_rounds']}  |  Category: {msg['category']}{RESET}")
    print(f"  Scores — {YELLOW}Player 1: {scores.get('Player 1', 0)}{RESET}  {MAGENTA}Player 2: {scores.get('Player 2', 0)}{RESET}")
    print_divider()
    print(f"\n{WHITE}{BOLD}  {msg['question']}{RESET}\n")
    for option in msg["options"]:
        letter = option.split(")")[0].strip()
        rest   = option[option.index(")") + 1:]
        print(f"    {CYAN}{BOLD}{letter}{RESET}{DIM}){RESET}{rest}")
    print(f"\n  {YELLOW}⏱  You have {int(msg['timeout'])} seconds to answer.{RESET}")
    print(f"  Enter your answer ({CYAN}A{RESET}/{CYAN}B{RESET}/{CYAN}C{RESET}/{CYAN}D{RESET}): ", end="", flush=True)


def display_round_result(msg: dict, my_role: str) -> None:
    """Display the outcome of the most recently completed round."""
    correct     = msg["correct_answer"]
    your_answer = msg["your_answer"]
    was_correct = msg["was_correct"]
    winner      = msg["round_winner"]
    scores      = msg["scores"]

    print()
    print_divider()
    if was_correct:
        print(f"  {GREEN}{BOLD}✓ Correct!{RESET}  The answer was {GREEN}{correct}{RESET}")
    elif your_answer is None:
        print(f"  {RED}{BOLD}⏰ Time's up!{RESET}  The correct answer was {GREEN}{correct}{RESET}")
    else:
        print(f"  {RED}{BOLD}✗ Wrong!{RESET}   You answered {RED}{your_answer}{RESET}. Correct was {GREEN}{correct}{RESET}")

    if winner:
        print(f"  {YELLOW}🏆 {winner} earned a point this round!{RESET}")
    else:
        print(f"  {DIM}  Nobody scored this round.{RESET}")

    print(f"\n  Scores — {YELLOW}Player 1: {scores.get('Player 1', 0)}{RESET}  {MAGENTA}Player 2: {scores.get('Player 2', 0)}{RESET}")
    print_divider()
    print()


def display_game_over(msg: dict, my_role: str) -> None:
    """Display the final scoreboard and winner."""
    scores = msg["scores"]
    winner = msg["winner"]
    s1     = scores.get("Player 1", 0)
    s2     = scores.get("Player 2", 0)

    print_divider("═")
    print(f"{CYAN}{BOLD}  🎉  GAME OVER  🎉{RESET}")
    print_divider("═")
    print(f"  {YELLOW}Player 1{RESET} : {s1} points")
    print(f"  {MAGENTA}Player 2{RESET} : {s2} points")
    print_divider()

    if winner == "Tie":
        print(f"  {CYAN}{BOLD}  It's a tie!{RESET}")
    elif winner == my_role:
        print(f"  {GREEN}{BOLD}  🏆  You WIN! Congratulations!{RESET}")
    else:
        print(f"  {RED}{BOLD}  😔  You LOST. Better luck next time!{RESET}")

    print_divider("═")


class CountdownTimer(threading.Thread):
    """
    Background thread that prints remaining time every second.
    Sets self.timed_out = True when it reaches 0.
    """
    def __init__(self, duration: float) -> None:
        super().__init__(daemon=True)
        self.duration   = duration
        self.timed_out  = False
        self._cancelled = threading.Event()

    def run(self) -> None:
        remaining = int(self.duration)
        while remaining > 0 and not self._cancelled.is_set():
            print(f"\r  {YELLOW}⏱  {remaining:2d}s remaining{RESET}  Enter answer: ", end="", flush=True)
            self._cancelled.wait(timeout=1)
            remaining -= 1
        if not self._cancelled.is_set():
            print(f"\r  {RED}⏰ Time's up!{RESET}                           ")
            self.timed_out = True

    def cancel(self) -> None:
        """Stop the timer early (player answered in time)."""
        self._cancelled.set()


def get_player_answer(timeout: float) -> str | None:
    """
    Prompt the player for A–D within `timeout` seconds.
    Returns the letter or None on timeout/disconnect.
    """
    timer = CountdownTimer(timeout)
    timer.start()
    answer = None
    try:
        raw = sys.stdin.readline().strip().upper()
        if raw in ("A", "B", "C", "D"):
            answer = raw
        elif raw:
            print(f"  {RED}Invalid choice '{raw}'. Must be A, B, C, or D.{RESET}")
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        timer.cancel()
        timer.join(timeout=0.5)

    return None if timer.timed_out else answer


def run_client() -> None:
    """
    Connects to the server, handles all protocol messages, and drives
    the CLI game loop.
    """
    print_banner()
    name = input(f"  {CYAN}Enter your name{RESET}: ").strip() or "Anonymous"
    print(f"\n  {DIM}Connecting to {HOST}:{PORT}...{RESET}")

    try:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((HOST, PORT))
    except ConnectionRefusedError:
        print(f"  {RED}ERROR: Could not connect to {HOST}:{PORT}.{RESET}")
        print(f"  {DIM}Make sure server.py is running first.{RESET}")
        sys.exit(1)

    buf     = [""]
    my_role = None
    send_msg(conn, {"type": "CONNECT", "name": name})

    try:
        while True:
            msg = recv_msg(conn, buf)
            if msg is None:
                print(f"\n  {DIM}Server disconnected. Goodbye!{RESET}")
                break

            msg_type = msg.get("type")

            if msg_type == "WAITING":
                print(f"  {YELLOW}⏳ {msg.get('payload', 'Waiting...')}{RESET}")

            elif msg_type == "WELCOME":
                my_role = msg.get("payload")
                colour  = YELLOW if my_role == "Player 1" else MAGENTA
                print(f"  {GREEN}✔ Match found!{RESET}  You are {colour}{BOLD}{my_role}{RESET}\n")

            elif msg_type == "QUESTION":
                display_question(msg, my_role)
                answer = get_player_answer(float(msg.get("timeout", 15.0)))
                send_msg(conn, {"type": "ANSWER", "answer": answer or ""})

            elif msg_type == "ROUND_RESULT":
                display_round_result(msg, my_role)
                time.sleep(1)

            elif msg_type == "GAME_OVER":
                display_game_over(msg, my_role)
                break

            else:
                print(f"  {DIM}[DEBUG] Unknown message: {msg}{RESET}")

    except KeyboardInterrupt:
        print(f"\n  {DIM}Disconnected by user.{RESET}")
    finally:
        conn.close()


if __name__ == "__main__":
    run_client()