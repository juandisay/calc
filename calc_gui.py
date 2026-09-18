#!/usr/bin/env python3
"""calc-gui — a PyQt6 GUI for calc, the safe full-precision calculator.

Run:
    .venv/bin/python calc_gui.py        (venv with PyQt6, see README)

The expression engine is the same single `calc` file the CLI uses — loaded
here as a module, so the GUI can never drift from the CLI behavior.
"""

from __future__ import annotations

import html
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QFont, QFontDatabase, QKeySequence, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

HERE = Path(__file__).resolve().parent

# ── engine: reuse the CLI calculator, no duplicated logic ──────────────────


def _calc_source() -> Path:
    """calc lives next to this file in dev; inside the bundle when frozen.

    PyInstaller's data placement changed across versions (Frameworks or
    Resources), and `--add-data "calc:calc_engine"` nests the file as
    `calc_engine/calc`. Probe the known spots, and accept a candidate only
    if it really is Python source — the frozen executable is also named
    `calc` and must never be mistaken for the engine.
    """
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        bundle = exe.parent.parent  # Contents/
        meipass = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else bundle
        for base in (meipass, bundle / "Resources"):
            for rel in ("calc_engine/calc", "calc_engine", "calc"):
                cand = base / rel
                if not cand.is_file():
                    continue
                try:
                    head = cand.read_text(encoding="utf-8", errors="strict")[:64]
                except (OSError, UnicodeDecodeError):
                    continue
                if head.lstrip().startswith("#"):
                    return cand
    return HERE / "calc"


