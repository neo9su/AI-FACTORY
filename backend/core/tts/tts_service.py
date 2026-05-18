"""TTSService — 封装 CosyVoice2 subprocess 调用，支持文字→WAV合成"""
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 路径配置
COSYVOICE_PYTHON = str(Path.home() / "cosyvoice-env/bin/python")
COSYVOICE_SYNTH = str(Path.home() / "cosyvoice2/cosyvoice_synth.py")
COSYVOICE_MODEL = str(Path.home() / ".cosyvoice/models/iic/CosyVoice2-0___5B")
DEFAULT_REF_AUDIO = str(Path.home() / "Movies/5月9日(2)/5月9日(2).wav")

# 音频输出目录（静态文件服务用）
AUDIO_OUTPUT_DIR = str(Path.home() / "autonomous-ai-factory/static/audio")


class TTSService:
    """CosyVoice2 TTS 服务封装"""

    def __init__(
        self,
        ref_audio: str = DEFAULT_REF_AUDIO,
        ref_text: str = "",
        speed: float = 1.0,
        timeout: int = 120,
    ) -> None:
        self.ref_audio = ref_audio
        self.ref_text = ref_text
        self.speed = speed
        self.timeout = timeout
        # 确保输出目录存在
        Path(AUDIO_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    async def synthesize(
        self,
        text: str,
        output_path: Optional[str] = None,
    ) -> str:
        """合成单段文字为 WAV 文件

        Args:
            text: 要合成的文字
            output_path: 输出路径，不传则自动生成到 AUDIO_OUTPUT_DIR

        Returns:
            输出 WAV 文件绝对路径

        Raises:
            RuntimeError: 合成失败
        """
        if not output_path:
            output_path = str(Path(AUDIO_OUTPUT_DIR) / f"{uuid.uuid4().hex}.wav")

        cmd = [
            COSYVOICE_PYTHON,
            COSYVOICE_SYNTH,
            "--text",
            text,
            "--out",
            output_path,
            "--model-dir",
            COSYVOICE_MODEL,
            "--speed",
            str(self.speed),
        ]
        if self.ref_audio and Path(self.ref_audio).exists():
            cmd += ["--ref-audio", self.ref_audio]
        if self.ref_text:
            cmd += ["--ref-text", self.ref_text]

        logger.info("[TTSService] Synthesizing: %s...", text[:50])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
        except asyncio.TimeoutError as e:
            raise RuntimeError(f"TTS timeout after {self.timeout}s") from e

        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0:
            raise RuntimeError(f"TTS failed: {stderr_str[-500:]}")

        if not stdout_str.startswith("OK:"):
            raise RuntimeError(f"TTS unexpected output: {stdout_str}")

        if not Path(output_path).exists():
            raise RuntimeError(f"TTS output file not found: {output_path}")

        logger.info("[TTSService] Done: %s", output_path)
        return output_path

    async def synthesize_lines(
        self,
        lines: list[str],
        product_id: str,
        script_index: int = 0,
    ) -> list[str]:
        """批量合成多行文字，每行生成独立 WAV

        Returns:
            每行对应的 WAV 文件路径列表
        """
        out_paths: list[str] = []
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            out_path = str(
                Path(AUDIO_OUTPUT_DIR) / f"{product_id}_s{script_index}_l{i}.wav"
            )
            try:
                path = await self.synthesize(line, output_path=out_path)
                out_paths.append(path)
            except RuntimeError as e:
                logger.warning("[TTSService] Line %d failed: %s", i, e)
        return out_paths

    @staticmethod
    def wav_to_url(wav_path: str) -> str:
        """将绝对路径转换为前端可访问的 URL"""
        # /static/audio/{filename}
        filename = Path(wav_path).name
        return f"/static/audio/{filename}"

    @staticmethod
    def concat_wavs(wav_paths: list[str], output_path: str) -> str:
        """拼接多个 WAV 文件为一个

        Returns:
            拼接后的 WAV 文件路径
        """
        import numpy as np
        import soundfile as sf

        chunks: list[np.ndarray] = []
        sample_rate: Optional[int] = None

        for p in wav_paths:
            if not Path(p).exists():
                continue
            data, sr = sf.read(p)
            if sample_rate is None:
                sample_rate = sr
            chunks.append(data)

        if not chunks:
            raise RuntimeError("No valid WAV files to concatenate")

        combined = np.concatenate(chunks)
        sf.write(output_path, combined, sample_rate or 22050, format="WAV")
        return output_path
