# ============================================================
# Griffin Library - Quote Image Export
# ============================================================
# Render a saved quote as a polished PNG suitable for sharing.
# Supports Arabic, Persian, Hebrew (RTL) and CJK scripts
# (Chinese, Japanese, Korean) via Noto fonts with automatic
# script detection and fallback chain.
# ============================================================

import io
import unicodedata
import html
from typing import Optional


def safe(text) -> str:
    """Inline safe() — avoids cross-package import dependency."""
    return html.escape(str(text or ""))


# Color palettes (gradient backgrounds)
PALETTES = {
    "ink":    {"bg1": (15, 23, 42),    "bg2": (30, 41, 59),    "fg": (240, 244, 255), "accent": (124, 58, 237)},
    "rose":   {"bg1": (251, 232, 220), "bg2": (243, 213, 212), "fg": (60, 30, 30),    "accent": (180, 65, 80)},
    "sage":   {"bg1": (220, 232, 218), "bg2": (200, 220, 200), "fg": (30, 50, 30),    "accent": (60, 100, 60)},
    "ocean":  {"bg1": (218, 234, 246), "bg2": (188, 215, 235), "fg": (15, 35, 60),    "accent": (46, 109, 164)},
    "violet": {"bg1": (243, 240, 255), "bg2": (224, 215, 245), "fg": (40, 25, 70),    "accent": (124, 58, 237)},
}


# ─────────────────────────────────────────────────────────────
# Script detection
# ─────────────────────────────────────────────────────────────

def _detect_script(text: str) -> str:
    """
    Detect the dominant script in the text.
    Returns one of: 'arabic', 'hebrew', 'cjk', 'devanagari', 'latin'
    """
    counts = {"arabic": 0, "hebrew": 0, "cjk": 0, "devanagari": 0, "latin": 0}
    for ch in text:
        cp = ord(ch)
        if 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F or 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF:
            counts["arabic"] += 1
        elif 0x0590 <= cp <= 0x05FF:
            counts["hebrew"] += 1
        elif (0x4E00 <= cp <= 0x9FFF or 0x3040 <= cp <= 0x30FF or
              0xAC00 <= cp <= 0xD7AF or 0x3400 <= cp <= 0x4DBF):
            counts["cjk"] += 1
        elif 0x0900 <= cp <= 0x097F:
            counts["devanagari"] += 1
        elif ch.isalpha():
            counts["latin"] += 1

    return max(counts, key=counts.get)


def _is_rtl(script: str) -> bool:
    return script in ("arabic", "hebrew")


# ─────────────────────────────────────────────────────────────
# Font candidates per script
# ─────────────────────────────────────────────────────────────

def _font_candidates(script: str, bold: bool = False, size_hint: str = "body") -> list:
    """
    Return ordered font path candidates for the given script.
    Falls back to Noto Sans which covers most Unicode ranges.
    """
    weight = "Bold" if bold else "Regular"

    # Windows font paths
    WIN = "C:/Windows/Fonts"
    # Linux font paths (Streamlit cloud / Ubuntu)
    LIN_NOTO = "/usr/share/fonts/truetype/noto"
    LIN_DEJAVU = "/usr/share/fonts/truetype/dejavu"
    LIN_LIB = "/usr/share/fonts/truetype/liberation"
    # macOS
    MAC = "/System/Library/Fonts/Supplemental"
    MAC_SYS = "/System/Library/Fonts"

    if script == "arabic":
        return [
            # Noto Naskh - best for Arabic prose
            f"{LIN_NOTO}/NotoNaskhArabic-{weight}.ttf",
            f"{LIN_NOTO}/NotoSansArabic-{weight}.ttf",
            # Windows
            f"{WIN}/arial.ttf",
            f"{WIN}/tahoma.ttf",
            f"{WIN}/times.ttf",
            # macOS
            f"{MAC}/GeezaPro.ttc",
            # Fallback
            f"{LIN_NOTO}/NotoSans-{weight}.ttf",
        ]

    if script == "hebrew":
        return [
            f"{LIN_NOTO}/NotoSerifHebrew-{weight}.ttf",
            f"{LIN_NOTO}/NotoSansHebrew-{weight}.ttf",
            f"{WIN}/arial.ttf",
            f"{MAC}/Arial Hebrew.ttf",
            f"{LIN_NOTO}/NotoSans-{weight}.ttf",
        ]

    if script == "cjk":
        return [
            # Japanese / Korean / Chinese - Noto CJK covers all
            f"{LIN_NOTO}/NotoSerifCJK-{weight}.ttc",
            f"{LIN_NOTO}/NotoSansCJK-{weight}.ttc",
            f"{LIN_NOTO}/NotoSansCJKjp-{weight}.otf",
            # Windows CJK
            f"{WIN}/meiryo.ttc",        # Japanese
            f"{WIN}/malgun.ttf",        # Korean
            f"{WIN}/msyh.ttc",          # Chinese Simplified
            f"{WIN}/simsun.ttc",
            # macOS
            f"{MAC_SYS}/PingFang.ttc",
            f"{MAC_SYS}/Hiragino Sans GB.ttc",
            f"{LIN_NOTO}/NotoSans-{weight}.ttf",
        ]

    if script == "devanagari":
        return [
            f"{LIN_NOTO}/NotoSerifDevanagari-{weight}.ttf",
            f"{LIN_NOTO}/NotoSansDevanagari-{weight}.ttf",
            f"{WIN}/mangal.ttf",
            f"{LIN_NOTO}/NotoSans-{weight}.ttf",
        ]

    # Latin / default - serif for body, sans for meta
    if size_hint == "body":
        return [
            f"{MAC}/Georgia.ttf",
            f"{WIN}/georgia.ttf",
            f"{LIN_DEJAVU}/DejaVuSerif-Bold.ttf" if bold else f"{LIN_DEJAVU}/DejaVuSerif.ttf",
            f"{LIN_LIB}/LiberationSerif-{weight}.ttf",
            f"{LIN_NOTO}/NotoSerif-{weight}.ttf",
            f"{LIN_NOTO}/NotoSans-{weight}.ttf",
        ]
    else:
        return [
            f"{WIN}/arial.ttf",
            f"{LIN_DEJAVU}/DejaVuSans-Bold.ttf" if bold else f"{LIN_DEJAVU}/DejaVuSans.ttf",
            f"{LIN_LIB}/LiberationSans-{weight}.ttf",
            f"{LIN_NOTO}/NotoSans-{weight}.ttf",
        ]


