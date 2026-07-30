"""יוצר את הלוגו הרשמי של לבן הארמי: סמל האיל, בזהב מטאלי.

שתי קרניים ספירליות היוצאות מצומת מרכזי — צורה שנקראת גם ב-16 פיקסל
בשורת המשימות, וגם ב-256 כשיש מקום לפרטים.

מריצים פעם אחת ומקבלים icon.ico (כל הגדלים) + logo.png לתיעוד.
דורש Pillow. ההרצה לא נדרשת לבנייה — הקבצים כבר במאגר.
"""
import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 1024
BG_TOP = (30, 25, 15)
BG_BOTTOM = (11, 10, 7)
GLOW = (96, 70, 20)
GOLD_TOP = (250, 226, 162)
GOLD_MID = (216, 168, 64)
GOLD_BOTTOM = (146, 102, 26)
NODE = (255, 243, 210)


def vertical_gradient(size, stops):
    """מעבר צבע אנכי לפי נקודות עיגון — נותן לזהב מראה מטאלי."""
    w, h = size
    strip = Image.new("RGB", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / max(1, h - 1)
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                k = (t - t0) / max(1e-6, t1 - t0)
                px[0, y] = tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
                break
    return strip.resize((w, h), Image.BILINEAR)


def bezier(p0, p1, p2, p3, steps=200):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0]
        y = u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]
        pts.append((x, y))
    return pts


def taper(path, w_start, w_end, ease=0.75):
    """הופך קו מרכזי למצולע מתעבה-מתחדד, כדי שהקרן תיראה מסותתת."""
    left, right = [], []
    n = len(path)
    for i, (x, y) in enumerate(path):
        t = i / (n - 1)
        w = w_start + (w_end - w_start) * (t ** ease)
        j, k = min(i + 1, n - 1), max(i - 1, 0)
        dx, dy = path[j][0] - path[k][0], path[j][1] - path[k][1]
        norm = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / norm, dx / norm
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    return left + right[::-1]


def horn_path(cx, cy, sign):
    """קרן איל: עולה מהצומת, מתעגלת מעל, ומתחדדת בקצה כלפי חוץ-מטה."""
    return bezier(
        (cx + sign * S * 0.012, cy + S * 0.085),
        (cx + sign * S * 0.055, cy - S * 0.215),
        (cx + sign * S * 0.365, cy - S * 0.230),
        (cx + sign * S * 0.315, cy + S * 0.115),
    )


def tip_curl(path, sign):
    """סלסול פנימי בקצה הקרן — הפרט שהופך צורה גנרית לקרן איל."""
    end = path[-1]
    return bezier(
        end,
        (end[0] + sign * S * 0.028, end[1] + S * 0.088),
        (end[0] - sign * S * 0.070, end[1] + S * 0.112),
        (end[0] - sign * S * 0.082, end[1] + S * 0.030),
        steps=110,
    )


