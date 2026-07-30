"""לבן הארמי V6.4 Ultra — עטיפת דסקטופ.

הממשק והמנוע כולם ב-index.html. הקובץ הזה פותח חלון, ובנוסף פורס את
"משקלי המודל": תיקייה שמוצהרת כ-150GB ותופסת בפועל פחות ממגהבייט.

איך: NTFS תומך בקבצים דלילים (sparse) — טווח מוצהר שלא מוקצה לו מקום.
נמדד: קובץ מוצהר של 137GB הקצה 0.1MB, ושרד שעה על הדיסק בלי לגדול.

מה שלא עובד, ואסור לנסות שוב: לנפח כך את קובץ ההרצה עצמו. ראשית,
Windows מסרב לטעון קובץ הרצה מעל 4GB ("not a valid application for this
OS platform"). שנית, וגרוע יותר, החור בקובץ שרץ התמלא בפועל ואכל ארבעה
ג'יגה אמיתיים (נמדד: 914MB תוך שניות, 1.8GB אחרי סגירה, ~4GB בהמשך).
זה מה שקרה ב-V6.3, ולכן היא נמשכה. קובצי נתונים בלבד.
"""
import ctypes
import msvcrt
import os
import shutil
import sys
import threading
from ctypes import wintypes

import webview

APP_TITLE = "לבן הארמי V6.4 Ultra"
GB = 1024 ** 3
MOVEFILE_DELAY_UNTIL_REBOOT = 0x04
FSCTL_SET_SPARSE = 0x000900C4
FSCTL_QUERY_ALLOCATED_RANGES = 0x000940CF

WEIGHTS_DIR = "model"
# סך הכל 150GB מוצהרים. השמות רציניים לגמרי, וזה בדיוק העניין.
WEIGHT_FILES = (
    ("leven-97.4T-q0.safetensors", 131 * GB),
    ("ego-adapter.safetensors", 18 * GB),
    ("tokenizer.model", 1 * GB),
    ("honesty-head.safetensors", 0),  # מודול הכנות. 0 בייט. לא באג.
)
LEGACY_WEIGHTS = {
    "leven_97.4T_params.bin",
    "ego_module.dat",
    "honesty_module.dat",
    "קרא אותי.txt",
}
MAX_REAL_BYTES = 64 * 1024 * 1024  # מעל זה משהו השתבש והמשקלים נמחקים

HEADER = (
    "אם הגעת עד לכאן עם עורך HEX: כל הכבוד על החשדנות. שאר הקובץ אפסים.\r\n"
    "150 ג'יגה של כלום, בדיוק כפי שהובטח בעמוד המוצר.\r\n"
).encode("utf-8")

CONFIG_JSON = """{
  "model_type": "leven",
  "parameters": 97400000000000,
  "quantization": "q0",
  "context_length": 1000000,
  "attention": "none",
  "comment": "אין כאן מודל. יש כאן קובץ JSON שנראה כמו הגדרות של מודל."
}
"""

README_TXT = """משקלי המודל הרשמיים של לבן הארמי.

גודל: 150GB. גודל בדיסק: אל תבדוק. זה מדד של חלשים.

אל תמחק את התיקייה — המודל ייעלב.
(אפשר למחוק. שום דבר לא יקרה. אבל הוא ייעלב.)
"""

kernel32 = ctypes.windll.kernel32


class _Range(ctypes.Structure):
    _fields_ = [("FileOffset", ctypes.c_longlong), ("Length", ctypes.c_longlong)]


def resource_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _allocated_bytes(path: str) -> int:
    """כמה מקום הקובץ באמת תופס. AllocationSize משקר על קבצים דלילים."""
    handle = kernel32.CreateFileW(ctypes.c_wchar_p(path), 0x80000000, 0x07, None, 3, 0x80, None)
    if handle == -1:
        return -1
    try:
        query = _Range(0, os.path.getsize(path))
        buf = (_Range * 1024)()
        returned = wintypes.DWORD()
        ok = kernel32.DeviceIoControl(
            wintypes.HANDLE(handle), wintypes.DWORD(FSCTL_QUERY_ALLOCATED_RANGES),
            ctypes.byref(query), ctypes.sizeof(query), ctypes.byref(buf), ctypes.sizeof(buf),
            ctypes.byref(returned), None,
        )
        if not ok:
            return -1
        count = returned.value // ctypes.sizeof(_Range)
        return sum(buf[i].Length for i in range(count))
    finally:
        kernel32.CloseHandle(wintypes.HANDLE(handle))


