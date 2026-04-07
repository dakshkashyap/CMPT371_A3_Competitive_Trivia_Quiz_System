# """
# CMPT 371 A3 - Competitive Trivia Quiz System (Server)
# Architecture : TCP Sockets with Multithreaded Game Session Management
# Protocol : Newline-delimited JSON messages over TCP

# How it works
# ============
# 1. Two clients connect and send a CONNECT handshake.
# 2. Once two players are queued, the server pops them and spawns a
#    GameSession thread, keeping the main listener free for more pairs.
# 3. Inside the GameSession:
#    - Each round the server sends the SAME question to both clients.
#    - A per-round timer (ANSWER_TIMEOUT seconds) is enforced server-side.
#    - The first client to submit a correct answer earns a point.
#    - If both answer incorrectly within the timeout, nobody scores.
#    - After all TOTAL_ROUNDS rounds the server sends a GAME_OVER message.
# 4. The server is the single source of truth for scores and correctness.
# """

# import socket
# import threading
# import json
# import random
# import time

# # Server configuration (Hardware/Network Constants)
# HOST           = "127.0.0.1"    # Bind to localhost (loopback interface)
# PORT           = 5050           # Listening port
# TOTAL_ROUNDS   = 10             # Number of questions per game
# ANSWER_TIMEOUT = 15.0           # Seconds each player has to answer
# CATEGORY_REVEAL_DELAY = 1.8     # Delay before showing each round question
# ROUND_RESULT_DELAY = 3.2        # Delay before moving to next round

# from questions import QUESTIONS

# # Utility helpers
# class PlayerDisconnectedError(Exception):
#     """Custom error raised when a player suddenly drops their connection mid-game."""

# def send_msg(conn: socket.socket, payload: dict) -> bool:
#     """
#     Serialise a Python dict to a JSON string, append a newline delimiter
#     (our application-layer TCP boundary marker), and transmit it.
#     Returns True on success, False if the socket is broken.
#     """
#     raw = json.dumps(payload) + "\n"
#     try:
#         conn.sendall(raw.encode("utf-8"))
#         return True
#     except OSError:
#         return False

# # -- AI Assisted Logic --
# # This function uses a list buffer parameter to work around TCP stream chunking
# # ChatGPT helped design this robust newline-delimited message parser.
# def recv_msg(conn: socket.socket, buffer: list) -> dict | None:
#     """
#     Receive data from a socket using a persistent per-connection buffer list
#     (buffer[0] holds the leftover bytes). Splits on the newline delimiter so
#     that TCP stream-merging does not corrupt messages.

#     Returns the next complete JSON message or None on disconnect/error.
#     """
#     while "\n" not in buffer[0]:
#         try:
#             chunk = conn.recv(4096).decode("utf-8")
#             if not chunk:           # Client disconnected cleanly
#                 return None
#             buffer[0] += chunk
#         except (OSError, ConnectionResetError):
#             return None             # Socket closed unexpectedly

#     # Pop the first complete message from the buffer
#     raw_msg, _, buffer[0] = buffer[0].partition("\n")
#     try:
#         return json.loads(raw_msg)
#     except json.JSONDecodeError:
#         return None                  # Malformed JSON — skip it

# # Game session
# def game_session(
#     conn_1: socket.socket,
#     conn_o: socket.socket,
#     name_1: str,
#     name_2: str,
# ) -> None:
#     """
#     Isolated game loop running on its own daemon thread.
#     Manages one full competitive trivia match between two players.
#     """
#     player_roles = {conn_1: "Player 1", conn_o: "Player 2"}
#     display_names = {"Player 1": name_1, "Player 2": name_2}
#     scores       = {conn_1: 0,          conn_o: 0}

#     # Persistent receive buffers (one list per connection so they survive
#     # between recv_msg calls without being overwritten).
#     buf_1 = [""]
#     buf_o = [""]
#     buffers = {conn_1: buf_1, conn_o: buf_o}

