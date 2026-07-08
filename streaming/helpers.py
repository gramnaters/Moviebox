import re
from urllib.parse import urlparse

FILE_EXT_PATTERN = re.compile(r".+\.(\w+)\?.+")

# Maps MovieBox link_type int -> display format
LINK_TYPE_FORMAT = {
    0: "MP4",
    1: "MP4",
    2: "DASH",
    3: "HLS",
}

# Normalises raw codecName strings (hevc, h265, x265, ...) -> "H.265" / "H.264" / etc.
CODEC_ALIASES = {
    "hevc": "H.265", "h265": "H.265", "h.265": "H.265", "x265": "H.265",
    "avc": "H.264", "h264": "H.264", "h.264": "H.264", "x264": "H.264",
    "av1": "AV1", "vp9": "VP9",
}

# ISO 2-letter -> flag emoji for the badges/compact layouts.
LANG_FLAG = {
    "EN": "🇬🇧", "HI": "🇮🇳", "TA": "🇮🇳", "TE": "🇮🇳", "MA": "🇮🇳",
    "KA": "🇮🇳", "BN": "🇧🇩", "ES": "🇪🇸", "FR": "🇫🇷", "DE": "🇩🇪",
    "JA": "🇯🇵", "KO": "🇰🇷", "ZH": "🇨🇳", "AR": "🇸🇦", "RU": "🇷🇺",
    "PT": "🇵🇹", "IT": "🇮🇹", "TR": "🇹🇷", "NL": "🇳🇱", "PL": "🇵🇱",
    "ID": "🇮🇩", "TH": "🇹🇭", "VI": "🇻🇳", "MS": "🇲🇾", "FA": "🇮🇷",
}


# ---------------------------------------------------------------------------
# Primitive formatters
# ---------------------------------------------------------------------------

def _format_size(size: int) -> str:
    """Format byte size into human-readable string. 1009 MB / 1.90 GB."""
    size_mb = size // 1024 // 1024
    if size_mb >= 1024:
        return f"{size_mb / 1024:.2f} GB"
    return f"{size_mb} MB"


def _format_resolution(resolution: int) -> str:
    """Format resolution into display string."""
    if resolution >= 2160:
        return "4K"
    elif resolution >= 1080:
        return "1080p"
    elif resolution >= 720:
        return "720p"
    else:
        return f"{resolution}p"


def _short_codec(codec: str | None) -> str | None:
    """H.265 -> HEVC, H.264 -> AVC, otherwise pass through."""
    if not codec:
        return None
    return {"H.265": "HEVC", "H.264": "AVC"}.get(codec, codec)


def _lang_with_flag(lang: str) -> str:
    """'Hindi' -> 'HI 🇮🇳', 'English' -> 'EN 🇬🇧'."""
    short = lang.strip().title()
    iso = short[:2].upper()
    flag = LANG_FLAG.get(iso)
    return f"{iso} {flag}" if flag else short


def normalize_codec(raw: str | None) -> str | None:
    """Normalise a raw codecName string into 'H.265' / 'H.264' / 'AV1' / 'VP9'.

    Returns None if the codec is unknown or empty — caller should then omit
    the codec line rather than display garbage.
    """
    if not raw:
        return None
    key = raw.strip().lower().replace("-", "")
    return CODEC_ALIASES.get(key) or (raw.strip().upper() if raw.strip() else None)


def infer_format_from_url(url: str) -> str | None:
    """Infer a display format (MP4 / MKV / WEBM / DASH / HLS) from a stream URL.

    Used as a fallback for v1/v2 web streams where the download API doesn't
    return a `linkType`. DASH/HLS are detected from .mpd / .m3u8 in the path.
    """
    if not url:
        return None
    path = urlparse(str(url)).path.lower()
    if path.endswith(".mpd"):
        return "DASH"
    if path.endswith(".m3u8"):
        return "HLS"
    for ext in (".mp4", ".mkv", ".webm", ".mov", ".m4v", ".ts", ".avi"):
        if path.endswith(ext):
            return ext.lstrip(".").upper()
    return None


