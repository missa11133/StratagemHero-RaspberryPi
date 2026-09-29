import pygame

from game.systems.video_player import VideoPlayer


class IdleVideoScreen:
    """Экран-заставка: крутит ролик из assets/videos.

    Показывается после длительного простоя на START. Видео доигрывает
    до конца и возвращает на START. Любое взаимодействие (клавиша,
    клик, тап) тут же возвращает на START.
    """

    # События, считающиеся взаимодействием
    INTERACTIVE_EVENTS = frozenset((
        pygame.KEYDOWN,
        pygame.MOUSEBUTTONDOWN,
        pygame.MOUSEBUTTONUP,
        pygame.FINGERDOWN,
        pygame.FINGERUP,
    ))

    def __init__(self, game):

        self.game = game

        self.player = VideoPlayer(
            game.screen.get_size()
        )

        self.current_frame = None

        # Накопленное время до смены кадра
        self._timer = 0.0

        # Последний ролик — чтобы не повторяться сразу
        self._last_path = None

    def start(self):
        """Запустить заставку со случайным роликом.

        Возвращает True, если воспроизведение началось.
        """

        path = self.player.pick_video(
            self._last_path
        )

        if path is None:
            return False

        self._last_path = path

        self.player.open(path)

        self.current_frame = None
        self._timer = 0.0

        self._advance()

        if self.current_frame is None:
            return False

        self.player.play_audio()

        return True

    def handle_events(self, events):

        for event in events:

            if event.type in self.INTERACTIVE_EVENTS:

                self._finish()

                return

        # Часть тач-событий дублируется в taps — ловим и их
        if self.game.input.taps:

            self._finish()

    def update(self):

        frame_time = self.player.frame_time_ms

        self._timer += self.game.clock.get_time()

        while self._timer >= frame_time:

            self._timer -= frame_time

            if self._advance() is None:

                self._finish()

                return

    def draw(self, screen):

        if self.current_frame is not None:

            screen.blit(
                self.current_frame,
                (0, 0),
            )

        else:
            screen.fill((0, 0, 0))

    # ==================================================
    # Внутренние помощники
    # ==================================================

    def _advance(self):

        frame = self.player.next_frame()

        if frame is not None:
            self.current_frame = frame

        return frame

    def _finish(self):
        """Видео закончилось или прервано — вернуться на START."""

        self.player.close()

        self.game.change_screen(
            self.game.start_screen
        )