#     def _notify_left_and_raise(survivor: socket.socket, leaver_role: str) -> None:
#         """Tell the surviving player their opponent left, then abort the session."""
#         send_msg(survivor, {
#             "type": "PLAYER_LEFT",
#             "payload": f"{display_names[leaver_role]} disconnected.",
#         })
#         raise PlayerDisconnectedError()

#     def _send_both(msg: dict) -> None:
#         """Send msg to both players; notify the survivor if one is gone."""
#         ok_1 = send_msg(conn_1, msg)
#         ok_o = send_msg(conn_o, msg)
#         if not ok_1:
#             _notify_left_and_raise(conn_o, "Player 1")
#         if not ok_o:
#             _notify_left_and_raise(conn_1, "Player 2")

#     # Welcome both players and tell them their role
#     send_msg(conn_1, {
#         "type": "WELCOME",
#         "payload": {
#             "role": "Player 1",
#             "player_names": display_names,
#         },
#     })
#     send_msg(conn_o, {
#         "type": "WELCOME",
#         "payload": {
#             "role": "Player 2",
#             "player_names": display_names,
#         },
#     })

#     # Select TOTAL_ROUNDS unique questions from the bank (shuffled)
#     selected_questions = random.sample(QUESTIONS, min(TOTAL_ROUNDS, len(QUESTIONS)))
#     remaining_questions = [q for q in QUESTIONS if q not in selected_questions]

#     print(f"[SESSION] Game started with 2 players. {TOTAL_ROUNDS} rounds.")

#     def play_round(q: dict, round_num: int, total_rounds: int, is_tiebreaker: bool = False) -> None:
#         round_label = f"TB-{round_num - TOTAL_ROUNDS}" if is_tiebreaker else str(round_num)

#         reveal_msg = {
#             "type": "CATEGORY_REVEAL",
#             "category": q["category"],
#             "round": round_num,
#             "round_label": round_label,
#             "total_rounds": total_rounds,
#             "is_tiebreaker": is_tiebreaker,
#             "player_names": display_names,
#             "scores": {
#                 "Player 1": scores[conn_1],
#                 "Player 2": scores[conn_o],
#             },
#         }
#         _send_both(reveal_msg)
#         time.sleep(CATEGORY_REVEAL_DELAY)

#         print(f"[SESSION] Round {round_label}: {q['question'][:50]}...")

#         question_msg = {
#             "type"        : "QUESTION",
#             "round"       : round_num,
#             "round_label" : round_label,
#             "total_rounds": total_rounds,
#             "category"    : q["category"],
#             "question"    : q["question"],
#             "options"     : q["options"],
#             "timeout"     : ANSWER_TIMEOUT,
#             "is_tiebreaker": is_tiebreaker,
#             "player_names" : display_names,
#             "scores"      : {
#                 "Player 1": scores[conn_1],
#                 "Player 2": scores[conn_o]
#             }
#         }
#         _send_both(question_msg)

#         # ── Collect answers concurrently using threads ─────────────────────────
#         answers            = {}   # { conn : (answer_str, elapsed_seconds) }
#         round_start        = time.monotonic()
#         lock               = threading.Lock()
#         first_submit_conn  = None
#         disconnected_conns = set()

#         def collect_answer(conn: socket.socket) -> None:
#             """
#             Worker that waits for a single ANSWER message from one client.
#             If the client takes longer than ANSWER_TIMEOUT the answer is
#             recorded as None (timeout). An abrupt disconnect is also None
#             but the conn is added to disconnected_conns for detection.
#             """
#             answer_val = None
#             elapsed    = ANSWER_TIMEOUT
#             conn.settimeout(ANSWER_TIMEOUT)
#             try:
#                 msg = recv_msg(conn, buffers[conn])
#                 elapsed = time.monotonic() - round_start
#                 if msg is None:
#                     # recv_msg returns None on clean/abrupt disconnect
#                     with lock:
#                         disconnected_conns.add(conn)
#                 else:
#                     answer_val = msg.get("answer", "").upper() or None
#             except (socket.timeout, OSError):
#                 pass   # timeout — answer_val stays None
#             finally:
#                 conn.settimeout(None)   # Reset to blocking mode

