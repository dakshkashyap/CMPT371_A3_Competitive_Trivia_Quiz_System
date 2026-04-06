# CMPT 371 A3 Socket Programming - `Competitive Trivia Quiz System`

**Course:** CMPT 371 - Data Communications & Networking  
**Instructor:** Mirza Zaeem Baig  
**Semester:** Spring 2026  


## Group Members

| Name | Student ID | Email |
|:-----|:-----------|:------|
| Daksh Kashyap | 301467170 | dka147@sfu.ca |
| Gurtaj Sangha | 301563146 | teammate@student.university.edu |


## 1. Project Overview & Description

This project is a **real-time, competitive Trivia Quiz system** built using Python's Socket API over TCP.  
Two players connect to a central server and compete head-to-head by answering the same multiple-choice trivia questions simultaneously.

**Key features:**
- 20-question bank across 4 categories: Science, History, Technology, and Geography
- Server-enforced 15-second answer timer per round (10 questions per game)
- First correct answer wins the round point — simultaneous competition
- Sudden-death tiebreaker rounds if scores are tied after 10 rounds
- **Desktop GUI client** (`client_desktop.py`) built with PySide6 — animated pages, live countdown progress bar, scoreboard, and audio feedback (correct/wrong/timeout sounds)
- **CLI client** (`client.py`) — terminal fallback with ANSI colour and live countdown
- Fully concurrent: multiple separate games can run at the same time
- Graceful mid-game disconnect handling: the surviving player sees a popup and is returned to the main screen

**Architecture:** Client-Server over TCP  
**Protocol:** Custom application-layer protocol using newline-delimited JSON messages


## 2. System Limitations & Edge Cases

As required by the project specifications, we have identified and handled (or explicitly defined) the following limitations:

### Handled

- **Handling Multiple Clients Concurrently:**  
  *Solution:* Python's `threading` module is used. When two clients are matched, they are spawned into an isolated `game_session` daemon thread. The main server listener loop is never blocked, allowing more pairs to queue simultaneously.

- **TCP Stream Buffering:**  
  *Solution:* TCP is a byte stream — multiple JSON messages can arrive concatenated. We implement an application-layer boundary by appending `\n` to every JSON payload. The `recv_msg()` function maintains a per-connection string buffer and only returns complete messages, splitting on `\n`.

- **Answer Timeout Enforcement:**  
  *Solution:* The server sets `conn.settimeout(ANSWER_TIMEOUT)` before blocking on `recv()`. If a client does not respond in time, a `socket.timeout` exception is caught and their answer is recorded as `None` (no score). The GUI client displays a live countdown progress bar and stops accepting input when the timer fires.

- **Client Disconnecting Mid-Game:**  
  *Solution:* The server detects disconnection at every send and receive point. `send_msg()` returns `False` on `OSError` and `recv_msg()` returns `None` on an empty read or socket error. When either is detected, the server sends a `PLAYER_LEFT` message to the surviving player and cleanly ends the session. The GUI client handles `PLAYER_LEFT` with a popup dialog and automatically returns to the connect screen.

- **Input Validation:**  
  *Solution:* The GUI client only enables answer buttons (A / B / C / D) during the active question window. The CLI client only accepts `A`, `B`, `C`, or `D` as valid inputs. The server validates the answer against the stored correct key server-side, so a modified client cannot send an arbitrary winning answer.

### Known Limitations

- **Thread scaling:** Thread-per-session model works well for small numbers of concurrent games. For hundreds of simultaneous games, an `asyncio`-based or thread-pool approach would be more efficient.
- **No reconnection support:** If a player's connection drops mid-game, there is no mechanism to rejoin. The other player is notified and returned to the main screen.
- **LAN play only (by default):** The server binds to `127.0.0.1` by default. To allow connections from other machines, change `HOST = "0.0.0.0"` in `server.py` and ensure the firewall allows port 5050.
- **No authentication:** Players choose their own display name with no verification.
- **Audio on Windows only:** The desktop client's sound feedback uses `winsound.PlaySound`, which is Windows-specific. On other platforms the sounds are silently skipped.

## 3. Video Demo

