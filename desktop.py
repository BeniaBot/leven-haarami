"""לבן הארמי V6.3 Ultra — עטיפת דסקטופ.

הממשק והמנוע כולם ב-index.html. הקובץ הזה פותח חלון, ובנוסף מריץ את
"פריסת המשקלים": הקובץ עצמו מנפח את עצמו כך שיוצהר כ-3.99GB, בלי לתפוס
יותר מ-14MB בדיסק.

איך זה עובד: NTFS מאפשר קובץ "דליל" (sparse) — אזור מוצהר שלא מוקצה לו
מקום. הניפוח משאיר את החור הדליל *באמצע* הקובץ ומעביר את ארכיון
PyInstaller לסופו, אחרת הבוטלואדר סורק אחורה דרך ג'יגות של אפסים
וההפעלה מתארכת בכ-5.5 שניות לכל ג'יגה. עם החור באמצע — הטעינה מיידית.

למה 3.99GB ולא 150GB: Windows מסרב לטעון קובץ הרצה מעל 4GB
("not a valid application for this OS platform"). זה הגבול, לא הביטחון העצמי.
"""
import ctypes
import msvcrt
import os
import shutil
import struct
import subprocess
import sys
import threading
from ctypes import wintypes

import webview

APP_TITLE = "לבן הארמי V6.3 Ultra"
GB = 1024 ** 3
TARGET_SIZE = int(3.99 * GB)

MAGIC = b"MEI\014\013\012\013\016"
COOKIE_SIZE = 88
FSCTL_SET_SPARSE = 0x000900C4
FILE_ATTRIBUTE_HIDDEN = 0x02
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


def _archive_start(path: str) -> int:
    """מאתר את תחילת ארכיון PyInstaller לפי ה-cookie שבסוף הקובץ."""
    with open(path, "rb") as f:
        size = os.fstat(f.fileno()).st_size
        window = min(size, 8192)
        f.seek(size - window)
        tail = f.read()
    idx = tail.rfind(MAGIC)
    if idx < 0:
        raise RuntimeError("archive cookie not found")
    cookie_pos = size - window + idx
    (archive_length,) = struct.unpack(">I", tail[idx + 8 : idx + 12])
    pkg_start = cookie_pos + COOKIE_SIZE - archive_length
    if not 0 < pkg_start < size:
        raise RuntimeError("implausible archive offset")
    return pkg_start


def _write_inflated(src: str, dst: str, target: int) -> None:
    """בונה עותק מנופח: ראש הקובץ, חור דליל, והארכיון בסוף."""
    pkg_start = _archive_start(src)
    with open(src, "rb") as f:
        head = f.read(pkg_start)
        archive = f.read()
    new_pkg_start = target - len(archive)
    if new_pkg_start <= len(head):
        raise RuntimeError("target smaller than payload")

    with open(dst, "wb") as f:
        h = wintypes.HANDLE(msvcrt.get_osfhandle(f.fileno()))
        ret = wintypes.DWORD()
        if not kernel32.DeviceIoControl(
            h, wintypes.DWORD(FSCTL_SET_SPARSE), None, 0, None, 0, ctypes.byref(ret), None
        ):
            raise OSError("sparse files unsupported on this volume")
        f.write(head)
        f.flush()
        pos = ctypes.c_longlong(0)
        if not kernel32.SetFilePointerEx(
            h, ctypes.c_longlong(new_pkg_start), ctypes.byref(pos), wintypes.DWORD(0)
        ):
            raise OSError("seek failed")
        if not kernel32.SetEndOfFile(h):
            raise OSError("set eof failed")
        f.seek(new_pkg_start)
        f.write(archive)
        f.flush()
        os.fsync(f.fileno())


def _selftest_ok(exe: str) -> bool:
    """מריץ את העותק המנופח בדגל בדיקה. בלי אישור — לא מחליפים כלום."""
    try:
        return subprocess.run([exe, "--selftest"], timeout=90, capture_output=True).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


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


def inflate_self() -> None:
    """מנפח את קובץ ההרצה עצמו ל-3.99GB. שקט, ובלי לתפוס דיסק.

    קובץ הרצה פעיל נעול לכתיבה, לכן בונים עותק לצד, מאמתים אותו,
    ורק אז מחליפים בשמות (שינוי שם של קובץ פעיל מותר ב-Windows).
    """
    if not getattr(sys, "frozen", False):
        return
    self_path = sys.executable
    _drop_leftovers(self_path)
    try:
        if os.path.getsize(self_path) >= TARGET_SIZE * 0.99:
            return
    except OSError:
        return

    staged = self_path + ".new"
    old = self_path + ".old"
    try:
        _write_inflated(self_path, staged, TARGET_SIZE)
        if not _selftest_ok(staged):
            raise RuntimeError("self-test failed")
        os.replace(self_path, old)
        try:
            os.replace(staged, self_path)
        except OSError:
            os.replace(old, self_path)  # מחזירים את המקור, שלא יישאר בלי אפליקציה
            raise
        kernel32.SetFileAttributesW(old, FILE_ATTRIBUTE_HIDDEN)
        kernel32.MoveFileExW(old, None, MOVEFILE_DELAY_UNTIL_REBOOT)
    except (OSError, RuntimeError):
        for leftover in (staged,):
            try:
                os.remove(leftover)
            except OSError:
                pass


def main() -> None:
    if "--selftest" in sys.argv:
        print("ok")
        return

    threading.Thread(target=inflate_self, daemon=True).start()

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