#             nonlocal first_submit_conn
#             with lock:
#                 if answer_val and first_submit_conn is None:
#                     first_submit_conn = conn
#                     other_conn = conn_o if conn is conn_1 else conn_1
#                     send_msg(other_conn, {
#                         "type": "OPPONENT_LOCKED",
#                         "payload": "Opponent locked in.",
#                     })
#                 answers[conn] = (answer_val, elapsed)

#         t1 = threading.Thread(target=collect_answer, args=(conn_1,), daemon=True)
#         t2 = threading.Thread(target=collect_answer, args=(conn_o,), daemon=True)
#         t1.start()
#         t2.start()
#         # Wait for both threads (plus a small buffer) before resolving
#         t1.join(timeout=ANSWER_TIMEOUT + 1)
#         t2.join(timeout=ANSWER_TIMEOUT + 1)

#         if disconnected_conns:
#             if conn_1 in disconnected_conns:
#                 _notify_left_and_raise(conn_o, "Player 1")
#             else:
#                 _notify_left_and_raise(conn_1, "Player 2")

#         # Score resolution
#         correct_key       = q["answer"].upper()
#         round_winner_name = None

#         # Find which correct answers arrived and pick the fastest
#         correct_submissions = [
#             (conn, elapsed)
#             for conn, (ans, elapsed) in answers.items()
#             if ans == correct_key
#         ]

#         if correct_submissions:
#             fastest_conn, _ = min(correct_submissions, key=lambda x: x[1])
#             scores[fastest_conn] += 1
#             round_winner_name = player_roles[fastest_conn]

#         # Build per-player RESULT messages
#         for conn in (conn_1, conn_o):
#             their_answer, _ = answers.get(conn, (None, ANSWER_TIMEOUT))
#             was_correct = their_answer == correct_key
#             other_conn  = conn_o if conn is conn_1 else conn_1
#             other_role  = "Player 2" if conn is conn_1 else "Player 1"

#             result_msg = {
#                 "type"          : "ROUND_RESULT",
#                 "round"         : round_num,
#                 "round_label"   : round_label,
#                 "correct_answer": correct_key,
#                 "your_answer"   : their_answer,
#                 "was_correct"   : was_correct,
#                 "round_winner"  : round_winner_name,
#                 "explanation"   : q.get("explanation", ""),
#                 "is_tiebreaker" : is_tiebreaker,
#                 "player_names"  : display_names,
#                 "scores"        : {
#                     "Player 1": scores[conn_1],
#                     "Player 2": scores[conn_o]
#                 }
#             }
#             if not send_msg(conn, result_msg):
#                 _notify_left_and_raise(other_conn, other_role)

#         print(f"[SESSION] Round {round_label} done. Scores — P1:{scores[conn_1]} P2:{scores[conn_o]}")
#         time.sleep(ROUND_RESULT_DELAY)   # Let players read round outcome

#     try:
#         # Main rounds
#         for round_num, q in enumerate(selected_questions, start=1):
#             play_round(q=q, round_num=round_num, total_rounds=TOTAL_ROUNDS, is_tiebreaker=False)

#         # Sudden-death tiebreakers continue until tie is broken
#         tiebreak_count = 0
#         while scores[conn_1] == scores[conn_o]:
#             tiebreak_count += 1
#             if remaining_questions:
#                 q = random.choice(remaining_questions)
#                 remaining_questions.remove(q)
#             else:
#                 q = random.choice(QUESTIONS)

#             round_num = TOTAL_ROUNDS + tiebreak_count
#             print(f"[SESSION] Tie detected. Starting sudden-death round {tiebreak_count}.")
#             play_round(q=q, round_num=round_num, total_rounds=round_num, is_tiebreaker=True)

