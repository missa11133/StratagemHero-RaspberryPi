import pygame


# ==================================================
# Свечение (bloom) вокруг текста и графики
#
# Включается/выключается флагом BLOOM_ENABLED:
#   False — текст рисуется обычным font.render, а графике
#           (стрелкам, полосам, плашкам) ореол не рисуется
#           вовсе (это же делает запуск с --no-bloom).
#
# Текст:   render_bloom() / blit_bloom()            (текст + размер)
# Графика: render_image_bloom(), render_rect_bloom(),
#          blit_bloom_image(), blit_bloom_rect(),
#          blit_bloom_bar()        (картинка или прямоугольник)
#
# Принцип у текста и графики один: силуэт элемента размывается,
# яркость нормируется к BLOOM_PEAK, а затем готовый слой
# складывается с фоном аддитивно (BLEND_RGB_ADD) — см.
# _additive_layer().
# ==================================================

BLOOM_ENABLED = True

# Шрифт, как и в остальных экранах игры
FONT_PATH = "assets/fonts/FS Sinclair Medium.otf"

# Кэш шрифтов и готовых «свечение + текст» поверхностей:
# рендерить и размывать каждый кадр не нужно.
_font_cache = {}
_surface_cache = {}

# Кэши ореолов графики (см. раздел «Свечение графики» в конце
# файла). Они отдельные: у полосы таймера записей бывает много,
# и они не должны вытеснять текстовые ореолы (и наоборот).
_image_cache = {}
_rect_cache = {}
_bar_cache = {}

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
    _image_cache.clear()
    _rect_cache.clear()
    _bar_cache.clear()


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


def _peak_brightness(surface, max_samples=4096, exclude=None):
    """Максимальная яркость поверхности по каналам.

    Точный максимум требует перебора всех пикселей (4000 и
    более вызовов get_at — это миллисекунды), поэтому яркость
    ищется по равномерной сетке. Для плавного ореола разница
    с точным максимумом незаметна, а число выборок ограничено.

    exclude — прямоугольник, который из замера выбрасывается.
    Так ореолы графики нормируются по своей самой яркой точке
    (у самого края фигуры), а не по её внутренности: у крупной
    плашки внутренность размывается почти без потерь, и без
    исключения нормировка вообще не срабатывает, оставляя
    ореол в пару единиц из 255.
    """

    width, height = surface.get_size()

    area = width * height

    step = 1

    if area > max_samples:

        step = int((area / max_samples) ** 0.5) + 1

    peak = 0

    for y in range(0, height, step):

        for x in range(0, width, step):

            if exclude is not None and exclude.collidepoint(x, y):

                continue

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


def _normalize_peak(surface, target, exclude=None):
    """Приводит максимальную яркость поверхности к target.

    Нормировка нужна, чтобы radius отвечал за ширину ореола,
    а не за его тусклость: размытие сохраняет суммарную
    «энергию», и широкий ореол иначе почти не виден (вдали от
    буквы высотой 40 px при радиусе 80 px добавка падает
    до 1..5 из 255).

    exclude — область, которая в замер яркости не входит (см.
    _peak_brightness): для графики это сама фигура, чтобы
    нормировался её ореол.
    """

    peak = _peak_brightness(surface, exclude=exclude)

    if peak <= 0:

        return

    boost = min(_MAX_BOOST, target / peak)

    if boost > 1.0:

        _boost_brightness(surface, boost)


