import json
import os

import pygame


# Все возможные якоря выравнивания из pygame.Rect
ANCHORS = [
    "center",
    "midleft",
    "midright",
    "midtop",
    "midbottom",
    "topleft",
    "topright",
    "bottomleft",
    "bottomright",
]


class LayoutItem:

    def __init__(
        self,
        element_id,
        anchor,
        x,
        y,
        size=None,
        font_size=None,
    ):

        self.id = element_id
        self.anchor = anchor
        self.x = x
        self.y = y
        self.size = size
        self.font_size = font_size

    @classmethod
    def from_dict(cls, element_id, data):

        x, y = data.get("pos", [0, 0])

        size = data.get("size")

        if size is not None:

            size = (size[0], size[1])

        return cls(
            element_id,
            data.get("anchor", "center"),
            x,
            y,
            size,
            data.get("font_size")
        )

    def to_dict(self):

        data = {
            "anchor": self.anchor,
            "pos": [self.x, self.y],
        }

        if self.size is not None:

            data["size"] = list(self.size)

        if self.font_size is not None:

            data["font_size"] = self.font_size

        return data


class LayoutRegistry:

    # Папка с JSON-файлами разметки
    LAYOUT_DIR = os.path.join(
        "game",
        "data",
        "layouts"
    )

    def __init__(self, screen_name, defaults=None, default_metrics=None):

        self.screen_name = screen_name

        self.items = {}
        self.metrics = {}

        self.load(
            defaults or {},
            default_metrics or {}
        )

    # ==================================================
    # Путь к JSON-файлу разметки
    # ==================================================

    @property
    def path(self):

        return os.path.join(
            self.LAYOUT_DIR,
            f"{self.screen_name}.json"
        )

    # ==================================================
    # Загрузка: дефолты из кода + переопределения из JSON
    # ==================================================

    def load(self, defaults, default_metrics):

        for element_id, data in defaults.items():

            self.items[element_id] = LayoutItem.from_dict(
                element_id,
                data
            )

        self.metrics = dict(default_metrics)

        if not os.path.exists(self.path):

            return

        try:

            with open(self.path, "r", encoding="utf-8") as file:

                content = json.load(file)

        except (OSError, ValueError):

            # Битый файл — работаем на дефолтах из кода
            return

        for element_id, data in content.get("elements", {}).items():

            self.items[element_id] = LayoutItem.from_dict(
                element_id,
                data
            )

        for metric_name, value in content.get("metrics", {}).items():

            self.metrics[metric_name] = value

    # ==================================================
    # Сохранение в JSON
    # ==================================================

    def save(self):

        os.makedirs(self.LAYOUT_DIR, exist_ok=True)

        content = {
            "screen": self.screen_name,
            "elements": {
                element_id: item.to_dict()
                for element_id, item in self.items.items()
            },
            "metrics": self.metrics,
        }

        with open(self.path, "w", encoding="utf-8") as file:

            json.dump(
                content,
                file,
                ensure_ascii=False,
                indent=2
            )

    # ==================================================
    # Чтение/запись элементов
    # ==================================================

    def pos(self, element_id):

        item = self.items[element_id]

        return (item.x, item.y)

    def anchor(self, element_id):

        return self.items[element_id].anchor

    def set_pos(self, element_id, x, y):

        item = self.items[element_id]

        item.x = x
        item.y = y

    def set_anchor(self, element_id, anchor):

        self.items[element_id].anchor = anchor

    def size(self, element_id):

        return self.items[element_id].size

    def set_size(self, element_id, size):

        self.items[element_id].size = size

    def font_size(self, element_id):

        return self.items[element_id].font_size

    def set_font_size(self, element_id, font_size):

        self.items[element_id].font_size = font_size

    # ==================================================
    # Построение прямоугольника по якорю и позиции
    # ==================================================

    def rect(self, element_id, width=None, height=None):

        item = self.items[element_id]

        if item.size is not None:

            width, height = item.size

        if width is None or height is None:

            raise ValueError(
                f"Элементу '{element_id}' не задан размер"
            )

        rect = pygame.Rect(
            0,
            0,
            width,
            height
        )

        setattr(
            rect,
            item.anchor,
            (item.x, item.y)
        )

        return rect

    # ==================================================
    # Метрики (числовые параметры: отступы, шаги и т.п.)
    # ==================================================

    def metric(self, name):

        return self.metrics[name]