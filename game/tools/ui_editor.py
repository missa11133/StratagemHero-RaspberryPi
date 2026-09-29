import pygame

from game.systems.layout import ANCHORS


class UIEditor:

    # ==================================================
    # Overlay
    # ==================================================

    HANDLE_SIZE = 8
    SELECT_RADIUS = 15
    RESIZE_RADIUS = 12

    NEUTRAL_COLOR = (80, 200, 255)
    SELECTED_COLOR = (255, 230, 0)
    RESIZE_COLOR = (255, 90, 90)
    HUD_BG = (18, 18, 28)
    HUD_TEXT = (240, 240, 240)

    # Preview box for elements that have no stored size
    PREVIEW_SIZE = (100, 28)

    # Base font size used when editing an element that
    # has no stored font size yet
    FONT_DEFAULT_SIZE = 24

    # ==================================================

    def __init__(self, game):

        self.game = game

        self.screens = [
            game.start_screen,
            game.get_ready_screen,
            game.game_over_screen,
            game.round_score_screen,
            game.gameplay_screen,
        ]

        self.screen_names = [
            "start",
            "get_ready",
            "game_over",
            "round_score",
            "gameplay",
        ]

        self.screen_index = 0
        self.selected_id = None
        self.dragging = False
        self.resizing = False

        self.message = ""
        self.message_timer = 0

        self.font = pygame.font.Font(
            "assets/fonts/FS Sinclair Medium.otf",
            18
        )

        # Start editing on the START screen
        self.game.current_screen = self.screens[
            self.screen_index
        ]

    # ==================================================
    # Helpers
    # ==================================================

    @property
    def current_layout(self):

        return self.screens[
            self.screen_index
        ].layout

    def switch_screen(self, step):

        self.screen_index = (
            self.screen_index + step
        ) % len(self.screens)

        self.selected_id = None
        self.dragging = False
        self.resizing = False

        # Switch screen directly: no music or resets
        self.game.current_screen = self.screens[
            self.screen_index
        ]

    def pick_element(self, pos):

        best_id = None
        best_distance = self.SELECT_RADIUS

        for element_id, item in self.current_layout.items.items():

            distance = (
                (item.x - pos[0]) ** 2
                + (item.y - pos[1]) ** 2
            ) ** 0.5

            if distance <= best_distance:

                best_distance = distance
                best_id = element_id

        return best_id

    # ==================================================
    # Event handling
    # ==================================================

    def handle_events(self, events):

        for event in events:

            if event.type == pygame.KEYDOWN:

                self._handle_key(event)

            elif event.type == pygame.MOUSEBUTTONDOWN:

                if event.button == 1:

                    self._mouse_down(event.pos)

            elif event.type == pygame.MOUSEBUTTONUP:

                if event.button == 1:

                    self.dragging = False
                    self.resizing = False

            elif event.type == pygame.MOUSEMOTION:

                self._mouse_motion(event.rel, event.pos)

    def _mouse_down(self, pos):

        layout = self.current_layout

        # A click on the resize handle starts resizing
        if self.selected_id is not None:

            hx, hy = self._resize_handle_pos(
                layout,
                self.selected_id
            )

            dx = hx - pos[0]
            dy = hy - pos[1]

            if (dx * dx + dy * dy) <= (
                self.RESIZE_RADIUS * self.RESIZE_RADIUS
            ):

                self.resizing = True
                return

        self.selected_id = self.pick_element(pos)

        if self.selected_id is not None:

            self.dragging = True

    def _mouse_motion(self, rel, pos):

        layout = self.current_layout

        if self.selected_id is None:

            return

        if self.resizing:

            self._apply_corner_size(
                layout,
                self.selected_id,
                pos
            )

        elif self.dragging:

            x, y = layout.pos(self.selected_id)

            layout.set_pos(
                self.selected_id,
                x + rel[0],
                y + rel[1]
            )

    def _apply_corner_size(self, layout, element_id, pos):

        x, y = layout.pos(element_id)

        width, height = self._size_from_corner(
            layout.anchor(element_id),
            x,
            y,
            pos[0],
            pos[1]
        )

        layout.set_size(element_id, (width, height))

    def _size_from_corner(self, anchor, x, y, corner_x, corner_y):

        # Bottom-right corner of the element relative to its
        # fixed anchor point depends on the anchor:
        #   edge flat  -> corner x = x + w   or  x - w
        #   edge center -> corner x = x + w / 2
        #   fixed edge -> corner x = x
        if anchor in ("topleft", "bottomleft", "midleft"):

            width = corner_x - x

        elif anchor in ("topright", "bottomright", "midright"):

            width = x - corner_x

        else:
            width = 2 * (corner_x - x)

        if anchor in ("topleft", "topright", "midtop"):

            height = corner_y - y

        elif anchor in ("bottomleft", "bottomright", "midbottom"):

            height = y - corner_y

        else:
            height = 2 * (corner_y - y)

        return max(1, int(round(width))), max(1, int(round(height)))

    def _element_rect(self, layout, element_id):

        # Screen rect of an element. Follows the same anchor
        # logic as LayoutRegistry.rect() but never raises for
        # a missing size (a preview size is used instead).
        x, y = layout.pos(element_id)

        size = layout.size(element_id)

        if size is None:

            size = self.PREVIEW_SIZE

        rect = pygame.Rect(0, 0, size[0], size[1])

        setattr(
            rect,
            layout.anchor(element_id),
            (x, y)
        )

        return rect

    def _resize_handle_pos(self, layout, element_id):

        rect = self._element_rect(layout, element_id)

        return (rect.right, rect.bottom)

    def _resize_by(self, layout, dw, dh):

        if layout.size(self.selected_id) is None:

            layout.set_size(
                self.selected_id,
                self.PREVIEW_SIZE
            )

        width, height = layout.size(self.selected_id)

        layout.set_size(
            self.selected_id,
            (
                max(1, width + dw),
                max(1, height + dh)
            )
        )

    def _change_font_size(self, layout, delta):

        if self.selected_id is None:

            return

        current = layout.font_size(self.selected_id)

        if current is None:

            current = self.FONT_DEFAULT_SIZE

        layout.set_font_size(
            self.selected_id,
            max(1, current + delta)
        )

    def _handle_key(self, event):

        control = bool(event.mod & pygame.KMOD_CTRL)

        layout = self.current_layout

        # ----------------------------------------------
        # Screen navigation
        # ----------------------------------------------

        if event.key == pygame.K_TAB:

            step = -1 if (event.mod & pygame.KMOD_SHIFT) else 1

            self.switch_screen(step)

            return

        # ----------------------------------------------
        # Exit the editor
        # ----------------------------------------------

        if event.key == pygame.K_ESCAPE:

            self.game.editor_mode = False

            self.game.change_screen(
                self.game.start_screen
            )

            return

        # ----------------------------------------------
        # Save layout (Ctrl+S)
        # ----------------------------------------------

        if event.key == pygame.K_s and control:

            layout.save()

            self.message = (
                f"Saved: {layout.path}"
            )
            self.message_timer = 120

            return

        # ----------------------------------------------
        # Cycle anchor of selected element (key A)
        # ----------------------------------------------

        if event.key == pygame.K_a:

            if self.selected_id is not None:

                current = layout.anchor(
                    self.selected_id
                )

                index = ANCHORS.index(current)

                new_anchor = ANCHORS[
                    (index + 1) % len(ANCHORS)
                ]

                layout.set_anchor(
                    self.selected_id,
                    new_anchor
                )

                self.message = f"Anchor: {new_anchor}"
                self.message_timer = 120

            return

        # ----------------------------------------------
        # Resize selected element (Ctrl+arrows)
        # ----------------------------------------------

        if self.selected_id is not None and control:

            step = 10 if (event.mod & pygame.KMOD_SHIFT) else 1

            dw = 0
            dh = 0

            if event.key == pygame.K_LEFT:
                dw = -step
            elif event.key == pygame.K_RIGHT:
                dw = step
            elif event.key == pygame.K_UP:
                dh = -step
            elif event.key == pygame.K_DOWN:
                dh = step

            if dw or dh:

                self._resize_by(layout, dw, dh)

            return

        # ----------------------------------------------
        # Clear stored size (key R, back to auto size)
        # ----------------------------------------------

        if event.key == pygame.K_r and self.selected_id is not None:

            layout.set_size(self.selected_id, None)

            self.message = f"Size cleared (auto): {self.selected_id}"
            self.message_timer = 120

            return

        # ----------------------------------------------
        # Font size of selected element ([ and ] keys)
        # ----------------------------------------------

        if (
            event.key == pygame.K_LEFTBRACKET
            or event.key == pygame.K_RIGHTBRACKET
        ):

            if self.selected_id is not None:

                step = 10 if (event.mod & pygame.KMOD_SHIFT) else 1
                delta = (
                    step
                    if event.key == pygame.K_RIGHTBRACKET
                    else -step
                )

                self._change_font_size(layout, delta)

            return

        # ----------------------------------------------
        # Precise nudge of selected element with arrows
        # ----------------------------------------------

        if self.selected_id is not None:

            step = 10 if (event.mod & pygame.KMOD_SHIFT) else 1

            dx = 0
            dy = 0

            if event.key == pygame.K_LEFT:
                dx = -step
            elif event.key == pygame.K_RIGHT:
                dx = step
            elif event.key == pygame.K_UP:
                dy = -step
            elif event.key == pygame.K_DOWN:
                dy = step

            if dx or dy:

                x, y = layout.pos(
                    self.selected_id
                )

                layout.set_pos(
                    self.selected_id,
                    x + dx,
                    y + dy
                )

    # ==================================================
    # Update (message counter)
    # ==================================================

    def update(self):

        if self.message_timer > 0:

            self.message_timer -= 1

    # ==================================================
    # Draw overlay on top of the screen
    # ==================================================

    def draw_overlay(self, screen):

        layout = self.current_layout

        # ----------------------------------------------
        # Element markers
        # ----------------------------------------------

        for element_id in layout.items:

            selected = (element_id == self.selected_id)

            color = (
                self.SELECTED_COLOR
                if selected
                else self.NEUTRAL_COLOR
            )

            self._draw_marker(
                screen,
                layout,
                element_id,
                layout.pos(element_id),
                color,
                selected
            )

        # ----------------------------------------------
        # HUD panel
        # ----------------------------------------------

        self._draw_hud(
            screen,
            layout
        )

        # ----------------------------------------------
        # Toast message (saved, etc.)
        # ----------------------------------------------

        if self.message_timer > 0:

            text_surface = self.font.render(
                self.message,
                True,
                (120, 255, 120)
            )

            screen.blit(
                text_surface,
                (
                    self.game.screen.get_width()
                    // 2
                    - text_surface.get_width() // 2,
                    60
                )
            )

    def _draw_dashed_rect(self, screen, color, rect):

        dash = 6
        gap = 4

        for edge_y in (rect.top, rect.bottom):

            edge_x = rect.left

            while edge_x < rect.right:

                end = min(edge_x + dash, rect.right)

                pygame.draw.line(
                    screen,
                    color,
                    (edge_x, edge_y),
                    (end, edge_y),
                    1
                )

                edge_x += dash + gap

        for edge_x in (rect.left, rect.right):

            edge_y = rect.top

            while edge_y < rect.bottom:

                end = min(edge_y + dash, rect.bottom)

                pygame.draw.line(
                    screen,
                    color,
                    (edge_x, edge_y),
                    (edge_x, end),
                    1
                )

                edge_y += dash + gap

    def _draw_resize_handle(self, screen, pos):

        x, y = pos

        size = self.HANDLE_SIZE + 4

        handle_rect = pygame.Rect(
            x - size // 2,
            y - size // 2,
            size,
            size
        )

        pygame.draw.rect(
            screen,
            self.RESIZE_COLOR,
            handle_rect,
            border_radius=2
        )

        pygame.draw.rect(
            screen,
            (10, 10, 10),
            handle_rect,
            width=1,
            border_radius=2
        )

    def _draw_marker(
        self,
        screen,
        layout,
        element_id,
        pos,
        color,
        selected
    ):

        x, y = pos

        # Selection box and resize handle for the selected element
        if selected:

            rect = self._element_rect(
                layout,
                element_id
            )

            if layout.size(element_id) is None:

                self._draw_dashed_rect(
                    screen,
                    self.NEUTRAL_COLOR,
                    rect
                )

            else:

                pygame.draw.rect(
                    screen,
                    self.SELECTED_COLOR,
                    rect,
                    width=1
                )

            self._draw_resize_handle(
                screen,
                (rect.right, rect.bottom)
            )

        cross = 14 + (8 if selected else 0)

        # Crosshair
        pygame.draw.line(
            screen,
            color,
            (x - cross, y),
            (x + cross, y),
            1
        )

        pygame.draw.line(
            screen,
            color,
            (x, y - cross),
            (x, y + cross),
            1
        )

        # Handle square
        half = self.HANDLE_SIZE // 2

        handle_rect = pygame.Rect(
            x - half,
            y - half,
            self.HANDLE_SIZE,
            self.HANDLE_SIZE
        )

        pygame.draw.rect(
            screen,
            color,
            handle_rect,
            border_radius=2
        )

        pygame.draw.rect(
            screen,
            (10, 10, 10),
            handle_rect,
            width=1,
            border_radius=2
        )

        # Label of selected element
        if selected:

            label = self.font.render(
                element_id,
                True,
                color
            )

            screen.blit(
                label,
                (x + 14, y + 14)
            )

    def _draw_hud(self, screen, layout):

        lines = [
            "=== UI EDITOR ===",
            f"SCREEN: {self.screen_names[self.screen_index]}",
        ]

        if self.selected_id is not None:

            x, y = layout.pos(self.selected_id)

            lines.append(
                f"ELEMENT: {self.selected_id}   "
                f"ANCHOR: {layout.anchor(self.selected_id)}"
            )

            lines.append(
                f"X: {x}   Y: {y}"
            )

            size = layout.size(self.selected_id)

            if size is None:

                lines.append("SIZE: auto (drag red corner to set it)")

            else:

                lines.append(f"SIZE: {size[0]} x {size[1]}")

            font_size = layout.font_size(self.selected_id)

            if font_size is None:

                lines.append("FONT: auto ([ / ] to set it)")

            else:

                lines.append(f"FONT: {font_size}")

        lines.append("TAB: next screen | Shift+TAB: previous")
        lines.append("LMB: select/move | red corner: resize")
        lines.append("Arrows: move | Ctrl+Arrows: resize (Shift: x10)")
        lines.append("[ / ]: font size (Shift: x10) | R: clear size")
        lines.append("A: anchor | Ctrl+S: save | ESC: exit")

        panel_height = len(lines) * 22 + 24

        panel = pygame.Surface(
            (620, panel_height)
        )

        panel.fill(self.HUD_BG)
        panel.set_alpha(200)

        margin = 16
        panel_y = screen.get_height() - panel_height - margin

        screen.blit(panel, (margin, panel_y))

        for index, line in enumerate(lines):

            text_surface = self.font.render(
                line,
                True,
                self.HUD_TEXT
            )

            screen.blit(
                text_surface,
                (margin + 16, panel_y + 12 + index * 22)
            )