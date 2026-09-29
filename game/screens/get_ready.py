import pygame

from game.systems.layout import LayoutRegistry
from game.systems import bloom


class GetReadyScreen:

    # Через сколько миллисекунд перейти на геймплей
    READY_DELAY = 1700

    # Обычный цвет текста — как TEXT_COLOR в геймплее.
    # Используется для надписи с номером раунда.
    TEXT_COLOR = (240, 240, 240)
    SUCCESS_COLOR = (255, 238, 0)

    # Позиции элементов экрана по умолчанию.
    # "Round" и номер раунда — единый блок разметки "ROUND N",
    # его позиция меняется в режиме --edit.
    DEFAULT_LAYOUT = {
        "round": {
            "anchor": "center",
            "pos": [512, 400],
            "font_size": 42,
        },
        "title": {
            "anchor": "center",
            "pos": [400, 300],
        },
        "theme": {
            "anchor": "center",
            "pos": [400, 380],
        },
    }

    # Заголовки тематических раундов
    THEME_TITLES = {
        "Orbital Strikes"   : "RAIN DOWN FROM ABOVE",
        "Backpacks"         : "BACK-PACKING A PUNCH",
        "Eagle Strikes"     : "FLY LIKE AN EAGLE",
        "Support Weapons"   : "OVERWHELMING FIREPOWER",
    }

    def __init__(self, game):

        self.game = game

        self.layout = LayoutRegistry(
            "get_ready",
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

        if self.elapsed >= self.READY_DELAY:

            self.game.change_screen(
                self.game.gameplay_screen
            )

    def draw(self, screen):

        screen.blit(
            self.background,
            (0, 0)
        )

        # ======================================================
        # Надпись с номером раунда — единый блок разметки
        # "ROUND N" (get_ready.json, редактируется в --edit).
        # Рисуется со свечением, как и "GET READY".
        # ======================================================

        bloom.blit_bloom(
            screen,
            "Round",
            self.layout.font_size("round") or 42,
            self.layout.pos("round"),
            self.TEXT_COLOR,
            anchor=self.layout.anchor("round"),
        )

        bloom.blit_bloom(
            screen,
            f"{self.game.round_manager.round_number}",
            self.layout.font_size("round_num") or 42,
            self.layout.pos("round_num"),
            self.SUCCESS_COLOR,
            anchor=self.layout.anchor("round_num"),
        )

        bloom.blit_bloom(
            screen,
            "GET READY",
            self.layout.font_size("title") or 64,
            self.layout.pos("title"),
            self.TEXT_COLOR,
            anchor=self.layout.anchor("title"),
        )

        # Слоган тематического раунда
        theme = self.game.round_manager.theme_category

        if theme is not None:

            slogan = self.THEME_TITLES.get(theme)

            if slogan is not None:

                bloom.blit_bloom(
                    screen,
                    slogan,
                    self.layout.font_size("theme") or 48,
                    self.layout.pos("theme"),
                    self.TEXT_COLOR,
                    anchor=self.layout.anchor("theme"),
                )