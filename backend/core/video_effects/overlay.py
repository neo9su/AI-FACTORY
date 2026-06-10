"""Video overlay effects: dynamic stickers + subtitle rendering.

Applies:
1. Subtitle overlay with new style (top-right corner + highlight)
2. Dynamic stickers (animated emoji/sticker overlay)
3. Sale point highlights (卖点高亮)

All effects are applied via ffmpeg with overlay filters.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Subtitle style config ──────────────────────────────────────────────────

@dataclass
class SubtitleStyle:
    """Subtitle rendering style parameters."""
    # Font
    font: str = "SmileySans-Oblique"
    font_size: int = 24
    font_color: str = "white"
    font_outline: int = 2
    font_outline_color: str = "black"
    font_bold: bool = True

    # Position
    position: str = "top_right"  # top_left, top_right, bottom_center
    margin_x: int = 40
    margin_y: int = 40
    line_spacing: int = 8

    # Highlight (for selling points / key text)
    highlight_color: str = "yellow"
    highlight_min_chars: int = 4  # min chars to trigger highlight

    # Bubble / badge background
    use_background: bool = True
    bg_color: str = "rgba(0,0,0,0.7)"
    bg_border: int = 2
    bg_border_color: str = "rgba(255,255,255,0.3)"
    bg_radius: int = 8
    bg_padding: int = 10


# ─── Sticker definitions ────────────────────────────────────────────────────

@dataclass
class Sticker:
    """A sticker overlay definition."""
    name: str
    image_path: str  # path to PNG with transparency
    position: str  # top_right, top_left, bottom_right, bottom_left, center
    size: int = 60  # sticker size in pixels
    animation: str = "pulse"  # pulse, fade_in, slide_in, bounce
    duration_start: float = 0.0  # start time in seconds
    duration_end: float = 5.0  # end time in seconds
    opacity: float = 0.8


# ─── Sticker images (generated programmatically) ───────────────────────────

STICKER_DIR = Path.home() / "autonomous-ai-factory" / "assets" / "stickers"
STICKER_DIR.mkdir(parents=True, exist_ok=True)


def create_sticker_files():
    """Create sticker image files using SVG rendering → PNG.

    We generate simple sticker images programmatically using matplotlib
    as a fallback (no external asset files needed).
    """
    sticker_map = {
        "emoji_fire": "🔥",
        "emoji_star": "⭐",
        "emoji_thumbsup": "👍",
        "emoji_heart": "❤️",
        "emoji_warning": "⚠️",
        "badge_new": "NEW",
        "badge_hot": "HOT",
        "badge_sale": "SALE",
        "badge_free": "FREE",
        "arrow_red": "→",
        "circle_green": "✓",
        "sparkle": "✨",
    }

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        from matplotlib.patches import Circle, FancyBboxPatch

        for name, emoji in sticker_map.items():
            png_path = STICKER_DIR / f"{name}.png"
            if png_path.exists():
                continue

            fig, ax = plt.subplots(
                figsize=(2, 2), dpi=120,
                facecolor="transparent",
                edgecolor="none",
            )
            ax.set_xlim(0, 2)
            ax.set_ylim(0, 2)
            ax.axis("off")

            if name.startswith("badge_") or name in ("circle_green",):
                # Badge style: rounded rect or circle background
                if name == "circle_green":
                    circle = Circle(
                        (1, 1), 0.4, facecolor="#22c55e",
                        edgecolor="white", linewidth=3,
                    )
                    ax.add_patch(circle)
                    ax.text(1, 1, "✓", ha="center", va="center",
                            fontsize=32, color="white", fontweight="bold")
                else:
                    bbox = FancyBboxPatch(
                        (0.2, 0.5), 1.6, 1.0,
                        boxstyle="round,pad=0.15",
                        facecolor="#ef4444", edgecolor="white", linewidth=2,
                    )
                    ax.add_patch(bbox)
                    ax.text(1, 1, emoji, ha="center", va="center",
                            fontsize=20, color="white", fontweight="bold")
            else:
                # Emoji style: just the emoji on transparent background
                ax.text(1, 1, emoji, ha="center", va="center",
                        fontsize=80, transform=ax.transData)

            fig.savefig(str(png_path), transparent=True, bbox_inches="tight", pad_inches=0.05)
            plt.close(fig)
            logger.debug(f"Created sticker: {png_path}")

    except ImportError:
        # Fallback: use simple PIL-based stickers
        try:
            from PIL import Image, ImageDraw, ImageFont
            for name, emoji in sticker_map.items():
                png_path = STICKER_DIR / f"{name}.png"
                if png_path.exists():
                    continue
                img = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.rounded_rectangle(
                    [10, 10, 230, 230], radius=20,
                    fill=(255, 255, 255, 255),
                )
                try:
                    font = ImageFont.truetype(
                        "/System/Library/Fonts/SFNSDisplay.ttf", 80
                    )
                except (OSError, IndexError):
                    font = ImageFont.load_default()
                draw.text((120, 120), emoji, font=font, anchor="mm")
                img.save(str(png_path))
        except ImportError:
            logger.warning("No matplotlib or PIL available for sticker generation")


# ─── Subtitle processing ────────────────────────────────────────────────────

# Common selling-point keywords that should be highlighted
SELLING_POINT_KEYWORDS = [
    "限时", "免费", "独家", "爆款", "神器", "必备",
    "全新", "升级", "推荐", "首选", "最强", "第一",
    "免费体验", "限时优惠", "立即抢购", "点击领取",
]


def parse_subtitles(subtitle_text: str) -> list[dict]:
    """Parse subtitle text into timed segments.

    Supports SRT-like format (line per subtitle) or plain text
    split into ~3-second chunks.

    Returns list of dicts with: start, end, text, highlight
    """
    segments = []

    # Detect SRT format
    if re.search(r'\d{2}:\d{2}:\d{2}.*-->', subtitle_text):
        # SRT format parsing
        blocks = re.split(r'\n\s*\n', subtitle_text.strip())
        for i, block in enumerate(blocks):
            lines = block.strip().split('\n')
            if len(lines) < 3:
                continue
            time_code = lines[1]
            text = ' '.join(lines[2:])
            m = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})', time_code)
            if m:
                start = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3)) + int(m.group(4))/1000
                end = int(m.group(5))*3600 + int(m.group(6))*60 + int(m.group(7)) + int(m.group(8))/1000
                segments.append({
                    'start': start,
                    'end': end,
                    'text': text.strip(),
                    'highlight': _check_highlight(text),
                })
    else:
        # Plain text: split into chunks of ~20 chars, 3 seconds each
        chunk_size = 20
        for i, chunk in enumerate(_text_chunks(subtitle_text, chunk_size)):
            segments.append({
                'start': i * 3.0,
                'end': (i + 1) * 3.0,
                'text': chunk.strip(),
                'highlight': _check_highlight(chunk),
            })

    return segments


def _text_chunks(text: str, chunk_size: int) -> list[str]:
    """Split text into chunks of ~chunk_size characters, breaking at spaces."""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        # Try to break at space
        last_space = chunk.rfind(' ')
        if last_space > chunk_size * 0.6 and i + chunk_size < len(text):
            chunks.append(text[i:i + last_space])
        else:
            chunks.append(chunk)
    return chunks


def _check_highlight(text: str) -> bool:
    """Check if subtitle text contains selling-point keywords."""
    for keyword in SELLING_POINT_KEYWORDS:
        if keyword in text:
            return True
    return False


# ─── FFmpeg overlay construction ────────────────────────────────────────────

def build_subtitle_filter(
    subtitle_segments: list[dict],
    video_width: int,
    video_height: int,
    style: Optional[SubtitleStyle] = None,
) -> str:
    """Build an ffmpeg filter_complex string for subtitle overlay.

    Uses drawtext filter with position-based placement.
    For highlighted text, uses separate colored text layers.
    """
    style = style or SubtitleStyle()

    filter_parts = []

    for seg in subtitle_segments:
        start = seg['start']
        end = seg['end']
        text = seg['text'].replace("'", "'\\''")  # Escape single quotes
        duration = end - start

        # Calculate position
        if style.position == "top_right":
            x = f"w-{style.margin_x}-text_w"
            y = f"{style.margin_y}+{(style.font_size + style.line_spacing)}"
        elif style.position == "top_left":
            x = f"{style.margin_x}"
            y = f"{style.margin_y}+{(style.font_size + style.line_spacing)}"
        else:  # bottom_center
            x = f"(w-text_w)/2"
            y = f"h-{style.margin_y}-text_h-(fontsize*0.2)"

        # Build drawtext expression
        expr = f"drawtext="
        expr += f"expr='if(gte(t,{start}),if(lte(t,{end}),'{text}', ''), '')'"
        expr += f":x={x}"
        expr += f":y={y}"
        expr += f":fontsize={style.font_size}"
        expr += f":fontcolor={style.font_color}"
        expr += f":borderw={style.font_outline}"
        expr += f":bordercolor={style.font_outline_color}"

        if style.font_bold:
            expr += ":fontweight=bold"

        if style.use_background:
            expr += f":box=1:boxcolor={style.bg_color}:boxborderw={style.bg_border}:boxrounds={style.bg_radius}:padding={style.bg_padding}"

        filter_parts.append(expr)

    # Highlight filter: pass 2 — re-render highlighted segments in highlight color
    highlight_segments = [s for s in subtitle_segments if s.get('highlight')]
    if highlight_segments:
        for seg in highlight_segments:
            start = seg['start']
            end = seg['end']
            text = seg['text'].replace("'", "'\\''")
            filter_parts.append(
                f"drawtext="
                f"expr='if(gte(t,{start}),if(lte(t,{end}),'{text}', ''), '')'"
                f":x={f'(w-text_w)/2'}"
                f":y={f'h-{40}-text_h-(fontsize*0.2)'}"
                f":fontsize={style.font_size}"
                f":fontcolor={style.highlight_color}"
                f":borderw=3:bordercolor=black"
                f":box=1:boxcolor=rgba(0,0,0,0.7):boxborderw=2:boxrounds=8:padding=10"
            )

    return ";".join(filter_parts)


def build_sticker_filter(
    stickers: list[Sticker],
    video_width: int,
    video_height: int,
) -> str:
    """Build ffmpeg overlay filter for sticker animations.

    Returns filter_complex string with overlay + fade effects.
    """
    filter_parts = []

    for i, sticker in enumerate(stickers):
        # Calculate position based on corner
        if sticker.position == "top_right":
            x = f"w-{sticker.size}-{sticker.margin_x if hasattr(sticker, 'margin_x') else 20}"
            y = f"{sticker.margin_y if hasattr(sticker, 'margin_y') else 20}"
        elif sticker.position == "top_left":
            x = f"{sticker.margin_x if hasattr(sticker, 'margin_x') else 20}"
            y = f"{sticker.margin_y if hasattr(sticker, 'margin_y') else 20}"
        elif sticker.position == "bottom_right":
            x = f"w-{sticker.size}-{sticker.margin_x if hasattr(sticker, 'margin_x') else 20}"
            y = f"h-{sticker.size}-{sticker.margin_y if hasattr(sticker, 'margin_y') else 20}"
        elif sticker.position == "bottom_left":
            x = f"{sticker.margin_x if hasattr(sticker, 'margin_x') else 20}"
            y = f"h-{sticker.size}-{sticker.margin_y if hasattr(sticker, 'margin_y') else 20}"
        else:  # center
            x = f"(w-{sticker.size})/2"
            y = f"(h-{sticker.size})/2"

        # Apply animation
        t = "t"
        if sticker.animation == "pulse":
            # Pulse effect: scale oscillates
            scale_expr = f"if(lte(t,{sticker.duration_start}),0,if(gte(t,{sticker.duration_end}),0,1+0.1*sin({3}*2*PI*t)))"
            x = f"{x}-({sticker.size}*({scale_expr}-1))/2"
            y = f"{y}-({sticker.size}*({scale_expr}-1))/2"
            # Apply opacity fade in/out
            opacity_expr = f"if(lte(t,{sticker.duration_start}),0,if(gte(t,{sticker.duration_end}),0,min(1,({sticker.duration_end}-t)/max(0.5,{sticker.duration_end}-{sticker.duration_start})*{sticker.opacity})))"
        elif sticker.animation == "fade_in":
            scale_expr = "1"
            opacity_expr = f"if(lte(t,{sticker.duration_start}),0,if(gte(t,{sticker.duration_end}),0,{sticker.opacity}))"
        elif sticker.animation == "slide_in":
            slide_start = y if sticker.position in ("top_left", "top_right") else x
            scale_expr = "1"
            opacity_expr = f"if(lte(t,{sticker.duration_start}),0,if(gte(t,{sticker.duration_end}),0,{sticker.opacity}))"
        else:  # bounce
            scale_expr = f"1+0.15*sin({4}*2*PI*t)"
            opacity_expr = f"if(lte(t,{sticker.duration_start}),0,if(gte(t,{sticker.duration_end}),0,{sticker.opacity}))"

        filter_parts.append(
            f"[{i+1}:v][0:v]overlay={x}:{y}:{opacity_expr}"
        )

    return ";".join(filter_parts)


# ─── Main overlay application ────────────────────────────────────────────────

def apply_overlay_effects(
    input_video: str,
    output_video: str,
    subtitle_text: Optional[str] = None,
    stickers: Optional[list[Sticker]] = None,
    style: Optional[SubtitleStyle] = None,
    duration: Optional[float] = None,
) -> dict:
    """Apply dynamic stickers and subtitle overlay to video.

    Args:
        input_video: Path to input video file
        output_video: Path to output video file
        subtitle_text: Subtitle text (plain text or SRT format)
        stickers: List of sticker overlays
        style: Subtitle rendering style
        duration: Optional override for video duration

    Returns:
        dict with processing result info
    """
    import subprocess

    style = style or SubtitleStyle()

    # Ensure sticker files exist
    create_sticker_files()

    # Get video info
    video_info = get_video_info(input_video)
    width = video_info['width']
    height = video_info['height']

    # Build filter_complex
    filter_parts = []

    # 1. Subtitle overlay
    if subtitle_text:
        segments = parse_subtitles(subtitle_text)
        if segments:
            filter_parts.append(
                build_subtitle_filter(segments, width, height, style)
            )

    # 2. Sticker overlays
    if stickers:
        for sticker in stickers:
            sticker_path = STICKER_DIR / f"{sticker.image_path}"
            if not sticker_path.exists():
                sticker_path = STICKER_DIR / f"{sticker.name}.png"
            if sticker_path.exists():
                filter_parts.append(
                    build_sticker_filter([sticker], width, height)
                )

    # Build ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_video,
    ]

    # Add sticker inputs
    if stickers:
        for sticker in stickers:
            sticker_path = STICKER_DIR / f"{sticker.image_path}"
            if not sticker_path.exists():
                sticker_path = STICKER_DIR / f"{sticker.name}.png"
            if sticker_path.exists():
                cmd.extend(["-i", str(sticker_path)])

    # Apply filters
    if filter_parts:
        cmd.extend(["-filter_complex", ";".join(filter_parts)])
    else:
        cmd.extend(["-c", "copy"])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac" if duration is None else "copy",
        "-b:a", "128k",
        output_video,
    ])

    logger.info(f"[Overlay] Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min max
        )
        if result.returncode != 0:
            logger.error(f"[Overlay] FFmpeg error: {result.stderr[:500]}")
            return {"success": False, "error": result.stderr[:500]}

        # Verify output
        output_info = get_video_info(output_video)
        logger.info(
            f"[Overlay] Complete: {width}x{height} → "
            f"{output_info['width']}x{output_info['height']}, "
            f"{output_info.get('duration', 0):.1f}s"
        )

        return {
            "success": True,
            "input": input_video,
            "output": output_video,
            "width": output_info['width'],
            "height": output_info['height'],
            "duration": output_info.get('duration', 0),
            "subtitle_segments": len(parse_subtitles(subtitle_text)) if subtitle_text else 0,
            "stickers_applied": len(stickers) if stickers else 0,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout (10min)"}
    except Exception as e:
        logger.error(f"[Overlay] Error: {e}")
        return {"success": False, "error": str(e)}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_video_info(video_path: str) -> dict:
    """Get video metadata via ffprobe."""
    import json
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                video_path,
            ],
            capture_output=True, text=True,
        )
        info = json.loads(result.stdout)
        stream = None
        for s in info.get("streams", []):
            if s.get("codec_type") == "video":
                stream = s
                break
        return {
            "width": stream.get("width", 0),
            "height": stream.get("height", 0),
            "duration": float(info.get("format", {}).get("duration", 0)),
            "codec": stream.get("codec_name", "unknown"),
        }
    except Exception as e:
        logger.warning(f"Failed to probe video: {e}")
        return {"width": 0, "height": 0, "duration": 0}


# ─── Quick demo ─────────────────────────────────────────────────────────────

def demo():
    """Quick demo of the overlay system."""
    print("✅ Overlay effects module loaded")
    print(f"   Sticker dir: {STICKER_DIR}")

    # Check ffmpeg
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    if result.returncode == 0:
        print("   ✅ ffmpeg available")
    else:
        print("   ❌ ffmpeg not found — overlay will fail at runtime")

    # Check subtitle parsing
    test_text = "这是一个卖点文字\n下一个卖点展示"
    segments = parse_subtitles(test_text)
    print(f"   Subtitle parser: {len(segments)} segments from test text")


if __name__ == "__main__":
    demo()