def _additive_layer(glow, intensity, exclude=None):
    """Размытый силуэт превращает в аддитивную поверхность.

    Общий путь для текста и графики — три шага:

    1) Предумножение на альфу.

       Аддитивное смешивание учитывает только RGB источника и
       полностью игнорирует альфу. Поэтому бледный ореол,
       размытый через smoothscale, складывался бы с фоном
       своим «сырым» RGB — и вокруг элемента появлялся бы
       светлый прямоугольник.

       Альфа-блит ореола на чёрную подложку даёт
       premultiplied-цвет: rgb * a / 255. Для нулевой альфы
       это ровно чёрный, то есть добавка к фону будет строго
       нулевой.

    2) Нормировка яркости к BLOOM_PEAK.

       Размытие сохраняет суммарную «энергию», поэтому широкий
       ореол выходит бледным: например, буква высотой 40 px при
       радиусе 80 px добавляет к фону всего 5 из 255. Нормировка
       по максимальной яркости делает radius ответственным за
       ширину ореола, а яркость оставляет за intensity.

    3) Масштаб на intensity — уже предумноженного и
       нормированного цвета, поэтому яркость ореола меняется
       ровно в intensity раз.

    exclude — область, исключаемая из замера яркости при
    нормировке (у графики это сама фигура, см. _peak_brightness).
    """

    additive = pygame.Surface(
        glow.get_size()
    )

    additive.fill((0, 0, 0))

    additive.blit(glow, (0, 0))

    _normalize_peak(additive, BLOOM_PEAK, exclude)

    if 0.0 <= intensity < 1.0:

        scale = max(0, min(255, int(intensity * 255)))

        additive.fill(
            (scale, scale, scale),
            special_flags=pygame.BLEND_RGB_MULT,
        )

    return additive


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

    # Предумножение на альфу, нормировка по яркости и
    # масштаб интенсивности — общий путь с ореолами графики
    # (см. _additive_layer).
    additive = _additive_layer(glow, intensity)

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

# ==================================================
# Свечение графики (стрелки, полосы, плашки)
#
# Графика не имеет размера шрифта, поэтому радиус ореола
# либо задаётся явно, либо берётся как доля меньшей стороны
# элемента (default_shape_radius).
#
# Почему не как у текста: там радиус — это высота буквы, то
# есть «размер самой фигуры». Для картинки/прямоугольника
# роль такого размера играет меньшая сторона.
# ==================================================

# Авто-радиус для сплошных элементов — доля меньшей стороны.
#
# Тонким контурам (рамка в 2 px) авто-радиус не подходит:
# у квадрата 118 px он вышел бы ~35 px, и рамка утонула бы в
# собственном свете. Таким элементам радиус задают явно.
BLOOM_RADIUS_SHAPES = 0.3

# Предохранители кэшей графики.
#
# Ореолы графики крупнее текстовых (полоса таймера — около
# 500x50), поэтому у каждого кэша свой небольшой лимит: всплеск
# записей полосы не должен вытеснять ореолы стрелок и не должен
# раздувать память на Raspberry Pi.
_IMAGE_CACHE_LIMIT = 64
_RECT_CACHE_LIMIT = 16

# Сколько длин короткого хвоста полосы кэшировать (см.
# blit_bloom_bar): длины короче шести радиусов собираются
# отдельно и лениво. Лимит должен покрывать хвост целиком,
# иначе словарь чистится прямо в таймере — при радиусе 14
# хвост 84 px, а при шаге 2 это около 42 ступеней.
_BAR_SHORT_LIMIT = 48

# Порог, с которого ореол полосы собирается из торцов и тела
# (в радиусах ореола).
#
# Замеренное расхождение такого композита с ореолом, посчитанным
# для конкретной длины: 4 радиуса — 7 из 255, 6 — 6, 10 — 5,
# 15 — 3, 25 и больше — 2 (2 из 255 — это уже округление 8 бит).
# Порог в шесть радиусов держит расхождение в пределах 5 из 255
# (около 2% яркости размытого края — на глаз незаметно), зато
# почти всю дистанцию полоса рисуется тремя блитами. Короткий
# хвост, где ошибка была бы больше, собирается точно и лениво.
_BAR_MIN_COMPOSITE_RADII = 6