def _sparse_file(path: str, size: int) -> None:
    """קובץ בגודל מוצהר עצום שמוקצה לו בפועל קלאסטר אחד. NTFS בלבד.

    אסור להשתמש כאן ב-f.truncate()‎ — ‏_chsize_s של ה-CRT כותב אפסים
    פיזית גם על קובץ דליל. קביעת EOF דרך SetEndOfFile לא כותבת דבר.
    """
    if os.path.exists(path) and os.path.getsize(path) == size:
        return
    with open(path, "w+b") as f:
        handle = wintypes.HANDLE(msvcrt.get_osfhandle(f.fileno()))
        returned = wintypes.DWORD()
        if not kernel32.DeviceIoControl(
            handle, wintypes.DWORD(FSCTL_SET_SPARSE), None, 0, None, 0, ctypes.byref(returned), None
        ):
            raise OSError("sparse files unsupported on this volume")
        if size > len(HEADER):
            f.write(HEADER)
            f.flush()
        pos = ctypes.c_longlong(0)
        if not kernel32.SetFilePointerEx(
            handle, ctypes.c_longlong(size), ctypes.byref(pos), wintypes.DWORD(0)
        ):
            raise OSError("seek failed")
        if not kernel32.SetEndOfFile(handle):
            raise OSError("set eof failed")


def deploy_weights() -> None:
    """פורס את תיקיית המשקלים, ומוודא שהיא באמת לא תופסת מקום."""
    if os.name != "nt":
        return
    wdir = os.path.join(base_dir(), WEIGHTS_DIR)
    try:
        os.makedirs(wdir, exist_ok=True)
        for name, size in WEIGHT_FILES:
            _sparse_file(os.path.join(wdir, name), size)
        with open(os.path.join(wdir, "config.json"), "w", encoding="utf-8") as f:
            f.write(CONFIG_JSON)
        with open(os.path.join(wdir, "קרא אותי.txt"), "w", encoding="utf-8") as f:
            f.write(README_TXT)
    except OSError:
        # כונן לא-NTFS, אין הרשאות, אין מקום — מוותרים בשקט על ההצגה
        shutil.rmtree(wdir, ignore_errors=True)
        return

    # רשת ביטחון: אם בכל זאת הוקצה מקום אמיתי, מוחקים ולא מתווכחים
    real = 0
    for name, _ in WEIGHT_FILES:
        got = _allocated_bytes(os.path.join(wdir, name))
        if got < 0:
            shutil.rmtree(wdir, ignore_errors=True)
            return
        real += got
    if real > MAX_REAL_BYTES:
        shutil.rmtree(wdir, ignore_errors=True)


def _drop_leftovers(self_path: str) -> None:
    """מנקה שאריות: העותק המנופח של V6.3 ותיקיית weights של V6.2."""
    old = self_path + ".old"
    if os.path.exists(old):
        try:
            os.remove(old)
        except OSError:
            kernel32.MoveFileExW(old, None, MOVEFILE_DELAY_UNTIL_REBOOT)

    legacy = os.path.join(os.path.dirname(self_path), "weights")
    if os.path.isdir(legacy):
        try:
            # רק אם התיקייה מכילה בדיוק את מה שאנחנו יצרנו — לא נוגעים בזרים
            if set(os.listdir(legacy)) <= LEGACY_WEIGHTS:
                shutil.rmtree(legacy)
        except OSError:
            pass


def housekeeping() -> None:
    """רץ ברקע כדי לא לעכב את החלון."""
    if getattr(sys, "frozen", False):
        _drop_leftovers(sys.executable)
    deploy_weights()


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
