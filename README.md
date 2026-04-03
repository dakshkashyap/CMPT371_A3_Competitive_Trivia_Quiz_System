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
- Colourful, animated CLI interface with live countdown timer
- Fully concurrent: multiple separate games can run at the same time

**Architecture:** Client-Server over TCP  
**Protocol:** Custom application-layer protocol using newline-delimited JSON messages


## 2. System Limitations & Edge Cases

As required by the project specifications, we have identified and handled (or explicitly defined) the following limitations:

### ✅ Handled

- **Handling Multiple Clients Concurrently:**  
  *Solution:* Python's `threading` module is used. When two clients are matched, they are spawned into an isolated `game_session` daemon thread. The main server listener loop is never blocked, allowing more pairs to queue simultaneously.

- **TCP Stream Buffering:**  
  *Solution:* TCP is a byte stream — multiple JSON messages can arrive concatenated. We implement an application-layer boundary by appending `\n` to every JSON payload. The `recv_msg()` function maintains a per-connection string buffer and only returns complete messages, splitting on `\n`.

- **Answer Timeout Enforcement:**  
  *Solution:* The server sets `conn.settimeout(ANSWER_TIMEOUT)` before blocking on `recv()`. If a client does not respond in time, a `socket.timeout` exception is caught and their answer is recorded as `None` (no score). The client also displays a live countdown and stops accepting input when the timer fires.

- **Client Disconnecting Mid-Game:**  
  *Solution:* All `recv()` calls are wrapped in `try/except (OSError, ConnectionResetError)` blocks. A `None` return from `recv_msg()` signals disconnection, and the session thread exits cleanly, closing both sockets.

- **Input Validation:**  
  *Solution:* The client only accepts `A`, `B`, `C`, or `D` as valid inputs. Invalid inputs print an error and prompt again. The server validates the answer against the stored correct key server-side, so a modified client cannot send an arbitrary winning answer.

### ⚠️ Known Limitations

- **Thread scaling:** Thread-per-session model works well for small numbers of concurrent games. For hundreds of simultaneous games, an `asyncio`-based or thread-pool approach would be more efficient.
- **No reconnection support:** If a player's connection drops mid-game, there is no mechanism to rejoin. The game session ends.
- **LAN play only (by default):** The server binds to `127.0.0.1` by default. To allow connections from other machines, change `HOST = "0.0.0.0"` in `server.py` and ensure the firewall allows port 5050.
- **No authentication:** Players choose their own display name with no verification.

## 3. Video Demo

[▶️ Watch Project Demo](https://www.youtube.com/watch?v=REPLACE_WITH_YOUR_LINK)

## 4. Prerequisites (Fresh Environment)

To run this project you need:
- **Python 3.10** or higher
- **No external pip packages required** — all modules used (`socket`, `threading`, `json`, `sys`, `time`, `random`) are part of the Python Standard Library
- A terminal that supports **ANSI escape codes** (macOS Terminal, Linux bash, Windows Terminal, VS Code terminal)

## 5. Step-by-Step Run Guide
### Step 1 - Clone / Download the repository

```bash
git clone https://github.com/YOUR_USERNAME/CMPT371_A3_TriviaQuiz.git
cd CMPT371_A3_TriviaQuiz/src
```

### Step 2 - (Optional) Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### Step 3 - Start the Server

Open **Terminal 1** and run:

```bash
python3 src/server.py
```

Expected output:
[STARTING] Trivia Quiz Server listening on 127.0.0.1:5050

Leave this terminal running throughout the game.

### Step 4 - Connect Player 1

Open **Terminal 2** and run:

```bash
python3 src/client.py
```

Expected interaction:
Enter your name: Alice
Connecting to 127.0.0.1:5050...
⏳ Waiting for an opponent...

### Step 5 - Connect Player 2

Open **Terminal 3** and run:

```bash
python3 src/client.py
```

Expected interaction:
Enter your name: Bob
Connecting to 127.0.0.1:5050...
✔ Match found! You are Player 2

Both terminals will now simultaneously receive and display trivia questions.

### Step 6 - Gameplay

- Each player sees the **same question** with 4 options (A / B / C / D)
- Type your answer letter and press **Enter**
- You have **15 seconds** — a live countdown is shown
- After each round, both terminals display the correct answer, whether you were right, and updated scores
- After 10 rounds the final scoreboard is shown and connections close automatically

### Step 7 - Stopping the server

Press **Ctrl+C** in Terminal 1.
[SHUTDOWN] Server shutting down gracefully (Ctrl+C).

## 6. Technical Protocol Details (JSON over TCP)

We designed a custom application-layer protocol using **JSON messages delimited by a newline `\n`** over TCP.

| Message Type | Direction | Key Fields |
|:-------------|:----------|:-----------|
| `CONNECT` | Client → Server | `type`, `name` |
| `WAITING` | Server → Client | `type`, `payload` |
| `WELCOME` | Server → Client | `type`, `payload` (role) |
| `QUESTION` | Server → Client | `type`, `round`, `total_rounds`, `category`, `question`, `options`, `timeout`, `scores` |
| `ANSWER` | Client → Server | `type`, `answer` |
| `ROUND_RESULT` | Server → Client | `type`, `correct_answer`, `your_answer`, `was_correct`, `round_winner`, `scores` |
| `GAME_OVER` | Server → Client | `type`, `scores`, `winner` |

**TCP Stream Fix:** Every JSON payload is terminated with `\n`. Receivers split the buffer on `\n` and parse each segment atomically, preventing partial or merged message corruption.

---

## 7. File Structure

```text
CMPT371_A3_TriviaQuiz/
├── README.md
└── src/
    ├── server.py       ← Server: matchmaking, game logic, scoring
    ├── client.py       ← Client: CLI interface, timer, display
    └── questions.py    ← Question bank (20 questions, 4 categories)
```

## 8. Academic Integrity & References

- **Code Origin:** All socket boilerplate was adapted from the course tutorial "TCP Echo Server". The game logic, custom protocol, concurrent answer collection, and CLI interface were written by the group members.
- **GenAI Usage:**
  - ChatGPT / Perplexity AI was used to assist with the ANSI colour codes for the CLI interface, the `CountdownTimer` thread design, and README formatting.
  - All generated code was reviewed, understood, and modified by the group.
- **References:**
  - [Python Socket Programming HOWTO](https://docs.python.org/3/howto/sockets.html)
  - [Real Python: Intro to Python Threading](https://realpython.com/intro-to-python-threading/)
  - [Python `json` module docs](https://docs.python.org/3/library/json.html)