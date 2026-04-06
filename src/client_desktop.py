
from __future__ import annotations

import json
import socket
import threading
import time
from typing import Optional

try:
    import winsound
except ImportError:  # Non-Windows environments
    winsound = None

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QThread, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5050


class NetworkClientThread(QThread):
    message_received = Signal(dict)
    connection_failed = Signal(str)
    disconnected = Signal(str)

    def __init__(self, host: str, port: int, name: str) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.name = name
        self._conn: Optional[socket.socket] = None
        self._buffer = ""
        self._send_lock = threading.Lock()

    def run(self) -> None:
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(5.0)
            conn.connect((self.host, self.port))
            conn.settimeout(None)
            self._conn = conn
            self.send_payload({"type": "CONNECT", "name": self.name})
        except OSError as exc:
            self.connection_failed.emit(f"Could not connect to {self.host}:{self.port} ({exc})")
            return

        while not self.isInterruptionRequested():
            msg = self._recv_message()
            if msg is None:
                if not self.isInterruptionRequested():
                    self.disconnected.emit("Server disconnected.")
                return
            self.message_received.emit(msg)

    def _recv_message(self) -> Optional[dict]:
        if self._conn is None:
            return None

        while "\n" not in self._buffer:
            try:
                chunk = self._conn.recv(4096)
            except OSError:
                return None
            if not chunk:
                return None
            self._buffer += chunk.decode("utf-8")

        raw, _, self._buffer = self._buffer.partition("\n")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def send_payload(self, payload: dict) -> bool:
        if self._conn is None:
            return False
        raw = json.dumps(payload) + "\n"
        data = raw.encode("utf-8")
        try:
            with self._send_lock:
                self._conn.sendall(data)
            return True
        except OSError:
            return False

    def close(self) -> None:
        self.requestInterruption()
        try:
            if self._conn:
                self._conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            if self._conn:
                self._conn.close()
        except OSError:
            pass


class TriviaClientWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("CMPT 371 Trivia Quiz")
        self.resize(980, 680)

        self.net_thread: Optional[NetworkClientThread] = None
        self.my_role: Optional[str] = None
        self.current_timeout = 0.0
        self.deadline = 0.0
        self.answer_submitted = False
        self._fade_anim: Optional[QPropertyAnimation] = None
        self._waiting_dot_phase = 0
        self.latest_scores = {"Player 1": 0, "Player 2": 0}
        self.player_names = {"Player 1": "Player 1", "Player 2": "Player 2"}
        self.game_over_received = False

        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(100)
        self.tick_timer.timeout.connect(self._update_countdown)

        self.waiting_dots_timer = QTimer(self)
        self.waiting_dots_timer.setInterval(450)
        self.waiting_dots_timer.timeout.connect(self._tick_waiting_message)

        self.lock_notice_timer = QTimer(self)
        self.lock_notice_timer.setSingleShot(True)
        self.lock_notice_timer.timeout.connect(lambda: self.locked_notice.setText(""))

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.connect_page = self._build_connect_page()
        self.waiting_page = self._build_waiting_page()
        self.reveal_page = self._build_reveal_page()
        self.question_page = self._build_question_page()
        self.result_page = self._build_result_page()
        self.game_over_page = self._build_game_over_page()

        self.stack.addWidget(self.connect_page)
        self.stack.addWidget(self.waiting_page)
        self.stack.addWidget(self.reveal_page)
        self.stack.addWidget(self.question_page)
        self.stack.addWidget(self.result_page)
        self.stack.addWidget(self.game_over_page)

        self._apply_styles()

    def _show_dialog(self, title: str, text: str, level: str = "info") -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(text)

        if level == "error":
            dialog.setIcon(QMessageBox.Critical)
        elif level == "warning":
            dialog.setIcon(QMessageBox.Warning)
        else:
            dialog.setIcon(QMessageBox.Information)

        dialog.setStyleSheet(
            """
            QMessageBox {
                background: #fffdf8;
            }
            QMessageBox QLabel {
                color: #1f3a5f;
                font-size: 14px;
            }
            QMessageBox QPushButton {
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                background: #2f5d67;
                color: #ffffff;
                min-width: 72px;
                font-weight: 600;
            }
            QMessageBox QPushButton:hover {
                background: #3b6d79;
            }
            """
        )
        dialog.exec()

    def _card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        return card

    def _build_connect_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(48, 36, 48, 36)
        outer.setSpacing(18)

        shell = QHBoxLayout()
        shell.setSpacing(22)

        hero = self._card()
        hero.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setSpacing(14)

        eyebrow = QLabel("CMPT 371 • SOCKET PROGRAMMING")
        eyebrow.setObjectName("eyebrow")

        title = QLabel("Competitive\nTrivia Arena")
        title.setObjectName("heroTitle")

        subtitle = QLabel("Race another player in real time. Fastest correct answer wins the round.")
        subtitle.setObjectName("heroSubtitle")
        subtitle.setWordWrap(True)

        bullets = QLabel(
            "• Live matchmaking\n"
            "• Server-authoritative scoring\n"
            "• 10 rounds, 15-second pressure"
        )
        bullets.setObjectName("heroBullets")

        status_strip = QLabel("Tip: Run the server first, then open two desktop clients.")
        status_strip.setObjectName("heroTip")

        hero_layout.addWidget(eyebrow)
        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        hero_layout.addWidget(bullets)
        hero_layout.addStretch(1)
        hero_layout.addWidget(status_strip)

        card = self._card()
        card.setObjectName("connectCard")
        form_layout = QVBoxLayout(card)
        form_layout.setSpacing(12)

        form_title = QLabel("Join Match")
        form_title.setObjectName("formTitle")

        form_subtitle = QLabel("Enter connection details to connect to the quiz server")
        form_subtitle.setObjectName("formSubtitle")
        form_subtitle.setWordWrap(True)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Player name")

        self.host_input = QLineEdit(DEFAULT_HOST)
        self.port_input = QLineEdit(str(DEFAULT_PORT))

        connect_btn = QPushButton("Connect")
        connect_btn.setObjectName("primaryButton")
        connect_btn.clicked.connect(self._on_connect_clicked)

        grid.addWidget(QLabel("Name"), 0, 0)
        grid.addWidget(self.name_input, 0, 1)
        grid.addWidget(QLabel("Host"), 1, 0)
        grid.addWidget(self.host_input, 1, 1)
        grid.addWidget(QLabel("Port"), 2, 0)
        grid.addWidget(self.port_input, 2, 1)

        quick_info = QGroupBox("Connection Preset")
        quick_info.setObjectName("presetBox")
        quick_layout = QVBoxLayout(quick_info)
        quick_layout.setContentsMargins(12, 12, 12, 12)
        quick_layout.setSpacing(6)
        quick_layout.addWidget(QLabel("Host: 127.0.0.1"))
        quick_layout.addWidget(QLabel("Port: 5050"))

        form_layout.addWidget(form_title)
        form_layout.addWidget(form_subtitle)
        form_layout.addLayout(grid)
        form_layout.addWidget(quick_info)
        form_layout.addWidget(connect_btn)

        shell.addWidget(hero, 3)
        shell.addWidget(card, 2)

        outer.addLayout(shell)
        return page

    def _build_waiting_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(60, 40, 60, 40)

        card = self._card()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        label = QLabel("Waiting for an opponent...")
        label.setObjectName("title")
        label.setAlignment(Qt.AlignCenter)

        self.waiting_status = QLabel("Connected. You will be matched automatically.")
        self.waiting_status.setObjectName("status")
        self.waiting_status.setAlignment(Qt.AlignCenter)
        self.waiting_score = QLabel("Scores will appear after match starts")
        self.waiting_score.setObjectName("scoreboard")
        self.waiting_score.setAlignment(Qt.AlignCenter)

        card_layout.addWidget(label)
        card_layout.addWidget(self.waiting_status)
        card_layout.addWidget(self.waiting_score)

        layout.addStretch(1)
        layout.addWidget(card)
        layout.addStretch(2)
        return page

    def _build_reveal_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(60, 40, 60, 40)

        card = self._card()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        self.reveal_round = QLabel("Round 1/10")
        self.reveal_round.setObjectName("title")
        self.reveal_round.setAlignment(Qt.AlignCenter)

        self.reveal_category = QLabel("Next category: Fundamentals")
        self.reveal_category.setObjectName("heroSubtitle")
        self.reveal_category.setAlignment(Qt.AlignCenter)

        self.reveal_score = QLabel("Scores will appear after match starts")
        self.reveal_score.setObjectName("scoreboard")
        self.reveal_score.setAlignment(Qt.AlignCenter)

        card_layout.addWidget(self.reveal_round)
        card_layout.addWidget(self.reveal_category)
        card_layout.addWidget(self.reveal_score)

        layout.addStretch(1)
        layout.addWidget(card)
        layout.addStretch(2)
        return page

    def _build_question_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        root = QVBoxLayout(page)
        root.setContentsMargins(40, 24, 40, 24)
        root.setSpacing(12)

        self.header_label = QLabel("Round 1/10")
        self.header_label.setObjectName("title")

        self.category_label = QLabel("Category")
        self.category_label.setObjectName("tag")

        self.role_label = QLabel("")
        self.role_label.setObjectName("roleTag")
        self.question_score = QLabel("Scores will appear after match starts")
        self.question_score.setObjectName("scoreboard")

        q_card = self._card()
        q_layout = QVBoxLayout(q_card)
        self.question_label = QLabel("Question text")
        self.question_label.setWordWrap(True)
        self.question_label.setObjectName("question")
        q_layout.addWidget(self.question_label)

        answers_card = self._card()
        answers_layout = QVBoxLayout(answers_card)
        answers_layout.setSpacing(10)

        self.answer_buttons: list[QPushButton] = []
        for letter in ("A", "B", "C", "D"):
            btn = QPushButton(f"{letter})")
            btn.setProperty("answerButton", True)
            btn.clicked.connect(lambda _checked=False, l=letter: self._submit_answer(l))
            self.answer_buttons.append(btn)
            answers_layout.addWidget(btn)

        timer_row = QHBoxLayout()
        self.timer_label = QLabel("Time left: 15.0s")
        self.timer_bar = QProgressBar()
        self.timer_bar.setObjectName("timerBar")
        self.timer_bar.setRange(0, 150)
        self.timer_bar.setValue(150)
        timer_row.addWidget(self.timer_label)
        timer_row.addWidget(self.timer_bar, 1)

        self.question_hint = QLabel("Choose one option. Your first selection is final.")
        self.locked_notice = QLabel("")
        self.locked_notice.setObjectName("lockedNotice")

        root.addWidget(self.header_label)
        root.addWidget(self.question_score)
        role_row = QHBoxLayout()
        role_row.addWidget(self.category_label)
        role_row.addStretch(1)
        role_row.addWidget(self.role_label)
        root.addLayout(role_row)
        root.addWidget(q_card)
        root.addWidget(answers_card)
        root.addLayout(timer_row)
        root.addWidget(self.question_hint)
        root.addWidget(self.locked_notice)
        root.addStretch(1)
        return page

    def _build_result_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(60, 40, 60, 40)

        card = self._card()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        title = QLabel("Round Result")
        title.setObjectName("title")

        self.result_main = QLabel("")
        self.result_main.setWordWrap(True)
        self.result_extra = QLabel("")
        self.result_score = QLabel("")
        self.result_explanation = QLabel("")
        self.result_explanation.setWordWrap(True)
        self.result_explanation.setObjectName("explanation")

        card_layout.addWidget(title)
        card_layout.addWidget(self.result_main)
        card_layout.addWidget(self.result_extra)
        card_layout.addWidget(self.result_score)
        card_layout.addWidget(self.result_explanation)

        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _build_game_over_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(60, 40, 60, 40)

        card = self._card()
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        self.final_heading = QLabel("Game Over")
        self.final_heading.setObjectName("title")

        self.final_result = QLabel("")
        self.final_result.setObjectName("finalResult")
        self.final_result.setWordWrap(True)
        self.final_scores = QLabel("")
        self.final_scores.setObjectName("scoreboard")

        btn_row = QHBoxLayout()
        self.play_again_btn = QPushButton("Back to Connect")
        self.play_again_btn.setObjectName("primaryButton")
        self.play_again_btn.clicked.connect(self._reset_to_connect)
        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setObjectName("secondaryButton")
        self.exit_btn.clicked.connect(self.close)
        btn_row.addWidget(self.play_again_btn)
        btn_row.addWidget(self.exit_btn)

        card_layout.addWidget(self.final_heading)
        card_layout.addWidget(self.final_result)
        card_layout.addWidget(self.final_scores)
        card_layout.addLayout(btn_row)

        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                color: #2b2a28;
                font-family: "Trebuchet MS", "Segoe UI", "Arial";
                font-size: 14px;
            }
            QMainWindow {
                background: #f7f4ee;
            }
            QWidget#page {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #fbf8f1,
                    stop: 1 #efe8dc
                );
            }
            QLabel {
                background: transparent;
            }
            QFrame#card {
                background: #fffdf8;
                border: 1px solid #dfd4c2;
                border-radius: 22px;
                padding: 18px;
            }
            QFrame#heroCard {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #1f3a5f,
                    stop: 1 #2f5d67
                );
                border: 1px solid #3b6d79;
                border-radius: 24px;
            }
            QFrame#connectCard {
                background: #fffdf8;
                border-radius: 22px;
            }
            QLabel#title {
                font-size: 32px;
                font-weight: 700;
                color: #1f3a5f;
            }
            QLabel#heroTitle {
                font-size: 46px;
                font-weight: 800;
                color: #fdf7ea;
                line-height: 1.1;
            }
            QLabel#heroSubtitle {
                font-size: 16px;
                color: #dbe8ef;
            }
            QLabel#heroBullets {
                font-size: 15px;
                color: #e7f1f5;
                line-height: 1.5;
            }
            QLabel#heroTip {
                font-size: 13px;
                color: #c5dbe5;
                border-top: 1px solid #547c8a;
                padding-top: 10px;
            }
            QLabel#eyebrow {
                font-size: 12px;
                font-weight: 700;
                color: #bdd8e5;
                letter-spacing: 1px;
            }
            QLabel#formTitle {
                font-size: 28px;
                font-weight: 700;
                color: #1f3a5f;
            }
            QLabel#formSubtitle {
                color: #5e5a52;
                font-size: 14px;
            }
            QLabel#subtitle {
                color: #5d6470;
                font-size: 16px;
            }
            QLabel#status {
                color: #4a5564;
                font-size: 16px;
            }
            QLabel#scoreboard {
                font-size: 15px;
                color: #1f3a5f;
                font-weight: 700;
            }
            QLabel#lockedNotice {
                color: #9b6117;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#explanation {
                color: #4a5564;
                font-size: 14px;
                background: #f4eee3;
                border: 1px solid #dccfbf;
                border-radius: 10px;
                padding: 8px;
            }
            QLabel#finalResult {
                font-size: 24px;
                font-weight: 800;
            }
            QLabel#tag {
                color: #4d6a2e;
                font-weight: 700;
                font-size: 13px;
                background: #edf3df;
                border: 1px solid #c6d6a9;
                border-radius: 10px;
                padding: 4px 10px;
            }
            QLabel#roleTag {
                color: #6b3f1f;
                background: #fde9d2;
                border: 1px solid #efbf8f;
                border-radius: 10px;
                padding: 4px 10px;
                font-weight: 700;
            }
            QLabel#question {
                font-size: 21px;
                font-weight: 600;
                line-height: 1.4;
            }
            QLineEdit {
                border: 1px solid #c9bca9;
                border-radius: 12px;
                padding: 10px;
                background: #fffdf8;
            }
            QLineEdit:focus {
                border: 1px solid #2f5d67;
            }
            QGroupBox#presetBox {
                border: 1px solid #d6c8b5;
                border-radius: 14px;
                margin-top: 10px;
                padding-top: 8px;
                font-weight: 700;
                color: #4c5b6f;
                background: #fbf5ea;
            }
            QGroupBox#presetBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QPushButton {
                border: none;
                border-radius: 14px;
                padding: 10px 14px;
                background: #3e4f66;
                color: #ffffff;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #53657f;
            }
            QPushButton#primaryButton {
                background: #2f5d67;
            }
            QPushButton#primaryButton:hover {
                background: #3b6d79;
            }
            QPushButton#secondaryButton {
                background: #7a8695;
            }
            QPushButton#secondaryButton:hover {
                background: #8b96a4;
            }
            QPushButton[answerButton="true"] {
                text-align: left;
                padding: 13px;
                background: #334e68;
                font-size: 15px;
            }
            QPushButton[answerButton="true"]:hover {
                background: #426286;
            }
            QPushButton[answerButton="true"]:disabled {
                background: #b2bcc6;
                color: #f7f9fb;
            }
            QProgressBar {
                border: 1px solid #cabca9;
                border-radius: 10px;
                text-align: center;
                background: #eee6da;
            }
            QProgressBar::chunk {
                border-radius: 9px;
                background: #2f5d67;
            }
            """
        )

    def _switch_page(self, page: QWidget) -> None:
        self.stack.setCurrentWidget(page)
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutCubic)

        def clear_effect() -> None:
            page.setGraphicsEffect(None)

        anim.finished.connect(clear_effect)
        self._fade_anim = anim
        anim.start()

    def _tick_waiting_message(self) -> None:
        self._waiting_dot_phase = (self._waiting_dot_phase + 1) % 4
        dots = "." * self._waiting_dot_phase
        role = self.my_role or "matchmaking queue"
        self.waiting_status.setText(f"Waiting for an opponent{dots}  |  {role}")

    def _set_timer_visual(self, remaining: float) -> None:
        ratio = 0.0 if self.current_timeout <= 0 else remaining / self.current_timeout
        if ratio > 0.55:
            color = "#4c956c"
            text = "#2f6d4a"
        elif ratio > 0.25:
            color = "#d18a2f"
            text = "#9b6117"
        else:
            color = "#c44536"
            text = "#922b21"

        self.timer_label.setStyleSheet(f"font-weight: 700; color: {text};")
        self.timer_bar.setStyleSheet(
            f"""
            QProgressBar {{
                border: 1px solid #cabca9;
                border-radius: 8px;
                text-align: center;
                background: #eee6da;
            }}
            QProgressBar::chunk {{
                border-radius: 7px;
                background: {color};
            }}
            """
        )

    def _format_scores(self, scores: dict) -> str:
        p1 = self.player_names.get("Player 1", "Player 1")
        p2 = self.player_names.get("Player 2", "Player 2")
        return f"{p1}: {scores.get('Player 1', 0)}   |   {p2}: {scores.get('Player 2', 0)}"

    def _name_for(self, role: str) -> str:
        return self.player_names.get(role, role)

    def _update_score_labels(self, scores: dict) -> None:
        self.latest_scores = {
            "Player 1": scores.get("Player 1", 0),
            "Player 2": scores.get("Player 2", 0),
        }
        text = self._format_scores(self.latest_scores)
        self.waiting_score.setText(text)
        self.reveal_score.setText(text)
        self.question_score.setText(text)
        self.result_score.setText(f"Scoreboard - {text}")

    def _play_feedback_sound(self, kind: str) -> None:
        def _emit_sound() -> None:
            if winsound:
                try:
                    # Custom melodic patterns (avoid Windows error chime).
                    if kind == "correct":
                        pattern = [(740, 90), (880, 90), (1040, 130)]
                    elif kind == "wrong":
                        pattern = [(520, 90), (430, 120), (340, 160)]
                    else:  # timeout
                        pattern = [(660, 120), (660, 120), (420, 180)]

                    for freq, dur in pattern:
                        winsound.Beep(freq, dur)
                except RuntimeError:
                    print("\a", end="", flush=True)
            else:
                print("\a", end="", flush=True)

        threading.Thread(target=_emit_sound, daemon=True).start()

    def _show_category_reveal(self, msg: dict) -> None:
        self.player_names = msg.get("player_names", self.player_names)
        scores = msg.get("scores", self.latest_scores)
        self._update_score_labels(scores)
        round_text = msg.get("round_label") or f"{msg.get('round', '?')}/{msg.get('total_rounds', '?')}"
        suffix = " (Sudden Death)" if msg.get("is_tiebreaker") else ""
        self.reveal_round.setText(f"Round {round_text}{suffix}")
        self.reveal_category.setText(f"Next category: {msg.get('category', 'Unknown')}")
        self._switch_page(self.reveal_page)

    def _show_opponent_locked(self, payload: str) -> None:
        self.locked_notice.setText(payload or "Opponent locked in.")
        self.lock_notice_timer.start(1400)

    def _on_connect_clicked(self) -> None:
        name = self.name_input.text().strip() or "Anonymous"
        host = self.host_input.text().strip() or DEFAULT_HOST
        port_text = self.port_input.text().strip()

        try:
            port = int(port_text)
        except ValueError:
            self._show_dialog("Invalid Port", "Port must be an integer.", "warning")
            return

        self._cleanup_thread()
        self.game_over_received = False

        self.net_thread = NetworkClientThread(host=host, port=port, name=name)
        self.net_thread.message_received.connect(self._on_server_message)
        self.net_thread.connection_failed.connect(self._on_connection_failed)
        self.net_thread.disconnected.connect(self._on_disconnected)
        self.net_thread.start()

        self.waiting_status.setText(f"Connecting to {host}:{port}...")
        self.waiting_dots_timer.start()
        self._switch_page(self.waiting_page)

    def _on_connection_failed(self, reason: str) -> None:
        self.waiting_dots_timer.stop()
        self._show_dialog("Connection Failed", reason, "error")
        self._switch_page(self.connect_page)
        self._cleanup_thread()

    def _on_disconnected(self, reason: str) -> None:
        self.waiting_dots_timer.stop()
        if self.game_over_received:
            self._cleanup_thread()
            return
        self._show_dialog("Disconnected", reason, "info")
        self.tick_timer.stop()
        self._switch_page(self.connect_page)
        self._cleanup_thread()

    def _on_server_message(self, msg: dict) -> None:
        msg_type = msg.get("type")

        if msg_type == "WAITING":
            self._update_score_labels(msg.get("scores", self.latest_scores))
            self.waiting_status.setText(msg.get("payload", "Waiting for an opponent..."))
            self.waiting_dots_timer.start()
            self._switch_page(self.waiting_page)
            return

        if msg_type == "WELCOME":
            payload = msg.get("payload")
            if isinstance(payload, dict):
                self.my_role = payload.get("role")
                self.player_names = payload.get("player_names", self.player_names)
            else:
                self.my_role = payload
            self._update_score_labels(self.latest_scores)
            self.waiting_status.setText(f"Matched. You are {self._name_for(self.my_role or 'Player')}.")
            self.waiting_dots_timer.start()
            self._switch_page(self.waiting_page)
            return

        if msg_type == "CATEGORY_REVEAL":
            self.waiting_dots_timer.stop()
            self._show_category_reveal(msg)
            return

        if msg_type == "OPPONENT_LOCKED":
            self._show_opponent_locked(msg.get("payload", "Opponent locked in."))
            return

        if msg_type == "QUESTION":
            self._show_question(msg)
            return

        if msg_type == "ROUND_RESULT":
            self._show_round_result(msg)
            return

        if msg_type == "GAME_OVER":
            self._show_game_over(msg)
            return

    def _show_question(self, msg: dict) -> None:
        self.player_names = msg.get("player_names", self.player_names)
        scores = msg.get("scores", {})
        self._update_score_labels(scores)
        round_text = msg.get("round_label") or f"{msg.get('round', '?')}/{msg.get('total_rounds', '?')}"
        suffix = " (Sudden Death)" if msg.get("is_tiebreaker") else ""
        self.header_label.setText(f"Round {round_text}{suffix}")
        self.category_label.setText(f"Category: {msg.get('category', 'Unknown')}")
        self.role_label.setText(self._name_for(self.my_role or "Player"))
        self.question_label.setText(msg.get("question", ""))

        options = msg.get("options", [])
        for i, btn in enumerate(self.answer_buttons):
            text = options[i] if i < len(options) else f"{chr(65 + i)})"
            btn.setText(text)
            btn.setEnabled(True)

        self.current_timeout = float(msg.get("timeout", 15.0))
        self.deadline = time.monotonic() + self.current_timeout
        self.answer_submitted = False
        self.timer_bar.setRange(0, int(self.current_timeout * 10))
        self.timer_bar.setValue(int(self.current_timeout * 10))
        self.timer_label.setText(f"Time left: {self.current_timeout:.1f}s")
        self._set_timer_visual(self.current_timeout)
        self.question_hint.setText("Choose one option. Your first selection is final.")
        self.locked_notice.setText("")

        self.tick_timer.start()
        self.waiting_dots_timer.stop()
        self._switch_page(self.question_page)

    def _submit_answer(self, letter: str) -> None:
        if self.answer_submitted:
            return
        self.answer_submitted = True

        self.question_hint.setText(f"Submitted: {letter}. Waiting for round result...")
        for btn in self.answer_buttons:
            btn.setEnabled(False)

        if self.net_thread:
            self.net_thread.send_payload({"type": "ANSWER", "answer": letter})

    def _update_countdown(self) -> None:
        if self.answer_submitted:
            return

        remaining = max(0.0, self.deadline - time.monotonic())
        self.timer_label.setText(f"Time left: {remaining:.1f}s")
        self.timer_bar.setValue(int(remaining * 10))
        self._set_timer_visual(remaining)

        if remaining <= 0.001:
            self.answer_submitted = True
            self.question_hint.setText("Time is up. Waiting for round result...")
            for btn in self.answer_buttons:
                btn.setEnabled(False)
            if self.net_thread:
                self.net_thread.send_payload({"type": "ANSWER", "answer": ""})

    def _show_round_result(self, msg: dict) -> None:
        self.tick_timer.stop()
        self.player_names = msg.get("player_names", self.player_names)

        correct = msg.get("correct_answer")
        your_answer = msg.get("your_answer")
        was_correct = bool(msg.get("was_correct"))
        winner = msg.get("round_winner")
        scores = msg.get("scores", {})
        explanation = msg.get("explanation", "")
        self._update_score_labels(scores)

        if was_correct:
            self.result_main.setText(f"Correct. The answer was {correct}.")
            self._play_feedback_sound("correct")
        elif your_answer in (None, ""):
            self.result_main.setText(f"Time out. Correct answer: {correct}.")
            self._play_feedback_sound("timeout")
        else:
            self.result_main.setText(f"Incorrect. You answered {your_answer}. Correct answer: {correct}.")
            self._play_feedback_sound("wrong")

        if winner:
            self.result_extra.setText(f"Round point awarded to: {self._name_for(winner)}")
        else:
            self.result_extra.setText("No points awarded this round.")

        self.result_explanation.setText(f"Why: {explanation}" if explanation else "")

        self._switch_page(self.result_page)

    def _show_game_over(self, msg: dict) -> None:
        self.tick_timer.stop()
        self.waiting_dots_timer.stop()
        self.game_over_received = True
        self.player_names = msg.get("player_names", self.player_names)
        scores = msg.get("scores", {})
        self._update_score_labels(scores)
        winner = msg.get("winner", "Tie")

        if winner == "Tie":
            self.final_heading.setText("Stalemate")
            verdict = "Match tied after all rounds."
            self.final_result.setStyleSheet("color: #9b6117;")
        elif winner == self.my_role:
            self.final_heading.setText("Victory")
            verdict = "You win this match."
            self.final_result.setStyleSheet("color: #2f6d4a;")
        else:
            self.final_heading.setText("Defeat")
            verdict = "You lost this match."
            self.final_result.setStyleSheet("color: #922b21;")

        self.final_result.setText(verdict)
        self.final_scores.setText(
            f"{self._name_for('Player 1')}: {scores.get('Player 1', 0)}\n"
            f"{self._name_for('Player 2')}: {scores.get('Player 2', 0)}"
        )
        self._switch_page(self.game_over_page)

    def _reset_to_connect(self) -> None:
        self.tick_timer.stop()
        self.waiting_dots_timer.stop()
        self._cleanup_thread()
        self.my_role = None
        self.player_names = {"Player 1": "Player 1", "Player 2": "Player 2"}
        self.game_over_received = False
        self.final_heading.setText("Game Over")
        self.final_result.setStyleSheet("")
        self._switch_page(self.connect_page)

    def _cleanup_thread(self) -> None:
        if self.net_thread is None:
            return
        self.net_thread.close()
        self.net_thread.wait(1000)
        self.net_thread = None

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._cleanup_thread()
        super().closeEvent(event)


def main() -> None:
    app = QApplication([])
    app.setApplicationName("CMPT 371 Trivia Quiz")
    app.setFont(QFont("Trebuchet MS", 10))

    window = TriviaClientWindow()
    window.show()

    app.exec()


if __name__ == "__main__":
    main()
