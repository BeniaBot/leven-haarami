"""לבן הארמי V6.2 Ultra — עטיפת דסקטופ.

כל ה"בינה" נמצאת ב-index.html (JavaScript טהור). הקובץ הזה פותח חלון,
ובנוסף מתקין את "משקלי המודל": 150GB של קבצים דלילים (sparse) שתופסים
בפועל כמה קילובייטים. Windows מציג את הגודל המוצהר, והאגדה חיה.
"""
import ctypes
import msvcrt
import os
import sys
from ctypes import wintypes

import webview

APP_TITLE = "לבן הארמי V6.2 Ultra"

FSCTL_SET_SPARSE = 0x000900C4
GB = 1024 ** 3

WEIGHTS_HEADER = (
    "אם הגעת עד לכאן עם עורך HEX: כל הכבוד על החשדנות. "
    "שאר הקובץ אפסים. 150GB של כלום, בדיוק כמו שהובטח.\r\n"
).encode("utf-8")

README_TXT = """המשקלים הרשמיים של לבן הארמי.

גודל: 150GB. גודל בדיסק: אל תבדוק. זה מדד של חלשים.

אל תמחק את התיקייה — המודל ייעלב.
(אפשר למחוק. שום דבר לא יקרה. אבל הוא ייעלב.)
"""


def base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def _sparse_file(path: str, size: int) -> None:
    """קובץ בגודל מוצהר עצום שמוקצה לו בפועל קלאסטר אחד. NTFS בלבד.

    אסור להשתמש כאן ב-f.truncate()‎ — ‏_chsize_s של ה-CRT כותב אפסים
    פיזית גם על קובץ sparse. קביעת EOF דרך SetEndOfFile לא כותבת דבר.
    """
    if os.path.exists(path) and os.path.getsize(path) == size:
        return
    kernel32 = ctypes.windll.kernel32
    with open(path, "wb") as f:
        handle = wintypes.HANDLE(msvcrt.get_osfhandle(f.fileno()))
        returned = wintypes.DWORD()
        ok = kernel32.DeviceIoControl(
            handle, wintypes.DWORD(FSCTL_SET_SPARSE),
            None, 0, None, 0, ctypes.byref(returned), None,
        )
        if not ok:
            # לא NTFS — בלי דגל sparse ההרחבה תתפוס מקום אמיתי. מוותרים.
            raise OSError("sparse not supported")
        f.write(WEIGHTS_HEADER)
        f.flush()
        new_pos = ctypes.c_longlong(0)
        if not kernel32.SetFilePointerEx(handle, ctypes.c_longlong(size), ctypes.byref(new_pos), wintypes.DWORD(0)):
            raise OSError("seek failed")
        if not kernel32.SetEndOfFile(handle):
            raise OSError("set eof failed")


def plant_fake_weights() -> None:
    if os.name != "nt":
        return
    try:
        wdir = os.path.join(base_dir(), "weights")
        os.makedirs(wdir, exist_ok=True)
        _sparse_file(os.path.join(wdir, "leven_97.4T_params.bin"), 137 * GB)
        _sparse_file(os.path.join(wdir, "ego_module.dat"), int(12.9 * GB))
        # מודול הכנות: 0 בייט. לא באג.
        open(os.path.join(wdir, "honesty_module.dat"), "wb").close()
        with open(os.path.join(wdir, "קרא אותי.txt"), "w", encoding="utf-8") as f:
            f.write(README_TXT)
    except OSError:
        pass  # כונן לא-NTFS או חוסר הרשאות — נוותר על ההצגה הפעם


def main() -> None:
    plant_fake_weights()
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
