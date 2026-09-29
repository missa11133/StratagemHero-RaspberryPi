import pygame

from game.systems.layout import LayoutRegistry
from game.systems import bloom


class GameOverScreen:

    # Через сколько миллисекунд автоматически
    # вернуться на экран START
    GAME_OVER_DELAY = 5000

    # Позиции элементов экрана по умолчанию
    DEFAULT_LAYOUT = {
        "title": {
            "anchor": "center",
            "pos": [400, 140],
        },
        "score": {
            "anchor": "center",
            "pos": [400, 230],
        },
    }

    TEXT_COLOR = (240, 240, 240)
    SUCCESS_COLOR = (255, 238, 0)

    def __init__(self, game):

        self.game = game

        self.layout = LayoutRegistry(
            "game_over",
            self.DEFAULT_LAYOUT
        )

        self.background = pygame.image.load(
            "assets/images/ui/background.png"
        ).convert()

        self.background = pygame.transform.scale(
            self.background,
            (1024, 600)
        )

        self.reset()

    def reset(self):

        self.elapsed = 0

    def handle_events(self, events):

        # Кнопки не нужны — экран сам
        # возвращается на START по таймеру
        pass

    def update(self):

        self.elapsed += self.game.clock.get_time()

        if self.elapsed >= self.GAME_OVER_DELAY:

            self.game.change_screen(
                self.game.start_screen
            )

    def draw(self, screen):

        screen.blit(
            self.background,
            (0, 0)
        )

        bloom.blit_bloom(
            screen,
            "GAME OVER",
            self.layout.font_size("title") or 64,
            self.layout.pos("title"),
            self.TEXT_COLOR,
            anchor=self.layout.anchor("title"),
        )

        bloom.blit_bloom(
            screen,
            "YOUR FINAL SCORE",
            self.layout.font_size("score") or 64,
            self.layout.pos("score"),
            self.TEXT_COLOR,
            anchor=self.layout.anchor("score"),
        )

        bloom.blit_bloom(
            screen,
            f"{self.game.round_manager.score:,}",
            self.layout.font_size("score_num") or 64,
            self.layout.pos("score_num"),
            self.SUCCESS_COLOR,
            anchor=self.layout.anchor("score_num"),
        )

        #score = pygame.font.Font(
        #    "assets/fonts/FS Sinclair Medium.otf",
        #    self.layout.font_size("score") or 48,
        #).render(
        #    f"SCORE: {self.game.round_manager.score}",
        #    True,
        #    (240, 240, 240)
        #)

        #score_rect = self.layout.rect(
        #    "score",
        #    score.get_width(),
        #    score.get_height()
        #)

        #screen.blit(
        #    score,
        #    score_rect
        #)