#         # Game-over
#         s1, s2 = scores[conn_1], scores[conn_o]
#         if   s1 > s2: overall_winner = "Player 1"
#         elif s2 > s1: overall_winner = "Player 2"
#         else:         overall_winner = "Tie"

#         game_over_msg = {
#             "type"  : "GAME_OVER",
#             "scores": {"Player 1": s1, "Player 2": s2},
#             "player_names": display_names,
#             "winner": overall_winner
#         }
#         send_msg(conn_1, game_over_msg)
#         send_msg(conn_o, game_over_msg)
#         print(f"[SESSION] Game over. Winner: {overall_winner}. Closing connections.")

#     except PlayerDisconnectedError:
#         print("[SESSION] A player disconnected mid-game. Ending session.")

#     finally:
#         conn_1.close()
#         conn_o.close()

# # Main server event loop
# # The main server loop structure adapted from the "TCP Echo Server" tutorial.
# def start_server() -> None:
#     """
#     Binds to HOST:PORT, listens for incoming TCP connections, performs the
#     CONNECT handshake, and manages a matchmaking queue. When two players are
#     queued a new GameSession daemon thread is spawned for them.
#     """
#     # Initialize an IPv4 (AF_INET) TCP (SOCK_STREAM) socket
#     server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     server.bind((HOST, PORT))
#     # Set socket to listening mode with a backlog
#     server.listen()
#     print(f"[STARTING] Trivia Quiz Server listening on {HOST}:{PORT}")

#     matchmaking_queue = []

#     try:
#         while True:
#             # Block until a new client connection arrives
#             conn, addr = server.accept()
#             print(f"[CONNECT] New connection from {addr}")

#             buf = [""]
#             msg = recv_msg(conn, buf)

#             if msg and msg.get("type") == "CONNECT":
#                 player_name_hint = msg.get("name", "Anonymous")
#                 print(f"[HANDSHAKE] '{player_name_hint}' joined the queue. Queue size: {len(matchmaking_queue)+1}")
#                 matchmaking_queue.append((conn, player_name_hint))
#                 send_msg(conn, {"type": "WAITING", "payload": "Waiting for an opponent..."})

#                 if len(matchmaking_queue) >= 2:
#                     player_1, name_1 = matchmaking_queue.pop(0)
#                     player_2, name_2 = matchmaking_queue.pop(0)
#                     print("[MATCH] Two players matched. Spawning GameSession thread.")
#                     session_thread = threading.Thread(
#                         target=game_session,
#                         args=(player_1, player_2, name_1, name_2),
#                         daemon=True
#                     )
#                     session_thread.start()
#             else:
#                 print(f"[REJECT] Bad handshake from {addr}. Closing.")
#                 conn.close()

#     except KeyboardInterrupt:
#         print("\n[SHUTDOWN] Server shutting down gracefully (Ctrl+C).")
#     finally:
#         server.close()


# if __name__ == "__main__":
#     start_server()

