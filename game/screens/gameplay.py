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
    ERROR_COLOR = (191, 81, 51) #(254, 134, 74) #(222, 123, 108)
    TITLE_COLOR = (0, 0, 0)

    # Неактивные стрелки
    INACTIVE_ALPHA = 255 #90

    # Цвет таймера
    TIMER_COLOR = (255, 238, 0)

    # Порог «опасного» времени, мс (последние 2 секунды)
    LOW_TIME_THRESHOLD = 2000

    # Красный цвет при критическом таймере
    DANGER_COLOR = (222, 40, 40)

    # ==================================================
    # Счётчик FPS (только для тестов)
    #
    # Выводится поверх всей графики геймплея в правом
    # верхнем углу. После тестов выключается флагом
    # SHOW_FPS = False (на другие экраны не выходит).
    # ==================================================

    # Показывать счётчик кадров
    SHOW_FPS = True

    # Как часто обновляется значение, миллисекунды.
    # За 500 мс успевает набраться достаточно кадров,
    # чтобы среднее не скакало из кадра в кадр.
    FPS_UPDATE_INTERVAL = 500

    FPS_FONT_SIZE = 22
    FPS_COLOR = (0, 255, 140)

    FPS_POSITION = (12, 12)

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
            "pos": [512, 155]
        },
        "stratagem_title_background": {
            "anchor": "center",
            "pos": [512, 155],
            "size": [840, 72],
        },
        "arrows": {
            "anchor": "center",
            "pos": [512, 250],
        },
        "queue": {
            "anchor": "center",
            "pos": [250, 90],
            "size": [106, 106],
        },
        "timer_bar": {
            "anchor": "topleft",
            "pos": [232, 355],
            "size": [560, 12],
        },
    }

    # Числовые параметры разметки (отступы, шаги)
    DEFAULT_METRICS = {

        # Шаг между центрами стрелок.
        "arrows_spacing": 45 + 1,
        "queue_spacing": -50    ,
    }

    # ==================================================
    # Очередь стратагем
    # ==================================================

    # Сколько стратагем одновременно видно в очереди
    QUEUE_VISIBLE = 6

    # Во сколько раз уменьшаются стратагемы
    SMALL_SCALE = 0.5

    # Отступ квадратной рамки вокруг текущей стратагемы
    SQUARE_MARGIN = 12

    # ==================================================
    # Стрелки
    # ==================================================

    # Размер картинки стрелки на экране, пиксели
    ARROW_SIZE = (45, 45)

    # ==================================================
    # Свечение графики (bloom)
    # ==================================================

    # Радиус отвечает за ШИРИНУ ореола, интенсивность — за его
    # яркость: с ростом радиуса тот же свет размазывается дальше
    # и у края бледнеет (у плашки добавка у края 46 при R=10 и
    # 39 при R=22), поэтому широкое свечение делается вместе
    # с интенсивностью ближе к 1.0.

    # Стрелки ввода (картинка 45x45)
    ARROW_GLOW_RADIUS = 16
    ARROW_GLOW_INTENSITY = 1.0

    # Сколько ступеней цвета у ореола анимируемой стрелки.
    ARROW_GLOW_ANIMATION_STEPS = 5

    # Плашка под названием стратагемы (484x26)
    TITLE_GLOW_RADIUS = 22
    TITLE_GLOW_INTENSITY = 1.0

    # Полоса таймера (472x18)
    TIMER_GLOW_RADIUS = 14
    TIMER_GLOW_INTENSITY = 1.0

    # Шаг длины, с которым кэшируется ореол короткого хвоста
    # полосы (последние шесть радиусов таймера)
    TIMER_GLOW_WIDTH_STEP = 2

    # Рамка вокруг текущей стратагемы в очереди: радиус у неё
    # самый маленький, потому что контур тонкий (2 px) — свет
    # у тонкой линии размазывается сильнее, чем у большой
    # заливки (замер яркости добавки у контура: R=4 даёт 36,
    # R=6 — 24, R=8 — 12, R=12 — ореол пропадает вовсе)
    QUEUE_FRAME_WIDTH = 2
    QUEUE_GLOW_RADIUS = 6
    QUEUE_GLOW_INTENSITY = 1.0

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
        # Тестовый счётчик FPS
        #
        # Накопители считаются только пока экран геймплея
        # отрисовывается, поэтому сбрасываются в reset()
        # не должны.
        # ==================================================

        self.fps_value = 0.0
        self.fps_frames = 0
        self.fps_elapsed = 0
        self.fps_surface = None
        self.fps_background = None

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

        # Все стрелки приводятся к единому размеру ARROW_SIZE
        for direction in self.arrow_images:

            self.arrow_images[direction] = (
                pygame.transform.smoothscale(
                    self.arrow_images[direction],
                    self.ARROW_SIZE
                )
            )

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
                128 / size[0],
                128 / size[1]
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
        anchor="center"
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
            anchor=anchor,
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
            if i == 0:

                image = self.stratagem_images[
                    stratagem.id
                ]
                x = start_x + i * spacing

            else:

                image = self.stratagem_images_small[
                    stratagem.id
                ]
                x = start_x + i * spacing + 40

            

            rect = image.get_rect(
                center=(x, y)
            )

            # ----------------------------------------------
            # Рамка вокруг текущей стратагемы.
            #
            # Считается до картинки: ореол рамки должен лечь
            # ПОД иконку, иначе свет подмешался бы к самой
            # иконке. Контур рисуется после картинки — как
            # и раньше.
            # ----------------------------------------------

            border_rect = None

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

                bloom.blit_bloom_rect(
                    screen,
                    border_rect,
                    self.accent_color,
                    radius=self.QUEUE_GLOW_RADIUS,
                    intensity=self.QUEUE_GLOW_INTENSITY,
                    width=self.QUEUE_FRAME_WIDTH,
                )

            screen.blit(
                image,
                rect
            )

            # Самая левая стратагема обведена
            # квадратной рамкой
            if border_rect is not None:

                pygame.draw.rect(
                    screen,
                    self.accent_color,
                    border_rect,
                    width=self.QUEUE_FRAME_WIDTH
                )

    # ==================================================
    # Тестовый счётчик FPS
    # ==================================================

    def update_fps_counter(self):
        """Накопление кадров и пересчёт значения FPS.

        Среднее считается вручную, а не через
        clock.get_fps(): тот сглажен pygame по последним
        кадрам и отдаёт 0 первые несколько тиков.
        """

        if not self.SHOW_FPS:
            return

        self.fps_frames += 1

        # Время между последними двумя tick() главного цикла
        self.fps_elapsed += self.game.clock.get_time()

        if self.fps_elapsed >= self.FPS_UPDATE_INTERVAL:

            self.fps_value = (
                self.fps_frames * 1000.0 / self.fps_elapsed
            )

            self.fps_frames = 0
            self.fps_elapsed = 0

            # Текст и подложка пересобираются только вместе
            # со значением, а не каждый кадр
            self.fps_surface = None
            self.fps_background = None

    def draw_fps(self, screen):
        """Оверлей FPS поверх всей графики (только тесты)."""

        if not self.SHOW_FPS:
            return

        if self.fps_surface is None:

            # До первого измерения (первые 500 мс) показываем
            # прочерк, а не ноль
            text = (
                f"FPS: {self.fps_value:.0f}"
                if self.fps_value > 0
                else "FPS: --"
            )

            self.fps_surface = bloom.get_font(
                self.FPS_FONT_SIZE
            ).render(
                text,
                True,
                self.FPS_COLOR,
            )

            # Полупрозрачная подложка: текст читается
            # поверх яркого фона и свечения
            self.fps_background = pygame.Surface(
                self.fps_surface.get_size(),
                pygame.SRCALPHA,
            )

            self.fps_background.fill((0, 0, 0, 150))

        rect = self.fps_surface.get_rect(
            topright=self.FPS_POSITION
        )

        screen.blit(self.fps_background, rect)
        screen.blit(self.fps_surface, rect)

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
        #
        # Обе надписи блока рисуются со свечением:
        # "Round" — белым (TEXT_COLOR), номер раунда —
        # акцентным цветом. Цвет свечения не задаём:
        # glow_color по умолчанию берётся равным цвету
        # текста, а радиус — bloom.default_radius(size).
        # Обе подписи статичны, поэтому ореол считается
        # один раз и дальше берётся из кэша bloom.
        # ==================================================

        self.draw_text(
            screen,
            f"Round",
            self.layout.font_size("round_label") or 18,
            self.TEXT_COLOR,
            self.layout.pos("round_label"),
            glow=True,
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
            anchor="midright"
        )

        self.draw_text(
            screen,
            f"SCORE",
            self.layout.font_size("score_label") or 18,
            self.TEXT_COLOR,
            self.layout.pos("score_label"),
            glow=True,
        )

        # ==================================================
        # Название текущей стратагемы
        # ==================================================

        # Плашка под названием: рисуется первой, чтобы текст
        # лёг поверх неё. Цвет плашки — SUCCESS_COLOR,
        # цвет текста — TITLE_COLOR (см. константы выше).
        #
        # Свечение у названия выключено: glow_color по
        # умолчанию берётся равным цвету текста, то есть
        # ореол был бы чёрным (нулевая добавка при
        # BLEND_RGB_ADD) — только лишний рендер и размытие.
        background_rect = self.layout.rect(
            "stratagem_title_background"
        )

        # Ореол плашки: под самой плашкой, чтобы аддитивный
        # слой не подмешивался к её жёлтой заливке.
        bloom.blit_bloom_rect(
            screen,
            background_rect,
            self.SUCCESS_COLOR,
            radius=self.TITLE_GLOW_RADIUS,
            intensity=self.TITLE_GLOW_INTENSITY,
        )

        pygame.draw.rect(
            screen,
            self.SUCCESS_COLOR,
            background_rect
        )

        self.draw_text(
            screen,
            self.stratagem.title,
            self.layout.font_size("stratagem_title") or 42,
            self.TITLE_COLOR,
            self.layout.pos("stratagem_title")
        )

        # ==================================================
        # Стрелки
        # ==================================================

        total_arrows = len(
            self.stratagem.code
        )

        # Шаг между центрами стрелок из разметки.
        # Текущее значение 51 = ширина стрелки 45 + зазор 6
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

            # Цвет ореола стрелки. Он совпадает с цветом самой
            # стрелки, а у исходной (белой) картинки ореол берёт
            # цвет из неё самой — поэтому здесь None.
            glow_color = None

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

                    glow_color = self.ERROR_COLOR

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

                    glow_color = self.get_arrow_glow_color(
                        self.arrow_animation_progress
                    )

                elif index < self.current_index:

                    arrow = self.color_image(
                        base_image,
                        self.SUCCESS_COLOR
                    )

                    glow_color = self.SUCCESS_COLOR

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

            # Ореол стрелки: под самой стрелкой, цветом её
            # текущего состояния. Ключ кэша — направление:
            # цвет уже входит в него отдельно.
            bloom.blit_bloom_image(
                screen,
                arrow,
                arrow_rect,
                color=glow_color,
                radius=self.ARROW_GLOW_RADIUS,
                intensity=self.ARROW_GLOW_INTENSITY,
                key=direction,
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
            )
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

        # --------------------------------------------------
        # Ореол заливки
        #
        # Рисуется под заливкой и следует за её длиной, поэтому
        # светится ровно та часть полосы, которая ещё осталась
        # (и меняет цвет вместе с accent_color в последние
        # секунды раунда).
        # --------------------------------------------------

        bloom.blit_bloom_bar(
            screen,
            bar_rect,
            current_width,
            self.accent_color,
            radius=self.TIMER_GLOW_RADIUS,
            intensity=self.TIMER_GLOW_INTENSITY,
            width_step=self.TIMER_GLOW_WIDTH_STEP,
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
                )
            )

        # ==================================================
        # Тестовый счётчик FPS — последним, поверх всего
        # ==================================================

        self.update_fps_counter()
        self.draw_fps(screen)

    def get_animated_arrow(
        self,
        image,
        progress
    ):

        # Цвет анимации вынесен в отдельный метод: тот же цвет
        # нужен и ореолу стрелки (bloom).
        color = self.get_animated_color(
            progress
        )

        arrow = self.color_image(
            image,
            color
        )


        arrow.set_alpha(255)

        return arrow

    # ==================================================
    # Цвет анимируемой стрелки
    # ==================================================

    def get_animated_color(self, progress):
        """Цвет стрелки в анимации ввода: белый — акцентный."""

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

        return (

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

    def get_arrow_glow_color(self, progress):
        """Цвет ореола анимируемой стрелки, округлённый по ступеням.

        Цвет стрелки в анимации меняется каждый кадр, а сборка
        ореола стоит около миллисекунды. Поэтому прогресс сначала
        округляется до ARROW_GLOW_ANIMATION_STEPS ступеней: за
        100 мс анимации кэш ореолов пополняется не больше пяти
        раз вместо каждого кадра.
        """

        steps = max(
            1,
            self.ARROW_GLOW_ANIMATION_STEPS
        )

        stepped = min(
            steps,
            int(progress * steps + 0.5)
        ) / steps

        return self.get_animated_color(
            stepped
        )