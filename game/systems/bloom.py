import pygame


# ==================================================
# Свечение (bloom) вокруг текста
#
# Включается/выключается флагом BLOOM_ENABLED:
#   False — весь текст рисуется обычным font.render,
#           без свечения (это же делает запуск с --no-bloom).
# ==================================================

BLOOM_ENABLED = True

# Шрифт, как и в остальных экранах игры
FONT_PATH = "assets/fonts/FS Sinclair Medium.otf"

# Кэш шрифтов и готовых «свечение + текст» поверхностей:
# рендерить и размывать каждый кадр не нужно.
_font_cache = {}
_surface_cache = {}

# Кэш высоты прописной буквы по размеру шрифта
_letter_height_cache = {}

# Предохранитель кэша поверхностей: за долгую игровую сессию
# текст меняется (счёт и т.п.), старые записи выбрасываем.
_CACHE_LIMIT = 128


def get_font(size):
    """Шрифт игры нужного размера (кэшируется)."""
    if size not in _font_cache:
        _font_cache[size] = pygame.font.Font(FONT_PATH, size)
    return _font_cache[size]


def clear_cache():
    """Полный сброс кэшей шрифтов и поверхностей."""
    _font_cache.clear()
    _surface_cache.clear()
    _letter_height_cache.clear()


# Радиус ореола задаётся в высотах прописной буквы
# (то есть «в размерах самой буквы»):
#
#   0.5 — плотное свечение, ореол уже самой буквы;
#   1.0 — ореол примерно в две буквы по диаметру (текущая
#         настройка): светится на высоту буквы в каждую сторону;
#   2.0 — очень широкий ореол, но он выходит бледнее, а после
#         усиления в нормировке появляются кольца (у размытого
#         ореола в 8 битах всего десяток градаций яркости).
BLOOM_RADIUS_LETTERS = 1.0

# Минимальный радиус, чтобы свечение было заметно на мелком тексте
_MIN_RADIUS = 4

# Предохранитель: на очень больших шрифтах поверхность ореола
# растёт как (radius * 2)^2, поэтому радиус ограничиваем.
_MAX_RADIUS = 160

# Яркость, к которой нормируется ореол (0..255).
#
# Величина в intensity — это уже доля от нормированного ореола.
#
# Зачем нормировка: гауссово размытие сохраняет суммарную
# «энергию» картинки, поэтому с ростом радиуса ореол становится
# шире, но при этом БЛЕДНЕЕ (буква при радиусе в две её высоты
# светит вдали от себя всего на 5 из 255 — то есть не видна).
# Нормировка по максимуму делает radius ответственным только за
# ширину ореола, а яркость отдаёт intensity.
BLOOM_PEAK = 96

# Ограничение усиления при нормировке.
#
# Сильное усиление бледного градиента видно как концентрические
# полосы: размытый ореол в 8 битах содержит всего десяток
# градаций, и при усилении в 30 раз шаг между ними доходит до
# 32 из 255. При усилении до 8 полосы не заметны, поэтому
# очень широкие ореолы выходят мягче и бледнее узких — как в
# настоящем bloom.
_MAX_BOOST = 8.0


def letter_height(size):
    """Высота прописной буквы («H») для шрифта данного размера.

    font.get_height() и font.size() возвращают высоту строки
    вместе с выносными элементами (для размера 64 это 80 px при
    реальной высоте буквы 40 px), поэтому высоту буквы берём из
    границ отрисованного глифа. Результат кэшируется.
    """

    height = _letter_height_cache.get(size)

    if height is None:

        glyph = get_font(size).render(
            "H",
            True,
            (255, 255, 255),
        )

        height = max(1, glyph.get_bounding_rect().height)

        _letter_height_cache[size] = height

    return height


def default_radius(size):
    """Радиус ореола (если он не задан явно) — в высотах буквы."""

    return max(
        _MIN_RADIUS,
        min(
            _MAX_RADIUS,
            int(letter_height(size) * BLOOM_RADIUS_LETTERS + 0.5),
        ),
    )


