"""
CMPT 371 A3 - Competitive Trivia Quiz System (Server)
Architecture : TCP Sockets with Multithreaded Game Session Management
Protocol : Newline-delimited JSON messages over TCP

How it works
============
1. Two clients connect and send a CONNECT handshake.
2. Once two players are queued, the server pops them and spawns a
   GameSession thread, keeping the main listener free for more pairs.
3. Inside the GameSession:
   - Each round the server sends the SAME question to both clients.
   - A per-round timer (ANSWER_TIMEOUT seconds) is enforced server-side.
   - The first client to submit a correct answer earns a point.
   - If both answer incorrectly within the timeout, nobody scores.
   - After all TOTAL_ROUNDS rounds the server sends a GAME_OVER message.
4. The server is the single source of truth for scores and correctness.
"""

import socket
import threading
import json
import random
import time

# Server configuration
HOST           = "127.0.0.1"   # Bind to localhost
PORT           = 5050           # Listening port
TOTAL_ROUNDS   = 10             # Number of questions per game
ANSWER_TIMEOUT = 15.0           # Seconds each player has to answer
CATEGORY_REVEAL_DELAY = 1.8     # Delay before showing each round question
ROUND_RESULT_DELAY = 2.2         # Delay before moving to next round

from questions import QUESTIONS

# Utility helpers
def send_msg(conn: socket.socket, payload: dict) -> None:
    """
    Serialise a Python dict to a JSON string, append a newline delimiter
    (our application-layer TCP boundary marker), and transmit it.
    """
    raw = json.dumps(payload) + "\n"
    conn.sendall(raw.encode("utf-8"))

def recv_msg(conn: socket.socket, buffer: list) -> dict | None:
    """
    Receive data from a socket using a persistent per-connection buffer list
    (buffer[0] holds the leftover bytes). Splits on the newline delimiter so
    that TCP stream-merging does not corrupt messages.

    Returns the next complete JSON message or None on disconnect/error.
    """
    while "\n" not in buffer[0]:
        try:
            chunk = conn.recv(4096).decode("utf-8")
            if not chunk:           # Client disconnected cleanly
                return None
            buffer[0] += chunk
        except (OSError, ConnectionResetError):
            return None             # Socket closed unexpectedly

    # Pop the first complete message from the buffer
    raw_msg, _, buffer[0] = buffer[0].partition("\n")
    try:
        return json.loads(raw_msg)
    except json.JSONDecodeError:
        return None                  # Malformed JSON — skip it