def format_link_type(link_type: int | None) -> str | None:
    """Map MovieBox v3 linkType int -> display format string."""
    if link_type is None:
        return None
    return LINK_TYPE_FORMAT.get(int(link_type))


# ---------------------------------------------------------------------------
# Layout renderers — one per option in the addon's layout selector.
#
# All three receive the same metadata payload; each composes a distinct
# visual identity. Each layout surfaces the FULL PenguPlay field set:
# title, resolution+codec+format, source, size, audio lang, subtitles.
# The `name` field on the Stremio stream object is "MovieBox" (left-side
# label); we still repeat "Source: MovieBox" inside the title for parity
# with Pengu's output.
# ---------------------------------------------------------------------------

def render_cinematic(
    title: str | None,
    resolution: int,
    size: int,
    codec: str | None,
    fmt: str | None,
    audio_langs: list[str] | None,
    subtitle_langs: list[str] | None,
) -> str:
    """Cinematic (Clean) — default.

    Multi-line, airy, emoji-led. Mirrors Pengu's full field set:
    title, tech row (res + codec + format), source, size, audio, subs.
    DASH/HLS streams are marked 'adaptive' on the resolution, matching
    PenguPlay's display ('1080p adaptive • H.265 • DASH').

        🍿 The Shawshank Redemption [Hindi]
        🎞️ 1080p adaptive • H.265 • DASH
        🛰️ Source: MovieBox
        💾 1.49 GB
        🎧 Audio: Hindi
        💬 English, Hindi Subs
    """
    res_str = _format_resolution(resolution)
    size_str = _format_size(size)

    lines = []
    if title:
        lines.append(f"🍿 {title}")

    # PenguPlay marks DASH/HLS streams as 'adaptive' on the resolution.
    res_display = f"{res_str} adaptive" if fmt in ("DASH", "HLS") else res_str
    film_parts = [res_display]
    if codec:
        film_parts.append(codec)
    if fmt:
        film_parts.append(fmt)
    lines.append("🎞️ " + " • ".join(film_parts))

    lines.append("🛰️ Source: MovieBox")
    lines.append(f"💾 {size_str}")

    if audio_langs:
        lines.append(f"🎧 Audio: {', '.join(audio_langs)}")

    if subtitle_langs:
        sub_str = ", ".join(subtitle_langs[:5])
        if len(subtitle_langs) > 5:
            sub_str += f" +{len(subtitle_langs) - 5}"
        lines.append(f"💬 {sub_str} Subs")

    return "\n".join(lines)


def render_compact(
    title: str | None,
    resolution: int,
    size: int,
    codec: str | None,
    fmt: str | None,
    audio_langs: list[str] | None,
    subtitle_langs: list[str] | None,
) -> str:
    """Compact (Torrentio Style) — dense single line, pipe-separated.

    Includes the same field set as cinematic, just flattened:

        The Shawshank Redemption [Hindi] | 1080p | H.265 | MP4 | MovieBox | 1.49 GB | HINDI | EN+HI subs
    """
    res_str = _format_resolution(resolution)
    size_str = _format_size(size)

    parts = []
    if title:
        parts.append(title)

    parts.append(res_str)
    if codec:
        parts.append(codec)
    if fmt:
        parts.append(fmt)
    parts.append("MovieBox")
    parts.append(size_str)

    if audio_langs:
        parts.append(", ".join(a.upper() for a in audio_langs))

    if subtitle_langs:
        sub_str = "+".join(s[:2].upper() for s in subtitle_langs[:4])
        if len(subtitle_langs) > 4:
            sub_str += f"+{len(subtitle_langs) - 4}"
        parts.append(f"{sub_str} subs")

    return " | ".join(parts)


