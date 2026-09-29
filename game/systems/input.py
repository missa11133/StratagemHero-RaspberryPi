import pygame


class InputManager:

    # Минимальное смещение пальца/мыши (в пикселях),
    # необходимое для засчитывания свайпа.
    SWIPE_THRESHOLD = 30

    def __init__(self, screen_size):

        self.screen_w, self.screen_h = screen_size

        self.pressed = set()

        self.key_map = {
            pygame.K_UP: "UP",
            pygame.K_DOWN: "DOWN",
            pygame.K_LEFT: "LEFT",
            pygame.K_RIGHT: "RIGHT",

            pygame.K_w: "UP",
            pygame.K_s: "DOWN",
            pygame.K_a: "LEFT",
            pygame.K_d: "RIGHT",
        }

        # ==================================================
        # Тапы — короткие касания без смещения.
        # Нужны кнопкам меню на сенсорном экране.
        # ==================================================

        self.taps = []

        # ==================================================
        # Очередь жестов.
        #
        # Каждый свайп кладёт сюда направление, геймплей
        # забирает их по одному через pop_gesture(). Очередь
        # нужна, чтобы быстрые серии свайпов (в том числе
        # повторы в одном направлении) не терялись.
        # ==================================================

        self._gesture_queue = []

        # Состояние текущего жеста
        self._tracking = False
        self._finger_id = None
        self._gesture_source = None
        self._anchor = (0, 0)

        # Направление последнего засчитанного свайпа.
        # Повтор того же направления в рамках одного касания
        # не засчитывается: нужна смена направления или
        # поднятие пальца (новое касание сбрасывает поле).
        self._last_direction = None

        # Жесты записываются в очередь только во время
        # геймплея. На остальных экранах (меню, GET READY,
        # результаты, заставка) свайпы не должны попадать
        # в очередь жестов и «воспроизводиться» при вводе
        # комбинации.
        #
        # Само отслеживание жеста идёт на всех экранах: меню
        # (START) реагирует на сам факт свайпа — «любой ввод
        # стратагемы начинает раунд». Очередь же направлений
        # наполняется только при gesture_enabled == True.
        self.gesture_enabled = False

        # Любой засчитанный свайп, в том числе вне геймплея.
        # Читается через consume_gesture() и живёт до своего
        # потребления или до начала следующего update().
        self.gesture_detected = False

    def update(self, events):

        self.pressed.clear()

        self.taps.clear()

        self.gesture_detected = False

        for event in events:

            # ==============================================
            # Клавиатура
            # ==============================================

            if event.type == pygame.KEYDOWN:

                if event.key in self.key_map:

                    self.pressed.add(
                        self.key_map[event.key]
                    )

            # ==============================================
            # Сенсорный экран (нативные FINGER-события SDL2)
            # ==============================================

            elif event.type == pygame.FINGERDOWN:

                x = event.x * self.screen_w
                y = event.y * self.screen_h

                # Жест отслеживаем на всех экранах: в геймплее
                # его направление идёт в очередь, в меню сам
                # факт свайпа начинает раунд. Тап добавляем
                # тоже всегда — он нужен кнопкам меню.
                self._begin_gesture(
                    event.finger_id,
                    x,
                    y,
                )

                self._add_tap(x, y)

            elif event.type == pygame.FINGERMOTION:

                if (
                    self._tracking
                    and self._gesture_source == "finger"
                    and event.finger_id == self._finger_id
                ):

                    self._motion_gesture(
                        event.x * self.screen_w,
                        event.y * self.screen_h,
                    )

            elif event.type == pygame.FINGERUP:

                if (
                    self._tracking
                    and self._gesture_source == "finger"
                    and event.finger_id == self._finger_id
                ):

                    self._end_gesture()

            # ==============================================
            # Мышь — fallback для тестирования на десктопе
            # и устройств, где касания приходят как мышь.
            # ==============================================

            elif event.type == pygame.MOUSEBUTTONDOWN:

                if event.button == 1 and not self._tracking:

                    # Жест отслеживаем на всех экранах (в меню
                    # свайп начинает раунд). Тап добавляем тоже
                    # всегда — он нужен кнопкам меню.
                    self._begin_gesture(
                        None,
                        event.pos[0],
                        event.pos[1],
                    )

                    self._add_tap(
                        event.pos[0],
                        event.pos[1],
                    )

            elif event.type == pygame.MOUSEMOTION:

                if (
                    self._tracking
                    and self._gesture_source == "mouse"
                ):

                    self._motion_gesture(
                        event.pos[0],
                        event.pos[1],
                    )

            elif event.type == pygame.MOUSEBUTTONUP:

                if (
                    event.button == 1
                    and self._tracking
                    and self._gesture_source == "mouse"
                ):

                    self._end_gesture()

    # ======================================================
    # Управление жестом
    # ======================================================

    def _begin_gesture(self, finger_id, x, y):

        self._tracking = True

        self._finger_id = finger_id

        self._gesture_source = (
            "finger" if finger_id is not None else "mouse"
        )

        self._anchor = (x, y)

        # Новое касание — повтор того же направления снова
        # допустим (можно «нажать» UP дважды двумя свайпами).
        self._last_direction = None

    def _motion_gesture(self, x, y):

        dx = x - self._anchor[0]
        dy = y - self._anchor[1]

        # Не дотянули до порога — направления ещё нет
        if (
            abs(dx) < self.SWIPE_THRESHOLD
            and abs(dy) < self.SWIPE_THRESHOLD
        ):

            return

        # Направление свайпа — по доминирующей оси
        if abs(dx) >= abs(dy):

            direction = "RIGHT" if dx > 0 else "LEFT"

        else:

            direction = "DOWN" if dy > 0 else "UP"

        # Повторное «нажатие» в том же направлении не
        # засчитывается в рамках одного касания: один жест —
        # одно нажатие. Снова «нажать» ту же сторону можно
        # либо после смены направления, либо после поднятия
        # пальца (нового касания).
        if direction == self._last_direction:

            return

        # Свайп засчитан: геймплей читает его направление из
        # очереди, меню (START) — сам факт жеста.
        self.gesture_detected = True

        # В очередь направление попадает только в геймплее:
        # свайпы на остальных экранах не должны
        # «воспроизводиться» при вводе комбинации.
        if self.gesture_enabled:

            self._gesture_queue.append(direction)

        self._last_direction = direction

        # Якорь сдвигается в точку засчитывания — следующий
        # свайп меряется от неё.
        self._anchor = (x, y)

    def _end_gesture(self):

        self._tracking = False

        self._finger_id = None

        self._gesture_source = None

        self._last_direction = None

    def _cancel_gesture(self):

        # Сброс незавершённого жеста без записи в очередь.
        # Нужен при смене экрана: палец/кнопка могли быть
        # нажаты в момент перехода, и их движение не должно
        # «продолжиться» на другом экране.
        self._tracking = False

        self._finger_id = None

        self._gesture_source = None

        self._anchor = (0, 0)

        self._last_direction = None

    def set_gesture_enabled(self, enabled):

        if self.gesture_enabled == enabled:

            return

        self.gesture_enabled = enabled

        # Очередь жестов нужна только геймплею: всё, что
        # накопилось вне геймплея (или осталось после его
        # завершения), больше не актуально.
        self._gesture_queue.clear()

        # Незавершённое касание не должно «продолжиться»
        # на новом экране.
        self._cancel_gesture()

    def _add_tap(self, x, y):

        # Защита от дублей: SDL2/ОС может продублировать
        # одно касание FINGER- и мышиными событиями.
        if self.taps:

            last_x, last_y = self.taps[-1]

            if (
                abs(last_x - x) < 5
                and abs(last_y - y) < 5
            ):

                return

        self.taps.append(
            (int(x), int(y))
        )

    # ======================================================
    # Чтение ввода
    # ======================================================

    def pop_gesture(self):

        if self._gesture_queue:

            return self._gesture_queue.pop(0)

        return None

    def consume_gesture(self):
        """Был ли за это обновление засчитан свайп.

        Возвращает True один раз на каждый засчитанный
        свайп — независимо от того, включена ли очередь
        жестов. Этого достаточно экранам меню: на START
        свайп начинает раунд (как раньше кнопка START).
        Геймплей читает сами направления через
        pop_gesture().
        """

        if not self.gesture_detected:

            return False

        self.gesture_detected = False

        return True

    def is_pressed(self, direction):

        return direction in self.pressed