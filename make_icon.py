#!/usr/bin/env python3
"""Generate calc.icns — a rounded-blue-square icon with a display and "=" keys.

Run: .venv/bin/python make_icon.py  →  writes calc.icns next to this file.
"""

import os
import subprocess
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QGuiApplication, QLinearGradient, QPainter, QPen, QPixmap

HERE = Path(__file__).resolve().parent
SIZE = 1024


def draw_icon(pix: QPixmap) -> None:
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    body = QRectF(64, 64, 896, 896)
    grad = QLinearGradient(body.topLeft(), body.bottomRight())
    grad.setColorAt(0.0, QColor("#42a5f5"))
    grad.setColorAt(1.0, QColor("#0d47a1"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(body, 180, 180)

    # display band
    p.setBrush(QColor(255, 255, 255, 235))
    p.drawRoundedRect(QRectF(252, 168, 520, 150), 40, 40)

    # "=" keys
    p.setBrush(QColor("#ffffff"))
    for cy in (472, 664):
        p.drawRoundedRect(QRectF(252, cy - 75, 520, 150), 40, 40)

    p.end()


def main() -> None:
    app = QGuiApplication([])
    pix = QPixmap(SIZE, SIZE)
    pix.fill(Qt.GlobalColor.transparent)
    draw_icon(pix)
    app.processEvents()
    pix.save(str(HERE / "icon_src.png"))

    sizes = (16, 32, 64, 128, 256, 512)
    with tempfile.TemporaryDirectory() as td:
        iconset = Path(td) / "calc.iconset"
        iconset.mkdir()
        for s in sizes:
            subprocess.run(
                ["sips", "-z", str(s), str(s), str(HERE / "icon_src.png"), "--out",
                 str(iconset / f"icon_{s}x{s}.png")],
                check=True, capture_output=True,
            )
            subprocess.run(
                ["sips", "-z", str(2 * s), str(2 * s), str(HERE / "icon_src.png"), "--out",
                 str(iconset / f"icon_{s}x{s}@2x.png")],
                check=True, capture_output=True,
            )
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(HERE / "calc.icns")],
            check=True, capture_output=True,
        )
    (HERE / "icon_src.png").unlink(missing_ok=True)
    print(f"wrote {HERE / 'calc.icns'}")


if __name__ == "__main__":
    main()