def render_badges(
    title: str | None,
    resolution: int,
    size: int,
    codec: str | None,
    fmt: str | None,
    audio_langs: list[str] | None,
    subtitle_langs: list[str] | None,
) -> str:
    """Badges (Technical) — power-user view.

    Title row, source row, bracketed badge row (mirrors Pengu's second line),
    then a compact audio+subs footer.

        🍿 The Shawshank Redemption [Hindi]
        🛰️ Source: MovieBox
        [1080p] [HEVC] [MP4] [1.49 GB] [HI 🇮🇳]
        🎧 Audio: Hindi • 💬 English, Hindi
    """
    res_str = _format_resolution(resolution)
    size_str = _format_size(size)

    lines = []
    if title:
        lines.append(f"🍿 {title}")

    lines.append("🛰️ Source: MovieBox")

    badges = [res_str]
    if codec:
        badges.append(_short_codec(codec))
    if fmt:
        badges.append(fmt)
    badges.append(size_str)
    if audio_langs:
        for lang in audio_langs[:2]:
            badges.append(_lang_with_flag(lang))
    lines.append(" ".join(f"[{b}]" for b in badges))

    footer_parts = []
    if audio_langs:
        footer_parts.append(f"🎧 Audio: {', '.join(audio_langs)}")
    if subtitle_langs:
        sub_str = ", ".join(subtitle_langs[:5])
        if len(subtitle_langs) > 5:
            sub_str += f" +{len(subtitle_langs) - 5}"
        footer_parts.append(f"💬 {sub_str}")
    if footer_parts:
        lines.append(" • ".join(footer_parts))

    return "\n".join(lines)


# Dispatcher used by routes.py
LAYOUT_RENDERERS = {
    "cinematic": render_cinematic,
    "torrentio": render_compact,
    "badges": render_badges,
}


def generate_stream_description(
    layout: str,
    title: str | None,
    resolution: int,
    size: int,
    codec: str | None = None,
    fmt: str | None = None,
    audio_langs: list[str] | None = None,
    subtitle_langs: list[str] | None = None,
) -> str:
    """Dispatch to the per-layout renderer. Falls back to cinematic."""
    renderer = LAYOUT_RENDERERS.get(layout, render_cinematic)
    return renderer(
        title=title,
        resolution=resolution,
        size=size,
        codec=codec,
        fmt=fmt,
        audio_langs=audio_langs,
        subtitle_langs=subtitle_langs,
    )


# Back-compat shim — older callers used this signature.
def generate_stream_title(
    resolution: int, size: int, audio_langs: list[str] = None
) -> str:
    """Generate a clean stream title with resolution and optional audio language."""
    res_str = _format_resolution(resolution)
    size_str = _format_size(size)
    title = f"{res_str} • {size_str}"
    if audio_langs:
        title += f" • {', '.join(audio_langs[:3])}"
    return title


def generate_stream_badges(
    resolution: int,
    codec: str | None,
    audio_langs: list[str] | None,
    fmt: str | None = None,
) -> list[str]:
    """Build the badge token list for behaviorHints.badges.

    Mirrors PenguPlay's second-line chips: resolution, codec short form,
    format, language with flag. Stremio renders these as colored pills
    above the stream title in the picker.

    Returns ['1080p', 'HEVC', 'DASH', 'HI 🇮🇳'].
    """
    res_str = _format_resolution(resolution)
    badges = [res_str]
    if codec:
        badges.append(_short_codec(codec))
    if fmt:
        badges.append(fmt)
    if audio_langs:
        for lang in audio_langs[:2]:
            badges.append(_lang_with_flag(lang))
    return badges


def get_stream_filename(url: str) -> str:
    """Extract or generate a filename with proper extension from a stream URL.
    This fixes the 'unrecognized file format' error in Stremio by providing
    a filename hint with a known video extension.
    """
    url_str = str(url)

    ext_match = FILE_EXT_PATTERN.match(url_str)
    if ext_match:
        ext = ext_match.group(1).lower()
        if ext in ("mp4", "mkv", "avi", "webm", "m4v", "mov", "ts"):
            return f"stream.{ext}"

    parsed = urlparse(url_str)
    path = parsed.path
    if "." in path:
        ext = path.rsplit(".", 1)[-1].lower()
        if ext in ("mp4", "mkv", "avi", "webm", "m4v", "mov", "ts"):
            return f"stream.{ext}"

    return "stream.mp4"