# Во сколько раз яркость композита может разойтись с ореолом,
# посчитанным для конкретной длины заливки: композит наследует
# нормировку «мастера» (полной полосы), поэтому его яркость не
# зависит от текущей длины — ореол не «дышит» при укорачивании.
_BAR_BRIGHTNESS_TOLERANCE = 25


def default_shape_radius(size, ratio=None):
    """Радиус ореола графики — доля меньшей стороны элемента.

    Например, стрелка 45x45 при BLOOM_RADIUS_SHAPES = 0.3
    получает радиус 14 px — ореол примерно в треть стрелки.
    """

    ratio = BLOOM_RADIUS_SHAPES if ratio is None else ratio

    return max(
        _MIN_RADIUS,
        min(
            _MAX_RADIUS,
            int(min(size) * ratio + 0.5),
        ),
    )


def _silhouette_layer(size, radius, draw):
    """Размытый силуэт элемента на прозрачной подложке.

    draw(layer, padding) рисует сам силуэт (картинку или
    прямоугольник) на поверхности ореола с отступом
    glow_padding(radius) со всех сторон — по этому отступу
    готовый ореол потом совмещается с элементом.
    """

    padding = glow_padding(radius)

    layer = pygame.Surface(
        (
            size[0] + padding * 2,
            size[1] + padding * 2,
        ),
        pygame.SRCALPHA,
    )

    draw(layer, padding)

    return _blur(layer, radius)


def _tinted_copy(image, color):
    """Копия картинки, окрашенная в color.

    Тот же приём, что в color_image() геймплея: умножение на
    цвет сохраняет альфу, то есть силуэт картинки.
    """

    tinted = image.copy()

    overlay = pygame.Surface(
        tinted.get_size(),
        pygame.SRCALPHA,
    )

    overlay.fill((*color, 255))

    tinted.blit(
        overlay,
        (0, 0),
        special_flags=pygame.BLEND_RGBA_MULT,
    )

    return tinted




def render_image_bloom(image, color=None, radius=None, intensity=0.7, key=None):
    """Аддитивный ореол по силуэту картинки.

    color=None — ореол цвета самой картинки (стрелка в исходном
    состоянии); для окрашенной стрелки передаётся тот же цвет,
    каким покрашена картинка, тогда ореол совпадает с ней.

    key — то, что отличает картинки друг от друга (например
    направление стрелки). По этому ключу работает кэш, поэтому
    повторные кадры ничего не считают: ореол стрелки строится
    один раз на пару «картинка + цвет».
    """

    if radius is None:

        radius = default_shape_radius(image.get_size())

    cache_key = (
        key,
        image.get_size(),
        None if color is None else tuple(color),
        radius,
        intensity,
    )

    cached = _image_cache.get(cache_key)

    if cached is not None:

        return cached

    source = (
        image
        if color is None
        else _tinted_copy(image, color)
    )

    glow = _silhouette_layer(
        source.get_size(),
        radius,
        lambda layer, padding: layer.blit(source, (padding, padding)),
    )

    additive = _additive_layer(glow, intensity)

    if len(_image_cache) >= _IMAGE_CACHE_LIMIT:

        _image_cache.clear()

    _image_cache[cache_key] = additive

    return additive