"""
CMPT 371 A3 - Competitive Trivia Quiz System (Server)
Architecture: TCP Sockets with Multithreaded Game Session Management
Protocol: Newline-delimited JSON messages over TCP

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

# Server configuration (Hardware/Network Constants)
HOST           = "127.0.0.1"    # Loopback address: the server only listens to connections on this machine
PORT           = 5050           # The specific "door" or port the server listens on
TOTAL_ROUNDS   = 10             # Number of questions per game
ANSWER_TIMEOUT = 15.0           # Seconds each player has to answer before they are timed out
CATEGORY_REVEAL_DELAY = 1.8     # Dramatic pause before showing each round question
ROUND_RESULT_DELAY = 3.2        # Pause to let players read the result before the next round

from questions import QUESTIONS

class PlayerDisconnectedError(Exception):
    """Custom error raised when a player suddenly drops their connection mid-game."""

def send_msg(conn: socket.socket, payload: dict) -> bool:
    """
    Takes a Python dictionary, converts it to a JSON text string, and sends it to the client.
    Why JSON? It gives our data a predictable, dictionary-like structure over the network.
    """
    # We add a newline character (\n) at the very end. This acts as our "end of message" boundary.
    raw = json.dumps(payload) + "\n"
    try:
        # sendall ensures every single byte is pushed through the network pipe
        conn.sendall(raw.encode("utf-8"))
        return True
    except OSError:
        # If the pipe is broken (client closed), we catch the error gracefully
        return False

def recv_msg(conn: socket.socket, buffer: list) -> dict | None:
    """
    Receives data from a client. 
    TCP STREAM BUFFERING FIX: TCP sends data as a continuous stream of bytes. If a client sends 
    two messages very fast, they might arrive mashed together. We use a persistent buffer (a list) 
    and split the data using our newline (\n) boundary to process one complete message at a time.
    """
    # Keep listening until we find our "end of message" marker (\n)
    while "\n" not in buffer[0]:
        try:
            # Receive up to 4096 bytes at a time and decode them from raw bytes to a readable string
            chunk = conn.recv(4096).decode("utf-8")
            if not chunk:           
                return None  # The client disconnected cleanly
            buffer[0] += chunk
        except (OSError, ConnectionResetError):
            return None      # The client crashed or network dropped

    # Split the buffer at the first newline. 
    # raw_msg gets the complete message, the rest stays in the buffer for next time.
    raw_msg, _, buffer[0] = buffer[0].partition("\n")
    try:
        # Convert the JSON string back into a usable Python dictionary
        return json.loads(raw_msg)
    except json.JSONDecodeError:
        return None          

def game_session(
    conn_1: socket.socket,
    conn_o: socket.socket,
    name_1: str,
    name_2: str,
) -> None:
    """
    This is the isolated game loop. It runs on its own background thread so it doesn't 
    stop the main server from matching other players. It acts as the 'Referee'.
    """
    player_roles = {conn_1: "Player 1", conn_o: "Player 2"}
    display_names = {"Player 1": name_1, "Player 2": name_2}
    scores       = {conn_1: 0,          conn_o: 0}

    # Persistent receive buffers for each player so their data doesn't get mixed up
    buf_1 = [""]
    buf_o = [""]
    buffers = {conn_1: buf_1, conn_o: buf_o}

    def _notify_left_and_raise(survivor: socket.socket, leaver_role: str) -> None:
        """If one player quits, tell the other player why the game is ending."""
        send_msg(survivor, {
            "type": "PLAYER_LEFT",
            "payload": f"{display_names[leaver_role]} disconnected.",
        })
        raise PlayerDisconnectedError()

    def _send_both(msg: dict) -> None:
        """Helper to broadcast the exact same message to both players at the same time."""
        ok_1 = send_msg(conn_1, msg)
        ok_o = send_msg(conn_o, msg)
        if not ok_1:
            _notify_left_and_raise(conn_o, "Player 1")
        if not ok_o:
            _notify_left_and_raise(conn_1, "Player 2")

    # Handshake: Send the initial WELCOME packets to tell clients the game is starting
    send_msg(conn_1, {
        "type": "WELCOME",
        "payload": {
            "role": "Player 1",
            "player_names": display_names,
        },
    })
    send_msg(conn_o, {
        "type": "WELCOME",
        "payload": {
            "role": "Player 2",
            "player_names": display_names,
        },
    })

    selected_questions = random.sample(QUESTIONS, min(TOTAL_ROUNDS, len(QUESTIONS)))
    remaining_questions = [q for q in QUESTIONS if q not in selected_questions]

    print(f"[SESSION] Game started with 2 players. {TOTAL_ROUNDS} rounds.")

    def play_round(q: dict, round_num: int, total_rounds: int, is_tiebreaker: bool = False) -> None:
        # Step 1: Tell clients what the category is
        round_label = f"TB-{round_num - TOTAL_ROUNDS}" if is_tiebreaker else str(round_num)

        reveal_msg = {
            "type": "CATEGORY_REVEAL",
            "category": q["category"],
            "round": round_num,
            "round_label": round_label,
            "total_rounds": total_rounds,
            "is_tiebreaker": is_tiebreaker,
            "player_names": display_names,
            "scores": {
                "Player 1": scores[conn_1],
                "Player 2": scores[conn_o],
            },
        }
        _send_both(reveal_msg)
        time.sleep(CATEGORY_REVEAL_DELAY) # Let the suspense build

        print(f"[SESSION] Round {round_label}: {q['question'][:50]}...")

        # Step 2: Send the actual question and start the timer
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
            "player_names" : display_names,
            "scores"      : {
                "Player 1": scores[conn_1],
                "Player 2": scores[conn_o]
            }
        }
        _send_both(question_msg)

        # We use nested threads here to listen to BOTH players at the exact same time.
        # This is crucial for a competitive race!
        answers            = {}   
        round_start        = time.monotonic()
        lock               = threading.Lock() # Prevents race conditions when updating variables
        first_submit_conn  = None
        disconnected_conns = set()

        def collect_answer(conn: socket.socket) -> None:
            """Waits for an answer from one specific client."""
            answer_val = None
            elapsed    = ANSWER_TIMEOUT
            # Set a hard timeout on the socket. If they take too long, it throws an error.
            conn.settimeout(ANSWER_TIMEOUT)
            try:
                msg = recv_msg(conn, buffers[conn])
                elapsed = time.monotonic() - round_start
                if msg is None:
                    with lock:
                        disconnected_conns.add(conn)
                else:
                    answer_val = msg.get("answer", "").upper() or None
            except (socket.timeout, OSError):
                pass   # Timeout happened — answer stays None
            finally:
                conn.settimeout(None)   # Remove the timeout for future messages

            nonlocal first_submit_conn
            with lock:
                # If this player was the first to answer, notify the other player
                if answer_val and first_submit_conn is None:
                    first_submit_conn = conn
                    other_conn = conn_o if conn is conn_1 else conn_1
                    send_msg(other_conn, {
                        "type": "OPPONENT_LOCKED",
                        "payload": "Opponent locked in.",
                    })
                answers[conn] = (answer_val, elapsed)

        # Start the listener threads
        t1 = threading.Thread(target=collect_answer, args=(conn_1,), daemon=True)
        t2 = threading.Thread(target=collect_answer, args=(conn_o,), daemon=True)
        t1.start()
        t2.start()
        
        # Wait until the timer runs out OR both players answer
        t1.join(timeout=ANSWER_TIMEOUT + 1)
        t2.join(timeout=ANSWER_TIMEOUT + 1)

        if disconnected_conns:
            if conn_1 in disconnected_conns:
                _notify_left_and_raise(conn_o, "Player 1")
            else:
                _notify_left_and_raise(conn_1, "Player 2")

        # Step 3: Server acts as the source of truth to calculate the winner
        correct_key       = q["answer"].upper()
        round_winner_name = None

        # Filter out wrong answers, keep only the correct ones
        correct_submissions = [
            (conn, elapsed)
            for conn, (ans, elapsed) in answers.items()
            if ans == correct_key
        ]

        if correct_submissions:
            # Find whoever answered in the shortest amount of time
            fastest_conn, _ = min(correct_submissions, key=lambda x: x[1])
            scores[fastest_conn] += 1
            round_winner_name = player_roles[fastest_conn]

        # Step 4: Broadcast the results of the round back to the clients
        for conn in (conn_1, conn_o):
            their_answer, _ = answers.get(conn, (None, ANSWER_TIMEOUT))
            was_correct = their_answer == correct_key
            other_conn  = conn_o if conn is conn_1 else conn_1
            other_role  = "Player 2" if conn is conn_1 else "Player 1"

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
                "player_names"  : display_names,
                "scores"        : {
                    "Player 1": scores[conn_1],
                    "Player 2": scores[conn_o]
                }
            }
            if not send_msg(conn, result_msg):
                _notify_left_and_raise(other_conn, other_role)

        print(f"[SESSION] Round {round_label} done. Scores — P1:{scores[conn_1]} P2:{scores[conn_o]}")
        time.sleep(ROUND_RESULT_DELAY)   

    try:
        # Loop through our 10 questions
        for round_num, q in enumerate(selected_questions, start=1):
            play_round(q=q, round_num=round_num, total_rounds=TOTAL_ROUNDS, is_tiebreaker=False)

        # Sudden-death tiebreaker logic
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

        # Step 5: Game is officially over. Calculate final standings.
        s1, s2 = scores[conn_1], scores[conn_o]
        if   s1 > s2: overall_winner = "Player 1"
        elif s2 > s1: overall_winner = "Player 2"
        else:         overall_winner = "Tie"

        game_over_msg = {
            "type"  : "GAME_OVER",
            "scores": {"Player 1": s1, "Player 2": s2},
            "player_names": display_names,
            "winner": overall_winner
        }
        send_msg(conn_1, game_over_msg)
        send_msg(conn_o, game_over_msg)
        print(f"[SESSION] Game over. Winner: {overall_winner}. Closing connections.")

    except PlayerDisconnectedError:
        print("[SESSION] A player disconnected mid-game. Ending session.")
        pass # The error was already handled and sent to the surviving player

    finally:
        # Always clean up and close the ports when the thread finishes
        conn_1.close()
        conn_o.close()

def start_server() -> None:
    """
    The main lobby of the server. It listens for incoming connections and pairs 
    them up. Because it spawns background threads for the games, this lobby 
    is never "blocked" and can accept hundreds of players concurrently.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # SO_REUSEADDR allows us to restart the server immediately after closing it without OS port-blocking errors
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    
    server.listen() # Open the door
    print(f"[STARTING] Trivia Quiz Server listening on {HOST}:{PORT}")

    matchmaking_queue = [] # Our lobby waiting room

    try:
        while True:
            # The server pauses here (blocks) until a client knocks on the door
            conn, addr = server.accept()
            print(f"[CONNECT] New connection from {addr}")

            buf = [""]
            msg = recv_msg(conn, buf)

            # Ensure the first message is the expected CONNECT handshake
            if msg and msg.get("type") == "CONNECT":
                player_name_hint = msg.get("name", "Anonymous")
                print(f"[HANDSHAKE] '{player_name_hint}' joined the queue. Queue size: {len(matchmaking_queue)+1}")
                matchmaking_queue.append((conn, player_name_hint))
                
                # Tell the client they are successfully in the lobby
                send_msg(conn, {"type": "WAITING", "payload": "Waiting for an opponent..."})

                # If 2 people are in the waiting room, pop them out and start a game!
                if len(matchmaking_queue) >= 2:
                    player_1, name_1 = matchmaking_queue.pop(0)
                    player_2, name_2 = matchmaking_queue.pop(0)
                    print("[MATCH] Two players matched. Spawning GameSession thread.")
                    
                    # Start the isolated game loop on a brand new background thread
                    session_thread = threading.Thread(
                        target=game_session,
                        args=(player_1, player_2, name_1, name_2),
                        daemon=True # Daemon means this thread dies automatically if the main server shuts down
                    )
                    session_thread.start()
            else:
                print(f"[REJECT] Bad handshake from {addr}. Closing.")
                conn.close()

    except KeyboardInterrupt:
        # Added flush=True to force the terminal to display this immediately
        print("\n[SHUTDOWN] Server shutting down gracefully (Ctrl+C).", flush=True)
    finally:
        server.close()
        print("[SHUTDOWN] Sockets closed. Goodbye!", flush=True)

if __name__ == "__main__":
    start_server()