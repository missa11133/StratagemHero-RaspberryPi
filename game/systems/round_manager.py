import random


class RoundManager:

    THEMATIC_ROUND_INTERVAL = 3
    THEMATIC_PERCENT = 0.5

    # Код длиной >= этой величины считается «длинным».
    # В раунд попадает не более половины таких
    # комбинаций от размера очереди.
    LONG_CODE_LENGTH = 6

    ALLOWED_CATEGORIES = [
        "Backpacks",
        "Eagle Strikes",
        #"Emplacements",
        #"Mission Stratagems",
        "Orbital Strikes",
        #"Sentries",
        "Support Weapons",
        #"Vehicles",
    ]
    
    def __init__(self, stratagems):

        self.stratagems = stratagems

        self.round_number = 1

        self.score = 50604615

        self.queue = []

        self.current_index = 0

        self.round_score = 0

        self.round_bonus = 35825
        self.time_bonus = 29
        self.perfect_bonus = 100
        self.round_total = 0

        self.create_round()
        

    # ==================================================
    # Создание нового раунда
    # ==================================================

    def create_round(self):

        # Выбираем случайные стратагемы
        enabled_stratagems = [
            stratagem
            for stratagem in self.stratagems
            if stratagem.enable
        ]

        if self.round_number <= 10 :
            STRATAGEMS_PER_ROUND = 5 + self.round_number
        else :
            STRATAGEMS_PER_ROUND = 16        

        queue_size = STRATAGEMS_PER_ROUND

        # ==================================================
        # Обычный раунд
        # ==================================================

        if self.round_number % self.THEMATIC_ROUND_INTERVAL != 0:

            # Лимит длинных комбинаций: половина очереди
            max_long = queue_size // 2

            long_used = 0

            self.queue = []

            for _ in range(queue_size):

                stratagem = self._pick_stratagem(
                    enabled_stratagems,
                    long_used,
                    max_long
                )

                if len(stratagem.code) >= self.LONG_CODE_LENGTH:

                    long_used += 1

                self.queue.append(stratagem)

            self.theme_category = None

            self.current_index = 0
            self.round_score = 0
            self.round_bonus = 0
            self.time_bonus = 0
            self.perfect_bonus = 0
            self.round_total = 0

            return

        # ==================================================
        # Тематический раунд
        # ==================================================

        categories = list(
            set(
                stratagem.type
                for stratagem in enabled_stratagems
                if stratagem.type in self.ALLOWED_CATEGORIES
            )
        )

        self.theme_category = random.choice(
            categories
        )

        print(
            self.theme_category
        )

        # --------------------------------------------------
        # Стратагемы выбранной категории
        # --------------------------------------------------

        thematic_stratagems = [
            stratagem
            for stratagem in enabled_stratagems
            if stratagem.type == self.theme_category
        ]

        # --------------------------------------------------
        # Остальные категории
        # --------------------------------------------------

        other_stratagems = [
            stratagem
            for stratagem in enabled_stratagems
            if stratagem.type != self.theme_category
        ]

        # ==================================================
        # Количество тематических
        # ==================================================

        thematic_count = (
            queue_size + 1
        ) // 2

        other_count = (
            queue_size - thematic_count
        )

        # ==================================================
        # Формируем очередь С повторениями
        # ==================================================

        self.queue = []

        # Лимит длинных комбинаций: половина очереди.
        # Счётчик общий на весь раунд (обе половины).
        max_long = queue_size // 2

        long_used = 0

        # Тематические
        for _ in range(thematic_count):

            stratagem = self._pick_stratagem(
                thematic_stratagems,
                long_used,
                max_long
            )

            if len(stratagem.code) >= self.LONG_CODE_LENGTH:

                long_used += 1

            self.queue.append(stratagem)

        # Остальные
        for _ in range(other_count):

            stratagem = self._pick_stratagem(
                other_stratagems,
                long_used,
                max_long
            )

            if len(stratagem.code) >= self.LONG_CODE_LENGTH:

                long_used += 1

            self.queue.append(stratagem)

        # ==================================================
        # Перемешиваем очередь
        # ==================================================

        random.shuffle(
            self.queue
        )

        self.current_index = 0

        self.round_score = 0
        self.round_bonus = 0
        self.time_bonus = 0
        self.perfect_bonus = 0
        self.round_total = 0

    # ==================================================
    # Выбор стратагемы с учётом лимита длинных комбинаций
    # ==================================================

    def _pick_stratagem(self, pool, long_used, max_long):

        # Лимит исчерпан — берём только короткие
        if long_used >= max_long:

            short_pool = [
                stratagem
                for stratagem in pool
                if len(stratagem.code) < self.LONG_CODE_LENGTH
            ]

            # Если в пуле нет коротких — страховка:
            # берём из всего пула, иначе очередь
            # не заполнится
            if short_pool:

                return random.choice(short_pool)

        return random.choice(pool)

    # ==================================================
    # Текущая стратагема
    # ==================================================

    @property
    def current_stratagem(self):

        return self.queue[
            self.current_index
        ]

    # ==================================================
    # Завершение текущей стратагемы
    # ==================================================

    def complete_stratagem(self):

        self.round_score += len(
            self.current_stratagem.code
        ) * 5

        self.current_index += 1

        # ----------------------------------------------
        # Весь раунд завершён
        #
        # Счёт НЕ прибавляем к score здесь — начисление
        # происходит на экране результатов (next_round).
        # Иначе в углу геймплея round_score учитывался
        # бы дважды.
        # ----------------------------------------------

        if self.current_index >= len(self.queue):

            return True

        return False

    def complete_round(self, time_bonus, perfect):

        # ==================================================
        # Бонус за раунд: 50 + номер раунда * 25
        # ==================================================

        self.round_bonus = 50 + self.round_number * 25

        # ==================================================
        # Бонус за время: проценты оставшегося времени
        # ==================================================

        self.time_bonus = time_bonus

        # ==================================================
        # Бонус за идеал: +100, если не было ошибок
        # ==================================================

        self.perfect_bonus = 100 if perfect else 0

        # ==================================================
        # Итог раунда: счёт за стратагемы + все бонусы
        # ==================================================

        self.round_total = (
            self.round_score
            + self.round_bonus
            + self.time_bonus
            + self.perfect_bonus
        )

        # Начисление в score НЕ делаем здесь — оно
        # происходит на экране результатов (next_round).

    # ==================================================
    # Провал раунда
    # ==================================================

    def fail_round(self):

        # Очки текущего раунда добавляем к общему счёту
        self.score += self.round_score

        self.round_score = 0

    # ==================================================
    # Начало следующего раунда
    # ==================================================

    def next_round(self):

        # Начисляем результат раунда в общий счёт
        # (здесь — на экране с результатом, по ENTER)
        self.score += self.round_total

        self.round_total = 0

        self.round_number += 1

        self.create_round()