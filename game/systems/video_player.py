import os
import random
import re
import subprocess

import pygame

import imageio_ffmpeg


# Папка с роликами
VIDEO_DIR = os.path.join("assets", "videos")

# Частота кадров по умолчанию, если метаданные не читаются
DEFAULT_FPS = 30.0

# Ограничения FPS из метаданных
MIN_FPS = 1.0
MAX_FPS = 60.0


class VideoPlayer:
    """Воспроизведение MP4 поверх pygame через ffmpeg (imageio-ffmpeg).

    Видеоряд декодируется в rawvideo (rgb24) и читается из stdout
    отдельного ffmpeg-процесса. Звук выдёргивается вторым проходом
    в WAV и играет как pygame.mixer.Sound — стрим музыки не трогаем.
    """

    def __init__(self, target_size):

        self.target_size = (int(target_size[0]), int(target_size[1]))

        # Статический ffmpeg, поставляемый в imageio-ffmpeg
        self._ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        self._process = None
        self._audio_sound = None

        # Период смены кадров в миллисекундах
        self.frame_time_ms = 1000.0 / DEFAULT_FPS

    # ==================================================
    # Выбор ролика
    # ==================================================

    @staticmethod
    def list_videos():
        """Все .mp4 из assets/videos."""

        if not os.path.isdir(VIDEO_DIR):
            return []

        return sorted(
            os.path.join(VIDEO_DIR, name)
            for name in os.listdir(VIDEO_DIR)
            if name.lower().endswith(".mp4")
        )

    def pick_video(self, last_path=None):
        """Случайный ролик без немедленного повтора."""

        videos = self.list_videos()

        if not videos:
            return None

        if len(videos) == 1:
            return videos[0]

        candidates = [
            video for video in videos
            if video != last_path
        ]

        return random.choice(candidates)

    # ==================================================
    # Запуск и остановка ролика
    # ==================================================

    def open(self, path):
        """Открыть ролик: подготовить видеоряд и звук."""

        self.close()

        width, height = self.target_size
        self._frame_size = width * height * 3   # rgb24

        self.frame_time_ms = 1000.0 / (
            self._detect_fps(path) or DEFAULT_FPS
        )

        self._process = subprocess.Popen(
            [
                self._ffmpeg,
                "-hide_banner",
                "-loglevel", "error",
                "-i", path,
                "-an",
                "-vf",
                (
                    f"scale={width}:{height}:"
                    "force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:"
                    "(ow-iw)/2:(oh-ih)/2:black"
                ),
                "-f", "rawvideo",
                "-pix_fmt", "rgb24",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        self._load_audio(path)

    def close(self):
        """Закрыть ролик: остановить звук и декодер."""

        self.stop_audio()
        self._stop_decoder()

    # ==================================================
    # Кадры
    # ==================================================

    def next_frame(self):
        """Следующий кадр как Surface. None — видео закончилось."""

        if self._process is None:
            return None

        data = self._process.stdout.read(self._frame_size)

        if not data or len(data) < self._frame_size:

            self._stop_decoder()

            return None

        try:
            return pygame.image.frombuffer(
                data,
                self.target_size,
                "RGB",
            )

        except pygame.error:
            return None

    # ==================================================
    # Звук
    # ==================================================

    def play_audio(self):

        if self._audio_sound is not None:
            self._audio_sound.play()

    def stop_audio(self):

        if self._audio_sound is not None:
            self._audio_sound.stop()

    # ==================================================
    # Внутренние помощники
    # ==================================================

    def _load_audio(self, path):
        """Извлечь звук ролика в WAV и подготовить Sound."""

        try:
            process = subprocess.Popen(
                [
                    self._ffmpeg,
                    "-hide_banner",
                    "-loglevel", "error",
                    "-i", path,
                    "-vn",
                    "-ac", "2",
                    "-ar", "44100",
                    "-f", "wav",
                    "pipe:1",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )

            wav_data = process.stdout.read()

            process.wait(timeout=120)

        except Exception:

            self._audio_sound = None

            return

        try:
            self._audio_sound = pygame.mixer.Sound(buffer=wav_data)

        except pygame.error:
            self._audio_sound = None

    def _detect_fps(self, path):
        """FPS видеодорожки из метаданных ffmpeg."""

        try:
            process = subprocess.Popen(
                [
                    self._ffmpeg,
                    "-i", path,
                    "-hide_banner",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

            _, stderr_data = process.communicate(timeout=30)

        except Exception:
            return DEFAULT_FPS

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*fps",
            stderr_data.decode("utf-8", "ignore"),
        )

        if match is None:
            return DEFAULT_FPS

        return min(
            max(float(match.group(1)), MIN_FPS),
            MAX_FPS,
        )

    def _stop_decoder(self):

        if self._process is not None:

            try:
                self._process.terminate()
                self._process.wait(timeout=5)

            except Exception:
                pass

            self._process = None
