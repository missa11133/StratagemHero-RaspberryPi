import pygame
import random

from game.entities.stratagem import Stratagem
from game.systems.layout import LayoutRegistry
from game.systems import bloom


class GameplayScreen:

    # ==================================================
    # Размер экрана
    # ==================================================

    SCREEN_WIDTH = 1024
    SCREEN_HEIGHT = 600

    # ==================================================
    # Цвета
    # ==================================================

    TEXT_COLOR = (240, 240, 240)

    SUCCESS_COLOR = (255, 238, 0)
    ERROR_COLOR = (254, 134, 74) #(222, 123, 108)

    # Неактивные стрелки
    INACTIVE_ALPHA = 255 #90

    # Цвет таймера
    TIMER_COLOR = (255, 238, 0)

    # Порог «опасного» времени, мс (последние 2 секунды)
    LOW_TIME_THRESHOLD = 2000

    # Красный цвет при критическом таймере
    DANGER_COLOR = (222, 40, 40)

    # ==================================================
    # Время
    # ==================================================

    # Время на одну стратагему, миллисекунды
    STRATAGEM_TIME = 10000

    # Бонус времени за успешно выполненную стратагему, мс
    TIME_BONUS_PER_STRATAGEM = 1000

    # Задержка после ошибки
    ERROR_DELAY = 300

    # Задержка после успешного ввода
    COMPLETE_DELAY = 200

    # ==================================================
    # Звуки
    # ==================================================

    BUTTON_PRESS_SOUND = "assets/sounds/button press.mp3"
    BUTTON_PRESS_ERROR_SOUND = "assets/sounds/button press error.mp3"
    SEQUENCE_SUCCESS_SOUND = "assets/sounds/sequence success.mp3"
    GAME_OVER_SOUND = "assets/sounds/game over.mp3"

    # Варианты финального звука раунда — случайный выбор
    ROUND_OVER_SOUNDS = [
        "assets/sounds/round over.mp3",
        "assets/sounds/round over alt.mp3",
    ]

    # ==================================================
    # Разметка экрана (позиции элементов)
    #
    # Правятся в картинном редакторе: python main.py --edit
    # ==================================================

    DEFAULT_LAYOUT = {
        "round_label": {
            "anchor": "center",
            "pos": [103, 110],
        },
        "round_number": {
            "anchor": "center",
            "pos": [98, 135],
        },
        "score_value": {
            "anchor": "center",
            "pos": [730, 90],
        },
        "score_label": {
            "anchor": "center",
            "pos": [730, 120],
        },
        "stratagem_title": {
            "anchor": "center",
            "pos": [512, 155],
        },
        "arrows": {
            "anchor": "center",
            "pos": [512, 250],
        },
        "queue": {
            "anchor": "center",
            "pos": [250, 90],
        },
        "timer_bar": {
            "anchor": "topleft",
            "pos": [232, 355],
            "size": [560, 12],
        },
    }

    # Числовые параметры разметки (отступы, шаги)
    DEFAULT_METRICS = {
        "arrows_spacing": 70,
        "queue_spacing": 105,
    }

    # ==================================================
    # Очередь стратагем
    # ==================================================

    # Сколько стратагем одновременно видно в очереди
    QUEUE_VISIBLE = 5

    # Во сколько раз уменьшаются стратагемы
    SMALL_SCALE = 0.75

    # Отступ квадратной рамки вокруг текущей стратагемы
    SQUARE_MARGIN = 12

    # ==================================================
    # Инициализация
    # ==================================================

    def __init__(self, game):

        self.game = game

        # ==================================================
        # Размеры шрифтов задаются в редакторе
        # разметки (поле font_size у элемента)
        # и читаются при отрисовке в draw().
        # ==================================================

        # ==================================================
        # Разметка экрана
        # ==================================================

        self.layout = LayoutRegistry(
            "gameplay",
            self.DEFAULT_LAYOUT,
            self.DEFAULT_METRICS
        )

        # ==================================================
        # Фон
        # ==================================================

        self.background = pygame.image.load(
            "assets/images/ui/background.png"
        ).convert()

        self.background = pygame.transform.scale(
            self.background,
            (
                self.SCREEN_WIDTH,
                self.SCREEN_HEIGHT
            )
        )

        # ==================================================
        # Изображения стрелок
        # ==================================================

        self.arrow_images = {

            "UP": pygame.image.load(
                "assets/images/ui/U.png"
            ).convert_alpha(),

            "RIGHT": pygame.image.load(
                "assets/images/ui/R.png"
            ).convert_alpha(),

            "LEFT": pygame.image.load(
                "assets/images/ui/L.png"
            ).convert_alpha(),

            "DOWN": pygame.image.load(
                "assets/images/ui/D.png"
            ).convert_alpha(),
        }

        # ==================================================
        # Анимация стрелок
        # ==================================================

        self.completed = False
        self.round_finished = False

        self.complete_timer = 0

        self.arrow_animation_time = 100
        self.arrow_animation_progress = 0.0
        self.animating_arrow = -1

        self.waiting_for_completion = False

        # ==================================================
        # Менеджер раунда
        # ==================================================

        self.round_manager = self.game.round_manager

        # ==================================================
        # Изображения стратагем для очереди
        # ==================================================

        self.stratagem_images = {}

        for stratagem in self.round_manager.stratagems:

            image = pygame.image.load(
                stratagem.path
            ).convert_alpha()

            size = image.get_size()

            scale = min(
                80 / size[0],
                80 / size[1]
            )

            image = pygame.transform.smoothscale(
                image,
                (
                    max(1, int(size[0] * scale)),
                    max(1, int(size[1] * scale))
                )
            )

            self.stratagem_images[
                stratagem.id
            ] = image

        # Уменьшенные копии (80%) для будущих стратагем
        # в очереди — готовим заранее, чтобы не
        # масштабировать каждый кадр
        self.stratagem_images_small = {}

        for stratagem_id, image in self.stratagem_images.items():

            size = image.get_size()

            self.stratagem_images_small[
                stratagem_id
            ] = pygame.transform.smoothscale(
                image,
                (
                    max(1, int(size[0] * self.SMALL_SCALE)),
                    max(1, int(size[1] * self.SMALL_SCALE))
                )
            )

        # ==================================================
        # Состояние геймплея
        # ==================================================

        self.reset()

    # ==================================================
    # Сброс экрана к текущему состоянию раунда
    # ==================================================

    def reset(self, reset_timer=True):

        # Синхронизируемся с актуальным менеджером раунда:
        # новый RoundManager создаётся при возврате
        # на экран START после Game Over.
        self.round_manager = self.game.round_manager

        self.stratagem = self.round_manager.current_stratagem
        self.current_index =  0

        # Таймер раунда сбрасывается только при смене
        # раунда/начале геймплея, а не при смене комбинации.
        if reset_timer:

            self.time_remaining = self.STRATAGEM_TIME

            # Счётчик ошибок раунда — тоже только при
            # начале нового раунда.
            self.errors_in_round = 0

        self.input_error = False
        self.error_timer =  0
        self.error_index = -1
        self.completed = False
        self.complete_timer =  0
        self.round_finished = False
        self.waiting_for_completion = False

        # Индекс первой стратагемы в окне очереди.
        # Обновляется вместе со сменой комбинации
        # (next_stratagem), а не в момент продвижения
        # round_manager.current_index.
        self.queue_index = self.round_manager.current_index

    # ==================================================
    # Акцентный цвет
    #
    # Жёлтый в обычном режиме, красный — в последние
    # 2 секунды до истечения таймера.
    # ==================================================

    @property
    def accent_color(self):

        if self.time_remaining <= self.LOW_TIME_THRESHOLD:

            return self.DANGER_COLOR

        return self.SUCCESS_COLOR

    # ==================================================
    # Окрашивание изображения
    # ==================================================

    def color_image(self, image, color):

        colored = image.copy()

        overlay = pygame.Surface(
            colored.get_size(),
            pygame.SRCALPHA
        )

        overlay.fill(
            (*color, 255)
        )

        colored.blit(
            overlay,
            (0, 0),
            special_flags=pygame.BLEND_RGBA_MULT
        )

        return colored

    # ==================================================
    # Переход к следующей стратагеме
    # ==================================================

    def next_stratagem(self):

        # --------------------------------------------------
        # Новая стратагема
        #
        # RoundManager уже продвинул current_index,
        # когда стратагема была завершена в check_input().
        # Здесь только загружаем следующую стратагему.
        # --------------------------------------------------

        self.stratagem = self.round_manager.current_stratagem

        # Таймер НЕ сбрасываем — он общий на весь раунд.
        self.reset(reset_timer=False)

    # ==================================================
    # Обработка событий
    # ==================================================

    def handle_events(self, events):

        for event in events:

            if event.type == pygame.KEYDOWN:

                # ESC -> назад в меню
                if event.key == pygame.K_ESCAPE:

                    self.game.change_screen(
                        self.game.start_screen
                    )

    # ==================================================
    # Обновление
    # ==================================================

    def update(self):

        delta_time = self.game.clock.get_time()

        # ==================================================
        # Задержка после успешной стратагемы
        #
        # Таймер при этом НЕ останавливается: код
        # продолжает выполнение к блоку «Таймер».
        # ==================================================

        if self.completed:

            self.complete_timer -= delta_time

            if self.complete_timer <= 0:

                self.completed = False

                if self.round_finished:

                    # Начался подсчёт результатов —
                    # играем случайный звук конца раунда
                    self.game.audio.play_sfx(
                        random.choice(self.ROUND_OVER_SOUNDS)
                    )

                    self.game.change_screen(
                        self.game.round_score_screen
                    )

                else:

                    self.next_stratagem()

        # ==================================================
        # Анимация стрелки
        # ==================================================

        if self.animating_arrow >= 0:

            self.arrow_animation_progress += (
                delta_time
                / self.arrow_animation_time
            )

            if self.arrow_animation_progress >= 1.0:

                self.arrow_animation_progress = 1.0

                self.animating_arrow = -1

                # Последняя стрелка закончила анимацию.
                # Теперь можно начинать задержку
                # перед следующей стратагемой.
                if self.waiting_for_completion:

                    self.waiting_for_completion = False

                    self.completed = True

                    self.complete_timer = (
                        self.COMPLETE_DELAY
                    )

        # ==================================================
        # Задержка после ошибки
        #
        # Таймер при этом НЕ останавливается: код
        # продолжает выполнение к блоку «Таймер».
        # ==================================================

        if self.input_error:

            self.error_timer -= delta_time

            if self.error_timer <= 0:

                self.input_error = False

                self.error_index = -1

                self.current_index = 0

                # Таймер НЕ сбрасываем — он общий на весь раунд.

        # ==================================================
        # Таймер
        # ==================================================

        self.time_remaining -= delta_time

        if self.time_remaining <= 0:

            self.time_remaining = 0

            # ----------------------------------------------
            # Время вышло — игра окончена. Очки текущего
            # раунда переносим в общий счёт.
            # ----------------------------------------------

            self.round_manager.fail_round()

            self.game.audio.play_sfx(
                self.GAME_OVER_SOUND
            )

            self.game.change_screen(
                self.game.game_over_screen
            )

            return

        # ==================================================
        # Проверяем ввод
        # ==================================================

        # Во время ошибки ввод не обрабатываем
        if self.input_error:

            return

        # Клавиатура — один ввод за кадр
        for direction in (
            "UP",
            "DOWN",
            "LEFT",
            "RIGHT"
        ):

            if self.game.input.is_pressed(direction):

                self.check_input(direction)

                break

        # Сенсорные свайпы — обрабатываем по очереди все,
        # накопившиеся в очереди жестов за этот кадр
        while not self.input_error:

            gesture = self.game.input.pop_gesture()

            if gesture is None:

                break

            self.check_input(gesture)

    # ==================================================
    # Проверка ввода
    # ==================================================

    def check_input(self, direction):

        # Стратагема уже завершена и мы ждём перехода
        # к следующей — лишний ввод игнорируем.
        if self.current_index >= len(
            self.stratagem.code
        ):
            return

        expected = self.stratagem.code[
            self.current_index
        ]

        # ==================================================
        # Правильный ввод
        # ==================================================

        if direction == expected:

            print(
                f"Correct: {direction}"
            )

            self.game.audio.play_sfx(
                self.BUTTON_PRESS_SOUND
            )

            # ----------------------------------------------
            # Запускаем анимацию текущей стрелки
            # ----------------------------------------------

            self.animating_arrow = self.current_index

            self.arrow_animation_progress = 0.0

            # ----------------------------------------------
            # Сразу переходим к следующей стрелке.
            #
            # Анимация НЕ блокирует игровой процесс.
            # ----------------------------------------------

            self.current_index += 1

            # ----------------------------------------------
            # Проверяем завершение стратагемы
            # ----------------------------------------------

            if self.current_index >= len(
                self.stratagem.code
            ):

                print(
                    "STRATAGEM COMPLETE"
                )

                self.game.audio.play_sfx(
                    self.SEQUENCE_SUCCESS_SOUND
                )

                # ----------------------------------------------
                # Бонус времени за выполненную стратагему
                # ----------------------------------------------

                self.time_remaining += (
                    self.TIME_BONUS_PER_STRATAGEM
                )

                # Сообщаем RoundManager,
                # что стратагема завершена
                self.round_finished = (
                    self.round_manager.complete_stratagem()
                )

                # ----------------------------------------------
                # Раунд завершён — считаем бонусы:
                # время и «идеал» фиксируем прямо сейчас,
                # пока пауза ещё не потратила остаток таймера.
                # ----------------------------------------------

                if self.round_finished:

                    time_bonus = int(
                        self.time_remaining
                        / self.STRATAGEM_TIME
                        * 100
                    )

                    self.round_manager.complete_round(
                        time_bonus,
                        self.errors_in_round == 0
                    )

                # COMPLETE_DELAY начнётся
                # после завершения анимации последней стрелки
                self.waiting_for_completion = True

            return

        # ==================================================
        # Неправильный ввод
        # ==================================================

        else:

            print(
                f"Wrong: {direction}, "
                f"expected {expected}"
            )

            self.game.audio.play_sfx(
                self.BUTTON_PRESS_ERROR_SOUND
            )

            # ----------------------------------------------
            # Запоминаем ошибку
            # ----------------------------------------------

            self.errors_in_round += 1

            self.input_error = True

            self.error_timer = (
                self.ERROR_DELAY
            )

            # ----------------------------------------------
            # Запоминаем индекс ошибочной стрелки.
            #
            # Сама ошибочная стрелка НЕ будет окрашена.
            # Красными будут только уже введённые.
            # ----------------------------------------------

            self.error_index = self.current_index

    # ==================================================
    # Отрисовка текста
    # ==================================================

    def draw_text(
        self,
        screen,
        text,
        size,
        color,
        position,
        glow=False,
        glow_color=None,
        radius=None,
        intensity=0.7,
    ):

        bloom.blit_bloom(
            screen,
            text,
            size,
            position,
            color,
            glow_color=glow_color,
            radius=radius if glow else 0,
            intensity=intensity,
        )

    # ==================================================
    # Отрисовка очереди стратагем
    # ==================================================

    def draw_queue(self, screen):

        queue = self.round_manager.queue

        queue_length = len(queue)

        if queue_length <= 0:

            return

        # ----------------------------------------------
        # Окно из QUEUE_VISIBLE стратагем:
        # слева — текущая, правее — следующие.
        #
        # Окно сдвигается влево в момент смены
        # комбинации (next_stratagem): завершённая
        # стратагема просто исчезает, а окно начинает
        # со следующей.
        # ----------------------------------------------

        base_index = self.queue_index

        visible_count = min(
            self.QUEUE_VISIBLE,
            queue_length - base_index
        )

        if visible_count <= 0:

            return

        spacing = self.layout.metric("queue_spacing")

        # Базовые координаты первого элемента очереди
        queue_x, y = self.layout.pos("queue")

        start_x = queue_x

        for i in range(
            visible_count
        ):

            queue_index = base_index + i

            stratagem = queue[queue_index]

            # Самая левая (текущая) стратагема — полный
            # размер. Остальные — на 20% меньше.
            if i == 0:

                image = self.stratagem_images[
                    stratagem.id
                ]

            else:

                image = self.stratagem_images_small[
                    stratagem.id
                ]

            # Текущая стратагема — полная яркость
            if queue_index == self.queue_index:

                image.set_alpha(255)

            # Будущие — приглушены
            else:

                image.set_alpha(
                    self.INACTIVE_ALPHA
                )

            x = start_x + i * spacing

            rect = image.get_rect(
                center=(x, y)
            )

            screen.blit(
                image,
                rect
            )

            # Самая левая стратагема обведена
            # квадратной рамкой
            if i == 0:

                side = (
                    max(rect.width, rect.height)
                    + self.SQUARE_MARGIN
                )

                border_rect = pygame.Rect(
                    0,
                    0,
                    side,
                    side
                )

                border_rect.center = rect.center

                pygame.draw.rect(
                    screen,
                    self.accent_color,
                    border_rect,
                    width=2
                )

    # ==================================================
    # Отрисовка
    # ==================================================

    def draw(self, screen):

        # ==================================================
        # Фон
        # ==================================================

        screen.blit(
            self.background,
            (0, 0)
        )

        # ==================================================
        # РАУНД
        # ==================================================

        self.draw_text(
            screen,
            f"Round",
            self.layout.font_size("round_label") or 18,
            self.TEXT_COLOR,
            self.layout.pos("round_label")
        )

        self.draw_text(
            screen,
            f"{self.round_manager.round_number}",
            self.layout.font_size("round_number") or 32,
            self.accent_color,
            self.layout.pos("round_number"),
            glow=True,
        )

        # ==================================================
        # ОЧЕРЕДЬ
        # ==================================================

        self.draw_queue(
            screen
        )

        # ==================================================
        # СЧЁТ
        # ==================================================

        self.draw_text(
            screen,
            f"{self.round_manager.score + self.round_manager.round_score:,}",
            self.layout.font_size("score_value") or 32,
            self.accent_color,
            self.layout.pos("score_value"),
            glow=True,
        )

        self.draw_text(
            screen,
            f"SCORE",
            self.layout.font_size("score_label") or 18,
            self.TEXT_COLOR,
            self.layout.pos("score_label")
        )

        # ==================================================
        # Название текущей стратагемы
        # ==================================================

        self.draw_text(
            screen,
            self.stratagem.title,
            self.layout.font_size("stratagem_title") or 42,
            self.TEXT_COLOR,
            self.layout.pos("stratagem_title"),
            glow=True,
        )

        # ==================================================
        # Стрелки
        # ==================================================

        total_arrows = len(
            self.stratagem.code
        )

        spacing = self.layout.metric("arrows_spacing")

        start_x = (
            self.SCREEN_WIDTH // 2
            - ((total_arrows - 1) * spacing // 2)
        )

        arrow_y = self.layout.pos("arrows")[1]

        for index, direction in enumerate(
            self.stratagem.code
        ):

            base_image = self.arrow_images[
                direction
            ]

            # ==================================================
            # ОШИБКА
            # ==================================================

            if self.input_error:

                # Красим только уже правильно
                # введённые стрелки
                if index < self.error_index:

                    arrow = self.color_image(
                        base_image,
                        self.ERROR_COLOR
                    )

                    arrow.set_alpha(255)

                else:

                    arrow = base_image.copy()

                    #arrow.set_alpha(
                    #    self.INACTIVE_ALPHA
                    #)

            # ==================================================
            # УЖЕ ПРАВИЛЬНО ВВЕДЕНА
            # ==================================================

            #elif index < self.current_index:

            elif index < self.current_index:

                if index == self.animating_arrow:

                    arrow = self.get_animated_arrow(
                        base_image,
                        self.arrow_animation_progress
                    )

                elif index < self.current_index:

                    arrow = self.color_image(
                        base_image,
                        self.SUCCESS_COLOR
                    )

                    arrow.set_alpha(255)

                else:

                    arrow = base_image.copy()

                    arrow.set_alpha(
                        self.INACTIVE_ALPHA
                    )

                arrow.set_alpha(255)
            
            # ==================================================
            # ЕЩЁ НЕ НАЖАТА
            # ==================================================

            else:

                arrow = base_image.copy()

                #arrow.set_alpha(
                #    self.INACTIVE_ALPHA
                #)

            # ==================================================
            # Положение стрелки
            # ==================================================

            arrow_rect = arrow.get_rect(
                center=(
                    start_x + index * spacing,
                    arrow_y
                )
            )

            screen.blit(
                arrow,
                arrow_rect
            )

        # ==================================================
        # ПОЛОСА ВРЕМЕНИ
        # ==================================================

        bar_rect = self.layout.rect("timer_bar")

        bar_x = bar_rect.x
        bar_y = bar_rect.y
        bar_width = bar_rect.width
        bar_height = bar_rect.height

        # --------------------------------------------------
        # Фон полосы
        # --------------------------------------------------

        pygame.draw.rect(
            screen,
            (70, 70, 70),
            (
                bar_x,
                bar_y,
                bar_width,
                bar_height
            ),
            border_radius=6
        )

        # --------------------------------------------------
        # Оставшееся время
        # --------------------------------------------------

        time_ratio = (
            self.time_remaining
            / self.STRATAGEM_TIME
        )

        current_width = int(
            bar_width * time_ratio
        )

        if current_width > 0:

            pygame.draw.rect(
                screen,
                self.accent_color,
                (
                    bar_x,
                    bar_y,
                    current_width,
                    bar_height
                ),
                border_radius=6
            )

    def get_animated_arrow(
        self,
        image,
        progress
    ):

        # ----------------------------------------------
        # Цвет начала
        # ----------------------------------------------

        start_color = (
            255,
            255,
            255
        )

        # ----------------------------------------------
        # Цвет конца
        # ----------------------------------------------

        end_color = self.SUCCESS_COLOR

        # ----------------------------------------------
        # Интерполяция RGB
        # ----------------------------------------------

        color = (

            int(
                start_color[0]
                + (
                    end_color[0]
                    - start_color[0]
                )
                * progress
            ),

            int(
                start_color[1]
                + (
                    end_color[1]
                    - start_color[1]
                )
                * progress
            ),

            int(
                start_color[2]
                + (
                    end_color[2]
                    - start_color[2]
                )
                * progress
            )
        )

        arrow = self.color_image(
            image,
            color
        )


        arrow.set_alpha(255)

        return arrow