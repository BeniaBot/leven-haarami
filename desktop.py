"""לבן הארמי V6.3.1 Ultra — עטיפת דסקטופ.

הממשק והמנוע כולם ב-index.html. הקובץ הזה רק פותח חלון ומנקה שאריות.

הערה לדורות הבאים — למה אין כאן ניפוח עצמי של קובץ ההרצה:
נוסה ונכשל. אפשר להצהיר על קובץ ענק בעזרת קובץ דליל (sparse) של NTFS,
וכל עוד לא מריצים אותו הוא באמת תופס 14MB. אבל ברגע ש-Windows טוען
אותו כתמונת הרצה, החור מתמלא בפועל: נמדד 914MB תוך שניות מההפעלה,
1.8GB אחרי הסגירה, וכ-4GB בהמשך. קריאה רגילה מתוך החור לא מממשת אותו —
רק הרצה. בנוסף, Windows מסרב בכלל לטעון קובץ הרצה מעל 4GB.

המסקנה: קובץ שרץ לא יכול להעמיד פנים שהוא כבד. רק קובץ נתונים, שאיש
לא מריץ, נשאר דליל.
"""
import ctypes
import os
import shutil
import sys
import threading

import webview

APP_TITLE = "לבן הארמי V6.3 Ultra"
MOVEFILE_DELAY_UNTIL_REBOOT = 0x04

LEGACY_WEIGHTS = {
    "leven_97.4T_params.bin",
    "ego_module.dat",
    "honesty_module.dat",
    "קרא אותי.txt",
}

kernel32 = ctypes.windll.kernel32


def resource_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def _drop_leftovers(self_path: str) -> None:
    """מנקה את השאריות: העותק הקודם, ותיקיית weights של V6.2."""
    old = self_path + ".old"
    if os.path.exists(old):
        try:
            os.remove(old)
        except OSError:
            kernel32.MoveFileExW(old, None, MOVEFILE_DELAY_UNTIL_REBOOT)

    wdir = os.path.join(os.path.dirname(self_path), "weights")
    if os.path.isdir(wdir):
        try:
            # רק אם התיקייה מכילה בדיוק את מה שאנחנו יצרנו — לא נוגעים בזרים
            if set(os.listdir(wdir)) <= LEGACY_WEIGHTS:
                shutil.rmtree(wdir)
        except OSError:
            pass


def housekeeping() -> None:
    """ניקוי שאריות מגרסאות קודמות. רץ ברקע כדי לא לעכב את החלון."""
    if not getattr(sys, "frozen", False):
        return
    _drop_leftovers(sys.executable)


def main() -> None:
    if "--selftest" in sys.argv:
        print("ok")
        return

    threading.Thread(target=housekeeping, daemon=True).start()

    icon = resource_path("icon.ico")
    webview.create_window(
        APP_TITLE,
        url=resource_path("index.html"),
        width=1000,
        height=740,
        min_size=(420, 560),
        background_color="#0f0e0a",
    )
    webview.start(icon=icon if os.path.exists(icon) else None)


if __name__ == "__main__":
    main()