def load_calc():
    loader = importlib.machinery.SourceFileLoader("calc", str(_calc_source()))
    spec = importlib.util.spec_from_loader("calc", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


calc = load_calc()

ERROR_COLOR = "#c62828"
RESULT_COLOR = "#111111"
MAX_HISTORY = 500

# ── widgets ────────────────────────────────────────────────────────────────


class InputLine(QLineEdit):
    """Expression entry with Up/Down history navigation."""

    def __init__(self, history: list[str], parent=None):
        super().__init__(parent)
        self._history = history
        self._index = -1
        self._draft = ""

    def remember(self, expr: str) -> None:
        if not self._history or self._history[-1] != expr:
            self._history.append(expr)
        self._index = -1

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Up and self._history:
            if self._index == -1:
                self._draft = self.text()
                self._index = len(self._history) - 1
            elif self._index > 0:
                self._index -= 1
            self.setText(self._history[self._index])
        elif key == Qt.Key.Key_Down and self._index != -1:
            self._index += 1
            if self._index < len(self._history):
                self.setText(self._history[self._index])
            else:
                self._index = -1
                self.setText(self._draft)
        elif key == Qt.Key.Key_Escape:
            self.clear()
            self._index = -1
        else:
            super().keyPressEvent(event)


class HelpDialog(QDialog):
    """Scrollable copy of the CLI help (calc.__doc__)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("calc — help")
        self.resize(640, 520)
        text = QPlainTextEdit(calc.__doc__ or "")
        text.setReadOnly(True)
        text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(12)
        text.setFont(font)
        layout = QVBoxLayout(self)
        layout.addWidget(text)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)


# ── main window ────────────────────────────────────────────────────────────


class CalcWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("calc — PyQt GUI")
        self.resize(860, 620)
        self.setMinimumSize(720, 520)

        self.env: dict = {"ans": None}
        self.input_history: list[str] = []
        self._help_dlg: HelpDialog | None = None

        self._build_ui()
        self._build_menu()
        self._build_pad()

        self.statusBar().showMessage(
            "Enter = evaluate · ↑/↓ = previous expressions · ans = last result · "
            "click history to reuse · double-click to re-run"
        )

    # UI ----------------------------------------------------------------

    def _build_ui(self):
        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        mono.setPointSize(14)

        self.input = InputLine(self.input_history)
        self.input.setPlaceholderText("2 + 3 * 4   —   full precision, see Help for functions")
        self.input.setFont(mono)
        self.input.returnPressed.connect(self.evaluate)

        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.display.setFont(mono)
        self.display.setMinimumHeight(96)
        self.display.setPlaceholderText("result")

        self.history = QListWidget()
        self.history.setToolTip("History — click to load, double-click to evaluate")
        self.history.itemClicked.connect(self._on_history_clicked)
        self.history.itemDoubleClicked.connect(self._on_history_double_clicked)

        clear_btn = QPushButton("Clear history")
        clear_btn.clicked.connect(self._clear_history)

        history_box = QVBoxLayout()
        history_box.addWidget(QLabel("History"))
        history_box.addWidget(self.history, 1)
        history_box.addWidget(clear_btn)
        history_widget = QWidget()
        history_widget.setLayout(history_box)

        pad_widget = QWidget()
        self.pad = QGridLayout(pad_widget)
        self.pad.setSpacing(6)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(pad_widget)
        self.splitter.addWidget(history_widget)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([540, 260])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.input)
        layout.addWidget(self.display, 1)
        layout.addWidget(self.splitter)
        self.setCentralWidget(central)

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("&File")
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(quit_action)

        help_menu = self.menuBar().addMenu("&Help")
        help_action = QAction("&Functions and operators", self)
        help_action.setShortcut(QKeySequence("Ctrl+/"))
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

    def _build_pad(self):
        # (label, inserted text, tooltip) — '' inserts nothing (action keys)
        basic = [
            ("C", "", "Clear the expression"),
            ("(", "(", None),
            (")", ")", None),
            ("⌫", "", "Delete last character"),
            ("7", "7", None),
            ("8", "8", None),
            ("9", "9", None),
            ("/", "/", None),
            ("4", "4", None),
            ("5", "5", None),
            ("6", "6", None),
            ("*", "*", None),
            ("1", "1", None),
            ("2", "2", None),
            ("3", "3", None),
            ("-", "-", None),
            ("0", "0", None),
            (".", ".", None),
            ("^", "^", "power — same as **"),
            ("+", "+", None),
            ("=", "", "Evaluate"),
        ]
        funcs = [
            ("sin(", "sin(", "sin(x)"),
            ("cos(", "cos(", "cos(x)"),
            ("tan(", "tan(", "tan(x)"),
            ("sqrt(", "sqrt(", "square root"),
            ("log(", "log(", "log base 10"),
            ("ln(", "ln(", "log base e"),
            ("exp(", "exp(", "e to the power of x"),
            ("abs(", "abs(", "absolute value"),
            ("round(", "round(", "round(x[, n])"),
            ("fact(", "fact(", "factorial"),
            ("min(", "min(", "minimum of arguments"),
            ("max(", "max(", "maximum of arguments"),
            ("sum(", "sum(", "sum of arguments"),
            ("mul(", "mul(", "product of arguments"),
            ("deg(", "deg(", "radians to degrees"),
            ("rad(", "rad(", "degrees to radians"),
            ("atan2(", "atan2(", "atan2(y, x)"),
            ("hypot(", "hypot(", "hypotenuse"),
            ("%", "%", "remainder"),
            ("//", "//", "floor division"),
            ("pi", "pi", "π"),
            ("e", "e", "Euler's number"),
            ("tau", "tau", "τ = 2π"),
            ("ans", "ans", "last result"),
        ]
        for row, (label, text, tip) in enumerate(basic):
            col = row % 4
            r = row // 4
            btn = QPushButton(label)
            btn.setMinimumHeight(40)
            if tip:
                btn.setToolTip(tip)
            if label == "=":
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: #1565c0; color: white; "
                    f"font-weight: bold; border-radius: 6px; padding: 4px; }}"
                    f"QPushButton:pressed {{ background-color: #0d47a1; }}"
                )
                btn.clicked.connect(self.evaluate)
            elif label == "C":
                btn.clicked.connect(self.input.clear)
            elif label == "⌫":
                btn.clicked.connect(self.input.backspace)
            else:
                btn.clicked.connect(lambda _=False, t=text: self.insert(t))
            self.pad.addWidget(btn, r, col)

        fn_box = QWidget()
        fn_grid = QGridLayout(fn_box)
        fn_grid.setSpacing(4)
        for i, (label, text, tip) in enumerate(funcs):
            btn = QPushButton(label)
            if tip:
                btn.setToolTip(tip)
            btn.clicked.connect(lambda _=False, t=text: self.insert(t))
            fn_grid.addWidget(btn, i // 6, i % 6)
        self.pad.addWidget(fn_box, 5, 0, 1, 4)

    # actions -----------------------------------------------------------

    def insert(self, text: str) -> None:
        self.input.insert(text)
        self.input.setFocus()

    def show_help(self) -> None:
        if self._help_dlg is None:
            self._help_dlg = HelpDialog(self)
        self._help_dlg.show()
        self._help_dlg.raise_()
        self._help_dlg.activateWindow()

    def evaluate(self) -> None:
        expr = self.input.text().strip()
        if not expr:
            return
        if expr == "help":
            self.show_help()
            return
        try:
            value = calc.evaluate(expr, self.env)
        except calc.CalcError as exc:
            self._show_error(str(exc))
            self._add_history(expr, None, str(exc))
            return
        self.env["ans"] = value
        text = calc.format_result(value)
        self.display.setPlainText(f"= {text}")
        self._add_history(expr, text, None)
        self.input.remember(expr)

    def _show_error(self, message: str) -> None:
        self.display.setHtml(
            f'<span style="color:{ERROR_COLOR}">error: {html.escape(message)}</span>'
        )

    def _add_history(self, expr: str, result: str | None, error: str | None) -> None:
        if result is not None:
            label = f"{expr} = {result}"
        else:
            label = f"{expr} → error: {error}"
        item = QListWidgetItem(label)
        if result is None:
            item.setForeground(QColor(ERROR_COLOR))
        self.history.insertItem(0, item)
        while self.history.count() > MAX_HISTORY:
            self.history.takeItem(self.history.count() - 1)

    def _on_history_clicked(self, item: QListWidgetItem) -> None:
        expr = self._expr_from_history(item.text())
        if expr is not None:
            self.input.setText(expr)
            self.input.setFocus()

    def _on_history_double_clicked(self, item: QListWidgetItem) -> None:
        expr = self._expr_from_history(item.text())
        if expr is not None:
            self.input.setText(expr)
            self.evaluate()

    @staticmethod
    def _expr_from_history(label: str) -> str | None:
        expr, sep, _ = label.partition(" = ")
        if not sep:
            expr = label.partition(" → error:")[0]
        return expr.strip() or None

    def _clear_history(self) -> None:
        self.history.clear()
        self.input_history.clear()
        self.input._index = -1
        self.input._draft = ""


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("calc-gui")
    if "--smoke" in sys.argv:
        # Headless bundle verification: "--smoke EXPR..." evaluates each
        # expression with the same engine/env as the GUI and prints results.
        exprs = sys.argv[sys.argv.index("--smoke") + 1 :]
        if not exprs:
            print("usage: --smoke EXPR...", file=sys.stderr)
            return 2
        win = CalcWindow()
        ok = True
        for expr in exprs:
            try:
                value = calc.evaluate(expr, win.env)
            except calc.CalcError as exc:
                print(f"error: {exc}")
                ok = False
            else:
                win.env["ans"] = value
                print(calc.format_result(value))
        return 0 if ok else 1
    win = CalcWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