def render_rect_bloom(size, color, radius=None, intensity=0.7, width=0):
    """Аддитивный ореол прямоугольника.

    width=0 — ореол вокруг залитого прямоугольника (плашка под
    названием стратагемы). width больше нуля — ореол вокруг
    контура толщиной width: так светится рамка вокруг текущей
    стратагемы в очереди.
    """

    if radius is None:

        radius = default_shape_radius(size)

    cache_key = (
        size,
        tuple(color),
        radius,
        intensity,
        width,
    )

    cached = _rect_cache.get(cache_key)

    if cached is not None:

        return cached

    outline = pygame.Rect(0, 0, size[0], size[1])

    def draw(layer, padding):

        pygame.draw.rect(
            layer,
            (*color, 255),
            outline.move(padding, padding),
            width=width,
        )

    glow = _silhouette_layer(size, radius, draw)

    # Залитый прямоугольник исключаем из замера яркости: ореол
    # нормируется по своей самой яркой точке у края фигуры (см.
    # _peak_brightness). У контура (width больше нуля) исключать
    # нечего — внутри рамки тот же ореол, что и снаружи.
    exclude = None

    if width == 0:

        padding = glow_padding(radius)

        exclude = pygame.Rect(
            padding,
            padding,
            size[0],
            size[1],
        )

    additive = _additive_layer(glow, intensity, exclude)

    if len(_rect_cache) >= _RECT_CACHE_LIMIT:

        _rect_cache.clear()

    _rect_cache[cache_key] = additive

    return additive


def blit_additive(screen, additive, rect):
    """Аддитивный блит готового ореола по месту элемента.

    Ореол больше элемента на glow_padding(radius) с каждой
    стороны, поэтому сдвигаем его назад — так центр свечения
    совпадает с элементом.

    BLEND_RGB_ADD складывает только цвет и не трогает альфу
    цели: фон под элементом светлеет ровно на величину ореола.
    """

    padding_x = (additive.get_width() - rect.width) // 2
    padding_y = (additive.get_height() - rect.height) // 2

    screen.blit(
        additive,
        (rect.x - padding_x, rect.y - padding_y),
        special_flags=pygame.BLEND_RGB_ADD,
    )


def blit_bloom_image(
    screen,
    image,
    rect,
    color=None,
    radius=None,
    intensity=0.7,
    key=None,
):
    """Ореол под картинкой.

    Саму картинку рисует вызывающий код уже после этого вызова:
    аддитивный слой должен лежать ПОД элементом, иначе свет
    подмешается к его собственному цвету.
    """

    if not BLOOM_ENABLED or radius == 0:

        return

    blit_additive(
        screen,
        render_image_bloom(
            image,
            color,
            radius,
            intensity,
            key,
        ),
        rect,
    )


def blit_bloom_rect(
    screen,
    rect,
    color,
    radius=None,
    intensity=0.7,
    width=0,
):
    """Ореол прямоугольника (сам прямоугольник рисует вызывающий)."""

    if not BLOOM_ENABLED or radius == 0:

        return

    blit_additive(
        screen,
        render_rect_bloom(
            rect.size,
            color,
            radius,
            intensity,
            width,
        ),
        rect,
    )


def _build_bar_parts(width, height, color, radius, intensity):
    """Куски ореола полосы: мастер, торцы и столбец-тело.

    «Мастер» — ореол полосы на полную ширину. Торец — его край
    шириной glow_padding(radius) + 2*radius: в этой полосе
    укладывается весь переход от края полосы к «плато» (у _blur
    плато начинается ровно в два радиуса внутрь), поэтому такой
    кусок можно перенести на любой край заливки.

    Тело — столбец шириной 1 px из середины мастера. В этой зоне
    ореол однороден по горизонтали (все колонки совпадают
    пиксель-в-пиксель), поэтому растяжение столбца картинку не
    искажает — именно это и позволяет обойтись без размытия
    на кадре.
    """

    master = render_rect_bloom(
        (width, height),
        color,
        radius,
        intensity,
    )

    master_width, master_height = master.get_size()

    padding = glow_padding(radius)

    # Половина ширины мастера — предохранитель на случай очень
    # короткой полосы в разметке: торцы не должны наложиться
    # друг на друга и не должны выйти за пределы мастера.
    cap_width = min(
        padding + 2 * radius,
        master_width // 2,
    )

    return {
        "height": master_height,
        "left": master.subsurface(
            (0, 0, cap_width, master_height)
        ).copy(),
        "right": master.subsurface(
            (master_width - cap_width, 0, cap_width, master_height)
        ).copy(),
        "body": master.subsurface(
            (cap_width, 0, 1, master_height)
        ).copy(),
        "short": {},
    }