# Game session
def game_session(conn_1: socket.socket, conn_o: socket.socket) -> None:
    """
    Isolated game loop running on its own daemon thread.
    Manages one full competitive trivia match between two players.
    """
    player_names = {conn_1: "Player 1", conn_o: "Player 2"}
    scores       = {conn_1: 0,          conn_o: 0}

    # Persistent receive buffers (one list per connection so they survive
    # between recv_msg calls without being overwritten).
    buf_1 = [""]
    buf_o = [""]
    buffers = {conn_1: buf_1, conn_o: buf_o}

    # Welcome both players and tell them their role
    send_msg(conn_1, {"type": "WELCOME", "payload": "Player 1"})
    send_msg(conn_o, {"type": "WELCOME", "payload": "Player 2"})

    # Select TOTAL_ROUNDS unique questions from the bank (shuffled)
    selected_questions = random.sample(QUESTIONS, min(TOTAL_ROUNDS, len(QUESTIONS)))
    remaining_questions = [q for q in QUESTIONS if q not in selected_questions]

    print(f"[SESSION] Game started with 2 players. {TOTAL_ROUNDS} rounds.")

    def play_round(q: dict, round_num: int, total_rounds: int, is_tiebreaker: bool = False) -> None:
        round_label = f"TB-{round_num - TOTAL_ROUNDS}" if is_tiebreaker else str(round_num)

        reveal_msg = {
            "type": "CATEGORY_REVEAL",
            "category": q["category"],
            "round": round_num,
            "round_label": round_label,
            "total_rounds": total_rounds,
            "is_tiebreaker": is_tiebreaker,
            "scores": {
                "Player 1": scores[conn_1],
                "Player 2": scores[conn_o],
            },
        }
        send_msg(conn_1, reveal_msg)
        send_msg(conn_o, reveal_msg)
        time.sleep(CATEGORY_REVEAL_DELAY)

        print(f"[SESSION] Round {round_label}: {q['question'][:50]}...")

        question_msg = {
            "type"        : "QUESTION",
            "round"       : round_num,
            "round_label" : round_label,
            "total_rounds": total_rounds,
            "category"    : q["category"],
            "question"    : q["question"],
            "options"     : q["options"],
            "timeout"     : ANSWER_TIMEOUT,
            "is_tiebreaker": is_tiebreaker,
            "scores"      : {
                "Player 1": scores[conn_1],
                "Player 2": scores[conn_o]
            }
        }
        send_msg(conn_1, question_msg)
        send_msg(conn_o, question_msg)

        # ── Collect answers concurrently using threads ─────────────────────────
        answers     = {}   # { conn : (answer_str, elapsed_seconds) }
        round_start = time.monotonic()
        lock        = threading.Lock()
        first_submit_conn = None

        def collect_answer(conn: socket.socket) -> None:
            """
            Worker that waits for a single ANSWER message from one client.
            If the client takes longer than ANSWER_TIMEOUT the answer is
            recorded as None (timeout).
            """
            conn.settimeout(ANSWER_TIMEOUT)
            try:
                msg = recv_msg(conn, buffers[conn])
                elapsed = time.monotonic() - round_start
                answer_val = msg.get("answer", "").upper() if msg else None
            except (socket.timeout, OSError):
                answer_val = None
                elapsed    = ANSWER_TIMEOUT
            finally:
                conn.settimeout(None)   # Reset to blocking mode

            nonlocal first_submit_conn
            with lock:
                if answer_val and first_submit_conn is None:
                    first_submit_conn = conn
                    other_conn = conn_o if conn is conn_1 else conn_1
                    send_msg(other_conn, {
                        "type": "OPPONENT_LOCKED",
                        "payload": "Opponent locked in.",
                    })
                answers[conn] = (answer_val, elapsed)

        t1 = threading.Thread(target=collect_answer, args=(conn_1,), daemon=True)
        t2 = threading.Thread(target=collect_answer, args=(conn_o,), daemon=True)
        t1.start()
        t2.start()
        # Wait for both threads (plus a small buffer) before resolving
        t1.join(timeout=ANSWER_TIMEOUT + 1)
        t2.join(timeout=ANSWER_TIMEOUT + 1)

        # Score resolution
        correct_key       = q["answer"].upper()
        round_winner_name = None

        # Find which correct answers arrived and pick the fastest
        correct_submissions = [
            (conn, elapsed)
            for conn, (ans, elapsed) in answers.items()
            if ans == correct_key
        ]

        if correct_submissions:
            fastest_conn, _ = min(correct_submissions, key=lambda x: x[1])
            scores[fastest_conn] += 1
            round_winner_name = player_names[fastest_conn]

        # Build per-player RESULT messages
        for conn in (conn_1, conn_o):
            their_answer, _ = answers.get(conn, (None, ANSWER_TIMEOUT))
            was_correct = their_answer == correct_key

            result_msg = {
                "type"          : "ROUND_RESULT",
                "round"         : round_num,
                "round_label"   : round_label,
                "correct_answer": correct_key,
                "your_answer"   : their_answer,
                "was_correct"   : was_correct,
                "round_winner"  : round_winner_name,
                "explanation"   : q.get("explanation", ""),
                "is_tiebreaker" : is_tiebreaker,
                "scores"        : {
                    "Player 1": scores[conn_1],
                    "Player 2": scores[conn_o]
                }
            }
            send_msg(conn, result_msg)

        print(f"[SESSION] Round {round_label} done. Scores — P1:{scores[conn_1]} P2:{scores[conn_o]}")
        time.sleep(ROUND_RESULT_DELAY)   # Let players read round outcome

    # Main rounds
    for round_num, q in enumerate(selected_questions, start=1):
        play_round(q=q, round_num=round_num, total_rounds=TOTAL_ROUNDS, is_tiebreaker=False)

    # Sudden-death tiebreakers continue until tie is broken
    tiebreak_count = 0
    while scores[conn_1] == scores[conn_o]:
        tiebreak_count += 1
        if remaining_questions:
            q = random.choice(remaining_questions)
            remaining_questions.remove(q)
        else:
            q = random.choice(QUESTIONS)

        round_num = TOTAL_ROUNDS + tiebreak_count
        print(f"[SESSION] Tie detected. Starting sudden-death round {tiebreak_count}.")
        play_round(q=q, round_num=round_num, total_rounds=round_num, is_tiebreaker=True)

    # Game-over
    s1, s2 = scores[conn_1], scores[conn_o]
    if   s1 > s2: overall_winner = "Player 1"
    elif s2 > s1: overall_winner = "Player 2"
    else:         overall_winner = "Tie"

    game_over_msg = {
        "type"  : "GAME_OVER",
        "scores": {"Player 1": s1, "Player 2": s2},
        "winner": overall_winner
    }
    send_msg(conn_1, game_over_msg)
    send_msg(conn_o, game_over_msg)

    print(f"[SESSION] Game over. Winner: {overall_winner}. Closing connections.")
    conn_1.close()
    conn_o.close()


# Main server event loop

def start_server() -> None:
    """
    Binds to HOST:PORT, listens for incoming TCP connections, performs the
    CONNECT handshake, and manages a matchmaking queue. When two players are
    queued a new GameSession daemon thread is spawned for them.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[STARTING] Trivia Quiz Server listening on {HOST}:{PORT}")

    matchmaking_queue = []

    try:
        while True:
            conn, addr = server.accept()
            print(f"[CONNECT] New connection from {addr}")

            buf = [""]
            msg = recv_msg(conn, buf)

            if msg and msg.get("type") == "CONNECT":
                player_name_hint = msg.get("name", "Anonymous")
                print(f"[HANDSHAKE] '{player_name_hint}' joined the queue. Queue size: {len(matchmaking_queue)+1}")
                matchmaking_queue.append(conn)
                send_msg(conn, {"type": "WAITING", "payload": "Waiting for an opponent..."})

                if len(matchmaking_queue) >= 2:
                    player_1 = matchmaking_queue.pop(0)
                    player_2 = matchmaking_queue.pop(0)
                    print("[MATCH] Two players matched. Spawning GameSession thread.")
                    session_thread = threading.Thread(
                        target=game_session,
                        args=(player_1, player_2),
                        daemon=True
                    )
                    session_thread.start()
            else:
                print(f"[REJECT] Bad handshake from {addr}. Closing.")
                conn.close()

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Server shutting down gracefully (Ctrl+C).")
    finally:
        server.close()


if __name__ == "__main__":
    start_server()