[Watch Project Demo](https://www.youtube.com/watch?v=REPLACE_WITH_YOUR_LINK)

## 4. Prerequisites (Fresh Environment)

To run this project you need:
- **Python 3.10** or higher
- **PySide6** — required for the desktop GUI client (`client_desktop.py`)
- The CLI client (`client.py`) has no external dependencies — all modules used (`socket`, `threading`, `json`, `sys`, `time`, `random`) are part of the Python Standard Library
- A terminal that supports **ANSI escape codes** for the CLI client (macOS Terminal, Linux bash, Windows Terminal, VS Code terminal)

## 5. Step-by-Step Run Guide

### Step 1 - Clone / Download the repository

```bash
git clone https://github.com/dakshkashyap/CMPT371-A3-Socket-Programmming.git
cd CMPT371-A3-Socket-Programmming/src
```

### Step 2 - Create a virtual environment and install dependencies

```bash
python -m venv .venv

# Activate it:
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# Install PySide6 (required for the desktop GUI client):
pip install PySide6
```

### Step 3 - Start the Server

Open **Terminal 1** and run:

```bash
python server.py
```

Expected output:
```
[STARTING] Trivia Quiz Server listening on 127.0.0.1:5050
```

Leave this terminal running throughout the game.

### Step 4 - Launch the clients

**Desktop GUI client (recommended)** — open two separate terminals and run in each:

```bash
python client_desktop.py
```

Enter a name and server address in the connection screen, then click **Connect**. The second player connecting will trigger the match to start automatically.

**CLI client (alternative)** — open two separate terminals and run in each:

```bash
python client.py
```

Expected interaction:
```
Enter your name: Alice
Connecting to 127.0.0.1:5050...
Waiting for an opponent...
```

Both clients will now simultaneously receive and display trivia questions.

### Step 5 - Gameplay

- Each player sees the **same question** with 4 options (A / B / C / D)
- In the GUI client, click an answer button; in the CLI client, type the letter and press **Enter**
- You have **15 seconds** — a live countdown is shown
- If scores are tied after 10 rounds, sudden-death tiebreaker rounds continue until the tie is broken
- After each round, both clients display the correct answer, whether you were right, and updated scores
- After the final round the scoreboard and winner are shown; the GUI returns you to the connect screen automatically

### Step 6 - Stopping the server

Press **Ctrl+C** in Terminal 1:
```
[SHUTDOWN] Server shutting down gracefully (Ctrl+C).
```

## 6. Technical Protocol Details (JSON over TCP)

We designed a custom application-layer protocol using **JSON messages delimited by a newline `\n`** over TCP.

| Message Type | Direction | Key Fields |
|:-------------|:----------|:-----------|
| `CONNECT` | Client → Server | `type`, `name` |
| `WAITING` | Server → Client | `type`, `payload` |
| `WELCOME` | Server → Client | `type`, `payload` (role, player_names) |
| `CATEGORY_REVEAL` | Server → Client | `type`, `category`, `round`, `round_label`, `total_rounds`, `is_tiebreaker`, `player_names`, `scores` |
| `QUESTION` | Server → Client | `type`, `round`, `round_label`, `total_rounds`, `category`, `question`, `options`, `timeout`, `is_tiebreaker`, `player_names`, `scores` |
| `ANSWER` | Client → Server | `type`, `answer` |
| `OPPONENT_LOCKED` | Server → Client | `type`, `payload` |
| `ROUND_RESULT` | Server → Client | `type`, `correct_answer`, `your_answer`, `was_correct`, `round_winner`, `explanation`, `is_tiebreaker`, `player_names`, `scores` |
| `GAME_OVER` | Server → Client | `type`, `scores`, `winner`, `player_names` |
| `PLAYER_LEFT` | Server → Client | `type`, `payload` (disconnect message) |

**TCP Stream Fix:** Every JSON payload is terminated with `\n`. Receivers split the buffer on `\n` and parse each segment atomically, preventing partial or merged message corruption.

---

## 7. File Structure

```text
CMPT371-A3-Socket-Programmming/
├── README.md
└── src/
    ├── server.py            ← Server: matchmaking, game logic, scoring, disconnect handling
    ├── client_desktop.py    ← Desktop GUI client: PySide6 interface, animations, audio feedback
    ├── client.py            ← CLI client: ANSI terminal interface, live countdown
    └── questions.py         ← Question bank (20 questions, 4 categories)
```

## 8. Academic Integrity & References

- **Code Origin:** All socket boilerplate was adapted from the course tutorial "TCP Echo Server". The game logic, custom protocol, concurrent answer collection, GUI interface, and audio synthesis were written by the group members.
- **GenAI Usage:**
  - ChatGPT / Perplexity AI was used to assist with the ANSI colour codes for the CLI interface, the `CountdownTimer` thread design, and README formatting.
  - Claude Code (Anthropic) was used to assist with the PySide6 GUI implementation, audio synthesis, and disconnect-handling logic.
  - All generated code was reviewed, understood, and modified by the group.
- **References:**
  - [Python Socket Programming HOWTO](https://docs.python.org/3/howto/sockets.html)
  - [Real Python: Intro to Python Threading](https://realpython.com/intro-to-python-threading/)
  - [Python `json` module docs](https://docs.python.org/3/library/json.html)
  - [PySide6 Documentation](https://doc.qt.io/qtforpython-6/)