def blit_bloom_bar(
    screen,
    rect,
    fill_width,
    color,
    radius=None,
    intensity=0.7,
    width_step=2,
):
    """Ореол полосы, следящий за длиной заливки.

    Полоса таймера меняет длину каждый кадр, а сборка ореола с
    нуля стоит около миллисекунды (на Raspberry Pi — заметно
    больше), поэтому размывать полосу на кадре нельзя.

    Вместо этого один раз считается «мастер» (см.
    _build_bar_parts), а на кадре он собирается из трёх кусков:

        [левый торец][тело: растянутый столбец][правый торец]

    Куски берутся из мастера встык, поэтому аддитивные блиты не
    накладываются друг на друга, и результат повторяет ореол
    заливки: расхождение с эталоном не больше 2 из 255 на
    длинных полосах и до 5 из 255 на средних (см. константу
    _BAR_MIN_COMPOSITE_RADII). Цена кадра — три блита и одно
    растяжение столбца.

    Яркость ореола наследуется от мастера (нормировка считается
    по полной полосе), поэтому при укорачивании заливки ореол не
    «дышит»: у собранного ореола и у ореола, посчитанного для
    конкретной длины, расхождение около 10% (не больше 25 из
    255) — на мягком свечении это незаметно.

    Совсем короткий хвост таймера (короче шести радиусов) так
    собрать нельзя: профиль ореола там ещё не «плато», а торцы
    начали бы накладываться и дали бы двойную яркость. Для
    такого хвоста ореол считается точно и лениво кэшируется по
    длине с шагом width_step: таких сборок за раунд десятки, и
    они крошечные (полоса длиной в десятки px).
    """

    if not BLOOM_ENABLED or radius == 0 or fill_width <= 0:

        return

    if radius is None:

        radius = default_shape_radius(rect.size)

    cache_key = (
        rect.width,
        rect.height,
        tuple(color),
        radius,
        intensity,
    )

    parts = _bar_cache.get(cache_key)

    if parts is None:

        if len(_bar_cache) >= _RECT_CACHE_LIMIT:

            _bar_cache.clear()

        parts = _build_bar_parts(
            rect.width,
            rect.height,
            color,
            radius,
            intensity,
        )

        _bar_cache[cache_key] = parts

    padding = glow_padding(radius)
    depth = 2 * radius

    # ----------------------------------------------
    # Длинная заливка: торец + тело + торец
    # ----------------------------------------------

    if fill_width > _BAR_MIN_COMPOSITE_RADII * radius:

        screen.blit(
            parts["left"],
            (rect.x - padding, rect.y - padding),
            special_flags=pygame.BLEND_RGB_ADD,
        )

        screen.blit(
            pygame.transform.scale(
                parts["body"],
                (
                    fill_width - 2 * depth,
                    parts["height"],
                ),
            ),
            (rect.x + depth, rect.y - padding),
            special_flags=pygame.BLEND_RGB_ADD,
        )

        screen.blit(
            parts["right"],
            (rect.x + fill_width - depth, rect.y - padding),
            special_flags=pygame.BLEND_RGB_ADD,
        )

        return

    # ----------------------------------------------
    # Короткий хвост таймера: точный ореол по ступеням длины
    # ----------------------------------------------

    step = max(1, width_step)

    bucketed = int((fill_width + step - 1) // step * step)

    buckets = parts["short"]

    additive = buckets.get(bucketed)

    if additive is None:

        additive = render_rect_bloom(
            (bucketed, rect.height),
            color,
            radius,
            intensity,
        )

        if len(buckets) >= _BAR_SHORT_LIMIT:

            buckets.clear()

        buckets[bucketed] = additive

    blit_additive(
        screen,
        additive,
        pygame.Rect(rect.x, rect.y, bucketed, rect.height),
    )
