import pygame

from game.systems.layout import LayoutRegistry
from game.systems import bloom


class StartScreen:

    # Текст вместо кнопки START: раунд начинает любой ввод
    # стратагемы — WASD, стрелки или свайп/тап по экрану
    HINT_TEXT = "Enter any Stratagem Input to Start!"

    # Цвет подсказки — как у успешного ввода в геймплее
    # (game/screens/gameplay.py: SUCCESS_COLOR)
    SUCCESS_COLOR = (255, 238, 0)

    # Звук начала игры при переходе на GET READY
    ROUND_START_COIN_SOUND = (
        "assets/sounds/round start coin.mp3"
    )

    # Через сколько миллисекунд простоя на экране START
    # запускается видео-заставка (изменяемая настройка)
    IDLE_VIDEO_DELAY_MS = 30_000 #5 * 60 * 1000

    # Позиции элементов экрана по умолчанию
    DEFAULT_LAYOUT = {
        "title": {
            "anchor": "center",
            "pos": [400, 130],
        },
        "start_hint": {
            "anchor": "center",
            "pos": [512, 420],
            "font_size": 26,
        },
    }

    def __init__(self, game):

        self.game = game

        # Время простоя на экране
        self.elapsed = 0

        self.layout = LayoutRegistry(
            "start",
            self.DEFAULT_LAYOUT
        )

        self.background = pygame.image.load(
            "assets/images/ui/background.png"
        ).convert()

        self.background = pygame.transform.scale(
            self.background,
            (1024, 600)
        )

    def _start_game(self):

        self.game.audio.play_sfx(
            self.ROUND_START_COIN_SOUND
        )

        self.game.change_screen(
            self.game.get_ready_screen
        )

    def reset(self):
        """Сброс таймера простоя (вход на экран/после заставки)."""

        self.elapsed = 0

    def handle_events(self, events):

        interacted = False
        started = False

        for event in events:

            # Раунд уже начался — остальные события
            # этого кадра обрабатывать не нужно
            if started:

                break

            # ----------------------------------------------
            # Клавиатура: любая клавиша-направление (WASD
            # или стрелки) и Enter начинают раунд так же,
            # как раньше это делала кнопка START
            # ----------------------------------------------

            if event.type == pygame.KEYDOWN:

                interacted = True

                if (
                    event.key == pygame.K_RETURN
                    or event.key in self.game.input.key_map
                ):

                    self._start_game()

                    started = True

            # ----------------------------------------------
            # Мышь: клик в любом месте экрана. На десктопе
            # он заменяет тап по сенсорному экрану
            # ----------------------------------------------

            elif event.type == pygame.MOUSEBUTTONDOWN:

                interacted = True

                if event.button == 1:

                    self._start_game()

                    started = True

        # Сенсорный экран: тап в любом месте экрана
        if not started and self.game.input.taps:

            interacted = True

            self._start_game()

            started = True

        # Сенсорный экран: свайп — это ввод стратагемы,
        # он тоже начинает раунд
        if not started and self.game.input.consume_gesture():

            interacted = True

            self._start_game()

        # Любое взаимодействие сбрасывает таймер простоя
        if interacted:

            self.elapsed = 0

    def update(self):

        # Долгий простой — включаем видео-заставку
        self.elapsed += self.game.clock.get_time()

        if self.elapsed >= self.IDLE_VIDEO_DELAY_MS:

            self.elapsed = 0

            self.game.change_screen(
                self.game.idle_video_screen
            )

    def draw(self, screen):

        screen.blit(
            self.background,
            (0, 0)
        )

        bloom.blit_bloom(
            screen,
            "STRATAGEM HERO",
            self.layout.font_size("title") or 64,
            self.layout.pos("title"),
            (240, 240, 240),
            anchor=self.layout.anchor("title"),
        )

        bloom.blit_bloom(
            screen,
            self.HINT_TEXT,
            self.layout.font_size("start_hint") or 26,
            self.layout.pos("start_hint"),
            self.SUCCESS_COLOR,
            anchor=self.layout.anchor("start_hint"),
        )