def build_variant(detailed=True, bold=1.0):
    cx, cy = S * 0.5, S * 0.50

    shape = Image.new("L", (S, S), 0)
    sd = ImageDraw.Draw(shape)
    horns = []
    for sign in (-1, 1):
        path = horn_path(cx, cy, sign)
        w_join = S * 0.040 * bold
        sd.polygon(taper(path, S * 0.098 * bold, w_join), fill=255)
        curl = tip_curl(path, sign)
        sd.polygon(taper(curl, w_join, S * 0.016 * bold), fill=255)
        # עיגול במפגש בין הקרן לסלסול, שלא ייראה שם מדרגה
        jx, jy = path[-1]
        sd.ellipse([jx - w_join / 2, jy - w_join / 2, jx + w_join / 2, jy + w_join / 2], fill=255)
        horns.append((path, curl))

    # חוטם מרכזי: מתחדד כלפי מטה, כך שהסמל נקרא כראש ולא כמנעול
    muzzle_top, muzzle_bottom = cy + S * 0.010, cy + S * 0.225
    w_top, w_bottom = S * 0.105 * bold, S * 0.052 * bold
    sd.polygon(
        [
            (cx - w_top / 2, muzzle_top),
            (cx + w_top / 2, muzzle_top),
            (cx + w_bottom / 2, muzzle_bottom),
            (cx - w_bottom / 2, muzzle_bottom),
        ],
        fill=255,
    )
    sd.ellipse(
        [cx - w_bottom / 2, muzzle_bottom - w_bottom / 2, cx + w_bottom / 2, muzzle_bottom + w_bottom / 2],
        fill=255,
    )

    # רקע: אריח כהה עם זוהר רדיאלי
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bg = vertical_gradient((S, S), [(0.0, BG_TOP), (1.0, BG_BOTTOM)])
    glow = Image.new("L", (S, S), 0)
    gd = ImageDraw.Draw(glow)
    for i in range(30):
        t = i / 29
        rad = S * 0.46 * (1 - t * 0.80)
        gd.ellipse([cx - rad, cy - rad * 0.88, cx + rad, cy + rad * 0.88], fill=int(8 + t * 30))
    bg.paste(Image.new("RGB", (S, S), GLOW), (0, 0), glow.filter(ImageFilter.GaussianBlur(S * 0.06)))
    canvas.paste(bg, (0, 0))

    # צל רך, שהזהב לא ידבק לרקע
    shadow = shape.filter(ImageFilter.GaussianBlur(S * 0.020)).point(lambda v: int(v * 0.6))
    canvas.paste(Image.new("RGB", (S, S), (0, 0, 0)), (int(S * 0.008), int(S * 0.014)), shadow)

    gold = vertical_gradient((S, S), [(0.0, GOLD_TOP), (0.45, GOLD_MID), (1.0, GOLD_BOTTOM)])
    canvas.paste(gold, (0, 0), shape)

    # נצנוץ פנימי — מצויר על שכבה נפרדת ומוטמע דרך מסכת הצורה,
    # כדי שלא יגלוש אל הרקע ויותיר שיירים
    sheen = Image.new("L", (S, S), 0)
    shd = ImageDraw.Draw(sheen)
    for path, _ in horns:
        rim = [(x, y - S * 0.026) for x, y in path[14 : int(len(path) * 0.66)]]
        shd.line(rim, fill=120, width=int(S * 0.014), joint="curve")
    sheen = ImageChops.multiply(sheen, shape)
    canvas.paste(Image.new("RGB", (S, S), GOLD_TOP), (0, 0), sheen)

    art = ImageDraw.Draw(canvas)
    if detailed:
        # צמתי רשת: אחד במרכז, ואחד בתוך כל סלסול. לא מחוברים לכלום, כמסורת.
        r_mid = S * 0.026
        art.ellipse(
            [cx - r_mid, cy + S * 0.048 - r_mid, cx + r_mid, cy + S * 0.048 + r_mid],
            fill=NODE,
            outline=GOLD_BOTTOM,
            width=int(S * 0.006),
        )
        for _, curl in horns:
            tip = curl[-1]
            r = S * 0.017
            art.ellipse([tip[0] - r, tip[1] - r, tip[0] + r, tip[1] + r], fill=NODE)

    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.21), fill=255)
    canvas.putalpha(mask)
    return canvas


def variant_for(size, detailed, simple, tiny):
    """שלוש דרגות: מפורט לגדול, מפושט לבינוני, ומודגש מאוד לשורת המשימות."""
    if size >= 48:
        return detailed
    return simple if size >= 32 else tiny


def build():
    detailed = build_variant(detailed=True)
    simple = build_variant(detailed=False, bold=1.16)
    tiny = build_variant(detailed=False, bold=1.38)
    detailed.save("logo.png")

    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    frames = [variant_for(n, detailed, simple, tiny).resize((n, n), Image.LANCZOS) for n in sizes]
    frames[-1].save("icon.ico", format="ICO", sizes=[(n, n) for n in sizes], append_images=frames[:-1])

    # רצועת בדיקה: איך הסמל נראה בגדלים האמיתיים של שורת המשימות
    strip = Image.new("RGBA", (16 + 20 + 24 + 32 + 48 + 64 + 70, 80), (24, 22, 18, 255))
    x = 8
    for n in (16, 20, 24, 32, 48, 64):
        strip.alpha_composite((simple if n < 48 else detailed).resize((n, n), Image.LANCZOS), (x, 40 - n // 2))
        x += n + 10
    strip.resize((strip.width * 2, strip.height * 2), Image.NEAREST).save("icon-preview.png")
    print("wrote logo.png, icon.ico, icon-preview.png", sizes)


if __name__ == "__main__":
    build()
