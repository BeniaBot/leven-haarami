"""לבן הארמי V6.1 Ultra — עטיפת דסקטופ.

כל ה"בינה" נמצאת ב-index.html (JavaScript טהור). הקובץ הזה רק פותח חלון.
17 מגהבייט של EXE בשביל זה — וזה, כידוע, חלק מהבדיחה.
"""
import os
import sys

import webview

APP_TITLE = "לבן הארמי V6.1 Ultra"


def resource_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def main() -> None:
    webview.create_window(
        APP_TITLE,
        url=resource_path("index.html"),
        width=1000,
        height=740,
        min_size=(420, 560),
    )
    webview.start()


if __name__ == "__main__":
    main()
