from prompt_toolkit.layout.containers import Window

class ScrollWindow(Window):
    '''
    Hack for proper line scrolling of Window. By default, scroll is based in document lines (before wrapping),
    so very long lines become problematic. This changes the behaviour to scrolling on lines after wrapping.
    '''
    def __init__(self, content, **kwargs):
        super().__init__(content, **kwargs)
        self._pos = -1
        self._last_scroll_position = 0

    def _scroll_down(self, cli):
        if self._pos >= 0:
            self._pos += 3

    def _scroll_up(self, cli):
        if self._pos < 0:
            self._pos = self._last_scroll_position
        self._pos = max(self._pos - 3, 0)

    def _copy_body(self, cli, ui_content, new_screen, write_position, move_x,
                   width, vertical_scroll=0, horizontal_scroll=0,
                   has_focus=False, wrap_lines=False, highlight_lines=False,
                   vertical_scroll_2=0, always_hide_cursor=False):
        actual_lines = sum((ui_content.get_height_for_line(i, width) for i in range(ui_content.line_count)))
        self._last_scroll_position = actual_lines - write_position.height
        if self._pos > self._last_scroll_position:
            self._pos = -1
        position = self._last_scroll_position if self._pos < 0 else self._pos
        return super()._copy_body(cli, ui_content, new_screen, write_position, move_x,
                                  width, 0, horizontal_scroll,
                                  has_focus, wrap_lines, highlight_lines,
                                  position, always_hide_cursor)
