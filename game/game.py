import os

# На сенсорном экране SDL2 дублирует касания и в FINGER-,
# и в синтетические мышиные события. Отключаем синтетическую
# мышь от тача: жесты получаем только из FINGER-событий,
# и двойного ввода не возникает. Настоящая мышь продолжает
# работать (нужна для тестов на десктопе).
os.environ.setdefault(
    "SDL_TOUCH_MOUSE_EVENTS",
    "0",
)

import pygame

from game.screens.start import StartScreen
from game.screens.gameplay import GameplayScreen
from game.systems.input import InputManager

from game.systems.round_manager import RoundManager
from game.data.stratagems import STRATAGEMS

#from game.screens.start import StartScreen
#from game.screens.gameplay import GameplayScreen
from game.screens.idle_video import IdleVideoScreen
from game.screens.round_score import RoundScoreScreen
from game.screens.game_over import GameOverScreen
from game.screens.get_ready import GetReadyScreen

from game.systems.audio import AudioManager


SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 600
FPS = 60

# Музыка геймплея
GAME_MUSIC_PATH = "assets/sounds/game music.mp3"


class Game:

    def __init__(self, editor_mode=False):

        pygame.init()

        self.editor_mode = editor_mode

        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT)
        )

        self.round_manager = RoundManager(
            STRATAGEMS
        )   

        pygame.display.set_caption("Stratagem Hero")

        self.clock = pygame.time.Clock()

        self.running = True

        self.input = InputManager(
            self.screen.get_size()
        )

        self.audio = AudioManager()

        self.start_screen = StartScreen(self)
        self.gameplay_screen = GameplayScreen(self)
        self.round_score_screen = RoundScoreScreen(self)
        self.game_over_screen = GameOverScreen(self)
        self.get_ready_screen = GetReadyScreen(self)

        # Экран видео-заставки при долгом простое на START
        self.idle_video_screen = IdleVideoScreen(self)

        self.current_screen = self.start_screen

        # В режиме редактирования разметки создаём редактор
        if self.editor_mode:

            from game.tools.ui_editor import UIEditor

            self.editor = UIEditor(self)

    def change_screen(self, screen):

        # При входе в геймплей сбрасываем экран
        # под текущее состояние менеджера раунда

        if screen == self.gameplay_screen:

            # Если раунд уже завершён, возвращаться в геймплей
            # не нужно — свободных стратагем больше нет.
            if (
                self.round_manager.current_index
                >= len(self.round_manager.queue)
            ):

                screen = self.round_score_screen

            else:

                screen.reset()

        # При входе на экран GET READY сбрасываем
        # его внутренний таймер
        elif screen == self.get_ready_screen:

            screen.reset()

        # При входе на экран результатов сбрасываем
        # таймер появления строк (сюда же попадаем,
        # если геймплей перенаправляет сюда при
        # завершённом раунде)
        if screen == self.round_score_screen:

            screen.reset()

        # При входе на экран GAME OVER сбрасываем
        # таймер автовозврата на START
        if screen == self.game_over_screen:

            screen.reset()

        # При входе на видео-заставку запускаем её.
        # Роликов нет или видео не открылось — остаёмся на START.
        if screen == self.idle_video_screen:

            if not screen.start():

                screen = self.start_screen

        # При возврате на экран START создаём новый
        # менеджер раунда — прошлый уже завершён.
        # Заодно сбрасываем таймер простоя и закрываем
        # плеер заставки (гигиенически).
        if screen == self.start_screen:

            self.idle_video_screen.player.close()

            self.round_manager = self.create_round_manager()

            screen.reset()

        # ==================================================
        # Музыка играет ТОЛЬКО во время геймплея
        # ==================================================

        if screen == self.gameplay_screen:

            self.audio.play_music(
                GAME_MUSIC_PATH
            )

        elif self.current_screen == self.gameplay_screen:

            self.audio.stop_music()

        # ==================================================
        # Жесты записываются в очередь только во время
        # геймплея: свайпы на других экранах не должны
        # попадать в игру при вводе комбинации.
        # ==================================================

        self.input.set_gesture_enabled(
            screen == self.gameplay_screen
        )

        self.current_screen = screen

    def create_round_manager(self):

        return RoundManager(
            STRATAGEMS
        )

    def run(self):

        while self.running:

            events = pygame.event.get()

            for event in events:

                if event.type == pygame.QUIT:
                    self.running = False

            if self.editor_mode:

                # Редактор разметки: события полностью за ним,
                # экраны заморожены (статичное превью)
                self.editor.handle_events(events)
                self.editor.update()

                self.current_screen.draw(self.screen)
                self.editor.draw_overlay(self.screen)

            else:

                self.input.update(events)

                self.current_screen.handle_events(events)
                self.current_screen.update()
                self.current_screen.draw(self.screen)

            pygame.display.flip()

            self.clock.tick(FPS)

        pygame.quit()