def glow_padding(radius):
    """Отступ ореола вокруг текста (с каждой стороны).

    Он чуть больше радиуса: гауссов «хвост» обрывается не ровно
    на радиусе, и при отступе, равном радиусу, по краям
    поверхности оставалась бы слабая прямоугольная кайма
    (2..3 из 255).

    Поверхность ореола из render_bloom() больше текста именно
    на этот отступ — по нему же ореол совмещается с текстом
    при отрисовке.
    """

    if radius <= 0:

        return 0

    return radius + max(2, radius // 4)


def _blur_downscale(radius):
    """Во сколько раз уменьшать картинку перед размытием.

    Гауссово размытие линейно по радиусу, а время его работы —
    по площади картинки. Ореол — картинка очень низкочастотная,
    поэтому её можно размывать на уменьшенной копии: результат
    неотличим, а считается в разы быстрее.

    Мелкие радиусы уменьшать нельзя — кернел станет меньше
    пикселя и ореол превратится в масштабированный блоб.
    """

    if radius >= 16:
        return 4

    if radius >= 6:
        return 2

    return 1


def _blur(surface, radius):
    """Мягкое размытие ореола на ширину radius (в пикселях).

    Основной путь — настоящее гауссово размытие
    (pygame.transform.gaussian_blur из pygame-ce): его результат
    линейно зависит от радиуса, поэтому ореол можно сделать
    сколь угодно широким.

    Раньше здесь были проходы smoothscale «вниз-вверх»: такой
    кернел слишком «жёсткий», и при больших радиусах буквы
    сливались в сплошную светлую полосу.
    """

    radius = max(1, int(radius))

    width, height = surface.get_size()

    factor = _blur_downscale(radius)

    if factor > 1:

        surface = pygame.transform.smoothscale(
            surface,
            (
                max(1, width // factor),
                max(1, height // factor),
            ),
        )

    gaussian_blur = getattr(
        pygame.transform,
        "gaussian_blur",
        None,
    )

    if gaussian_blur is not None:

        surface = gaussian_blur(
            surface,
            max(1, radius // factor),
        )

    else:

        # Резервный путь для pygame без gaussian_blur:
        # несколько проходов smoothscale подряд.
        for _ in range(3):

            small = pygame.transform.smoothscale(
                surface,
                (
                    max(1, surface.get_width() // 4),
                    max(1, surface.get_height() // 4),
                ),
            )

            surface = pygame.transform.smoothscale(
                small,
                (width, height),
            )

    if factor > 1:

        surface = pygame.transform.smoothscale(
            surface,
            (width, height),
        )

    return surface


def _peak_brightness(surface, max_samples=4096):
    """Максимальная яркость поверхности по каналам.

    Точный максимум требует перебора всех пикселей (4000 и
    более вызовов get_at — это миллисекунды), поэтому яркость
    ищется по равномерной сетке. Для плавного ореола разница
    с точным максимумом незаметна, а число выборок ограничено.
    """

    width, height = surface.get_size()

    area = width * height

    step = 1

    if area > max_samples:

        step = int((area / max_samples) ** 0.5) + 1

    peak = 0

    for y in range(0, height, step):

        for x in range(0, width, step):

            pixel = surface.get_at((x, y))

            value = pixel[0]

            if pixel[1] > value:
                value = pixel[1]

            if pixel[2] > value:
                value = pixel[2]

            if value > peak:
                peak = value

    return peak


def _boost_brightness(surface, boost):
    """Умножает яркость поверхности на boost (boost >= 1).

    Умножение в pygame умеет только уменьшать яркость
    (BLEND_RGB_MULT), поэтому усиление делаем сложением
    поверхности самой с собой: v + v = 2v — это быстрая
    C-операция, а насыщение на 255 для ореола не страшно.
    Последним шагом «лишний» множитель снимаем затемнением.
    """

    factor = 1.0

    while factor < boost:

        factor *= 2.0

        surface.blit(
            surface,
            (0, 0),
            special_flags=pygame.BLEND_RGB_ADD,
        )

    scale = max(0, min(255, int(boost / factor * 255 + 0.5)))

    if scale < 255:

        surface.fill(
            (scale, scale, scale),
            special_flags=pygame.BLEND_RGB_MULT,
        )


def _normalize_peak(surface, target):
    """Приводит максимальную яркость поверхности к target.

    Нормировка нужна, чтобы radius отвечал за ширину ореола,
    а не за его тусклость: размытие сохраняет суммарную
    «энергию», и широкий ореол иначе почти не виден (вдали от
    буквы высотой 40 px при радиусе 80 px добавка падает
    до 1..5 из 255).
    """

    peak = _peak_brightness(surface)

    if peak <= 0:

        return

    boost = min(_MAX_BOOST, target / peak)

    if boost > 1.0:

        _boost_brightness(surface, boost)


def render_bloom(text, size, color, glow_color=None, radius=None, intensity=0.7):
    """Сборка пары поверхностей: свечение + чёткий текст.

    Возвращает (additive, text_surface):

    additive — непрозрачная поверхность, уже предумноженная на
    альфу и готовая к блиту с BLEND_RGB_ADD. Она больше текста на
    glow_padding(radius) с каждой стороны, и текст лежит в её
    центре (по этому отступу свечение совмещается с текстом);
    text_surface — обычный font.render с чётким текстом.

    radius — ширина ореола, а его яркость задаёт intensity:
    перед отдачей ореол нормируется по максимальной яркости к
    BLOOM_PEAK (см. комментарии к константам).

    Результат кэшируется по всем параметрам — повторные кадры
    просто достают готовые поверхности из кэша.
    """
    color = tuple(color)
    glow_color = (
        color
        if glow_color is None
        else tuple(glow_color)
    )
    radius = (
        default_radius(size)
        if radius is None
        else radius
    )

    key = (text, size, color, glow_color, radius, intensity)

    cached = _surface_cache.get(key)

    if cached is not None:
        return cached

    font = get_font(size)

    text_surface = font.render(
        text,
        True,
        color,
    )

    # Слой свечения: текст цвета ореола на прозрачной подложке
    # с отступом glow_padding() со всех сторон.
    padding = glow_padding(radius)

    glow = pygame.Surface(
        (
            text_surface.get_width() + padding * 2,
            text_surface.get_height() + padding * 2,
        ),
        pygame.SRCALPHA,
    )

    glow.blit(
        font.render(
            text,
            True,
            glow_color,
        ),
        (padding, padding),
    )

    glow = _blur(glow, radius)

    # ----------------------------------------------
    # Предумножение на альфу.
    #
    # Аддитивное смешивание учитывает только RGB
    # источника и полностью игнорирует альфу. Поэтому
    # бледный ореол, размытый через smoothscale,
    # складывался бы с фоном своим «сырым» RGB — и
    # вокруг текста появлялся бы светлый прямоугольник.
    #
    # Альфа-блит ореола на чёрную подложку даёт
    # premultiplied-цвет: rgb * a / 255. Для нулевой
    # альфы это ровно чёрный, то есть добавка к фону
    # будет строго нулевой.
    # ----------------------------------------------

    additive = pygame.Surface(
        glow.get_size()
    )

    additive.fill((0, 0, 0))

    additive.blit(glow, (0, 0))

    # ----------------------------------------------
    # Нормировка яркости ореола.
    #
    # Размытие сохраняет суммарную «энергию», поэтому
    # широкий ореол выходит бледным: например, буква
    # высотой 40 px при радиусе 80 px добавляет к фону
    # всего 5 из 255. Нормировка по максимальной яркости
    # делает radius ответственным за ширину ореола, а
    # яркость оставляет за intensity.
    # ----------------------------------------------

    _normalize_peak(additive, BLOOM_PEAK)

    # Интенсивность: масштабируем уже предумноженный
    # и нормированный цвет, поэтому яркость ореола
    # меняется ровно в intensity раз.
    if 0.0 <= intensity < 1.0:

        scale = max(0, min(255, int(intensity * 255)))

        additive.fill(
            (scale, scale, scale),
            special_flags=pygame.BLEND_RGB_MULT,
        )

    if len(_surface_cache) >= _CACHE_LIMIT:
        _surface_cache.clear()

    _surface_cache[key] = (additive, text_surface)

    return additive, text_surface


def blit_bloom(
    screen,
    text,
    size,
    position,
    color,
    glow_color=None,
    radius=None,
    intensity=0.7,
    anchor="center",
):
    """Отрисовка текста со свечением.

    Если BLOOM_ENABLED выключен или radius == 0 — это обычный
    font.render + blit, картинка не меняется.
    """
    radius = (
        default_radius(size)
        if radius is None
        else radius
    )

    if not BLOOM_ENABLED or radius <= 0:

        surface = get_font(size).render(
            text,
            True,
            tuple(color),
        )

        rect = surface.get_rect()
        setattr(rect, anchor, position)

        screen.blit(surface, rect)
        return

    additive, text_surface = render_bloom(
        text,
        size,
        color,
        glow_color,
        radius,
        intensity,
    )

    text_rect = text_surface.get_rect()
    setattr(text_rect, anchor, position)

    padding = glow_padding(radius)

    # Ореол подсвечивает фон аддитивно (пересвет, как в HDR).
    #
    # BLEND_RGB_ADD складывает только цвет и не трогает
    # альфу цели. У поверхности ореола уже есть отступ
    # glow_padding() со всех сторон — поэтому сдвигаем её
    # назад, чтобы центр свечения совпал с текстом.
    screen.blit(
        additive,
        text_rect.move(-padding, -padding),
        special_flags=pygame.BLEND_RGB_ADD,
    )
    screen.blit(
        text_surface,
        text_rect,
    )
