import pygame

from game.systems.layout import LayoutRegistry
from game.systems import bloom

class RoundScoreScreen:

    ROW_DELAYS = [0, 300, 900, 1500]

    # Через сколько миллисекунд экран результатов
    # автоматически сменится на GET READY
    SCREEN_DELAY = 3000

    # Позиции элементов экрана по умолчанию
    DEFAULT_LAYOUT = {
        "row_label": {
            "anchor": "midleft",
            "pos": [280, 220],
        },
        "row_value": {
            "anchor": "midright",
            "pos": [540, 220],
        },
    }

    # Шаг между строками результатов
    ROW_LABLE_STEP = 68
    ROW_VALUE_STEP = 64

    def __init__(self, game):

        self.game = game

        self.layout = LayoutRegistry(
            "round_score",
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
        # переходит на геймплей по таймеру
        pass

    def update(self):

        self.elapsed += self.game.clock.get_time()

        if self.elapsed >= self.SCREEN_DELAY:

            self.game.round_manager.next_round()

            self.game.change_screen(
                self.game.get_ready_screen
            )

    def draw(self, screen):

        screen.blit(
            self.background,
            (0, 0)
        )

        manager = self.game.round_manager

        # ==================================================
        # Результаты раунда
        # ==================================================

        rows = [
            ("Round Bonus", str(manager.round_bonus)),
            ("Time Bonus", str(manager.time_bonus)),
            ("Perfect Bonus", str(manager.perfect_bonus)),
            ("Total Score", f"{manager.score + manager.round_total:,}"),
        ]

        # Показываем только те строки, чей таймер
        # уже сработал (текст просто появляется,
        # без анимации)
        visible_rows = [
            row
            for row, delay in zip(rows, self.ROW_DELAYS)
            if self.elapsed >= delay
        ]

        for index, (label, value) in enumerate(visible_rows):

            label_x, label_y = self.layout.pos("row_label")

            bloom.blit_bloom(
                screen,
                label,
                self.layout.font_size("row_label") or 64,
                (label_x, label_y + index * self.ROW_LABLE_STEP),
                (240, 240, 240),
                anchor=self.layout.anchor("row_label"),
            )

            value_x, value_y = self.layout.pos("row_value")

            bloom.blit_bloom(
                screen,
                value,
                self.layout.font_size("row_value") or 64,
                (value_x, value_y + index * self.ROW_VALUE_STEP),
                (255, 238, 0),
                anchor=self.layout.anchor("row_value"),
            )