def _load_font(candidates: list, size: int):
    from PIL import ImageFont
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────
# RTL text reshaping
# ─────────────────────────────────────────────────────────────

def _reshape_rtl(text: str) -> str:
    """
    Apply Arabic/Hebrew shaping and bidi reordering if libraries
    are available. Falls back to raw text if not installed.
    """
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        # Libraries not installed - text may look unjoined but won't crash
        try:
            from bidi.algorithm import get_display
            return get_display(text)
        except ImportError:
            return text


# ─────────────────────────────────────────────────────────────
# Text wrapping (width-aware)
# ─────────────────────────────────────────────────────────────

def _wrap_text(text: str, font, max_width: int, draw) -> list:
    """Wrap text to fit max_width given the font."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ─────────────────────────────────────────────────────────────
# Main render
# ─────────────────────────────────────────────────────────────

def render_quote_image(
    text: str,
    title: str = "",
    author: str = "",
    palette: str = "violet",
    width: int = 1080,
    height: int = 1080,
) -> bytes:
    """
    Render a quote as a square PNG (Instagram-ready 1080×1080).
    Automatically detects Arabic, Hebrew, CJK, Devanagari, Latin scripts
    and loads the appropriate font. RTL text is properly reshaped.

    Returns PNG bytes.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise RuntimeError("Pillow not installed; quote image export unavailable.")

    p = PALETTES.get(palette, PALETTES["violet"])

    # ── Detect script ──────────────────────────────────────
    script = _detect_script(text)
    rtl = _is_rtl(script)

    # ── Prepare text (RTL reshaping) ───────────────────────
    display_text = _reshape_rtl(text) if rtl else text.strip()
    if len(display_text) > 350:
        display_text = display_text[:347] + "…"

    # ── Background gradient ────────────────────────────────
    img = Image.new("RGB", (width, height), p["bg1"])
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        r = int(p["bg1"][0] * (1 - ratio) + p["bg2"][0] * ratio)
        g = int(p["bg1"][1] * (1 - ratio) + p["bg2"][1] * ratio)
        b = int(p["bg1"][2] * (1 - ratio) + p["bg2"][2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # ── Load fonts ─────────────────────────────────────────
    quote_font  = _load_font(_font_candidates(script, bold=False, size_hint="body"), size=52)
    meta_font   = _load_font(_font_candidates(script, bold=False, size_hint="meta"), size=24)
    accent_font = _load_font(_font_candidates("latin", bold=True,  size_hint="meta"), size=18)

    margin = 80
    max_width = width - 2 * margin

    # ── Decorative bar + wordmark ──────────────────────────
    bar_y = 140
    draw.rectangle([(80, bar_y), (200, bar_y + 4)], fill=p["accent"])
    draw.text((80, bar_y + 20), "GRIFFIN LIBRARY", font=accent_font, fill=p["accent"])

    # ── Wrap quote text ────────────────────────────────────
    wrapped = _wrap_text(display_text, quote_font, max_width, draw)

    line_height = quote_font.size + 16
    total_h = len(wrapped) * line_height
    start_y = (height - total_h) // 2 - 40

    # Opening quote mark (always LTR decorative)
    qmark_font = _load_font(_font_candidates("latin", bold=False, size_hint="body"), size=120)
    qmark_char = "\u201C" if not rtl else "\u201D"
    if rtl:
        draw.text((width - margin - 60, start_y - 80), qmark_char, font=qmark_font, fill=p["accent"])
    else:
        draw.text((margin - 10, start_y - 80), qmark_char, font=qmark_font, fill=p["accent"])

    # ── Draw each line ─────────────────────────────────────
    for i, line in enumerate(wrapped):
        y = start_y + i * line_height
        if rtl:
            # Right-align RTL text
            bbox = draw.textbbox((0, 0), line, font=quote_font)
            line_w = bbox[2] - bbox[0]
            x = width - margin - line_w
        else:
            x = margin
        draw.text((x, y), line, font=quote_font, fill=p["fg"])

    # ── Footer: title + author ─────────────────────────────
    footer_y = height - 140
    footer_script = _detect_script((title + " " + author).strip())
    footer_rtl = _is_rtl(footer_script)
    footer_font = _load_font(_font_candidates(footer_script, bold=False, size_hint="meta"), size=24)

    def _draw_footer_line(text_line: str, y: int, alpha: float = 1.0):
        if not text_line.strip():
            return
        display = _reshape_rtl(text_line) if footer_rtl else text_line
        color = tuple(int(c * alpha + 255 * (1 - alpha) * 0.3) for c in p["fg"])
        if footer_rtl:
            bbox = draw.textbbox((0, 0), display, font=footer_font)
            x = width - margin - (bbox[2] - bbox[0])
        else:
            x = margin
        draw.text((x, y), display, font=footer_font, fill=color)

    if title:
        _draw_footer_line(f"— {title}", footer_y, alpha=0.9)
    if author:
        _draw_footer_line(author, footer_y + 36, alpha=0.6)

    # ── Save to bytes ──────────────────────────────────────
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()