import asyncio
import functools

from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.layout.containers import Container
from prompt_toolkit.layout.screen import Point
from prompt_toolkit.layout.dimension import LayoutDimension
from pymux.screen import BetterScreen
from pymux.stream import BetterStream

from ..lib.ssh import _SSHInteractiveHandler
from .tab import Tab


def create_interactive_tab(tosh, session):
    tab = Vt100Tab(tosh, session)
    session.switch_handler(functools.partial(_SSHInteractiveHandler, tab))
    return tab


class Vt100Tab(Tab):
    def __init__(self, tosh, session):
        super().__init__(tosh)
        self.title = 'SSH'
        self._session = session

        self._screen = BetterScreen(20, 80, self.write_to_ssh)
        self._stream = BetterStream(self._screen)
        self._stream.attach(self._screen)

        self.layout = Vt100Window(self._screen, self)

    def paste(self, event):
        self.write_to_ssh(event.data)

    def write_to_ssh(self, data):
        self._session.channel.write(data)

    def write_to_screen(self, data):
        self._stream.feed(data)
        self._tosh.refresh()

    def set_size(self, w, h):
        self._session.channel.change_terminal_size(w, h)
        self._screen.resize(h, w)

class Vt100Window(Container):
    """
    Container that holds the VT100 control.
    """
    def __init__(self, screen, tab):
        self.screen = screen
        self._tab = tab
        self._scroll_pos = 0

    def reset(self):
        pass

    def preferred_width(self, cli, max_available_width):
        return LayoutDimension()

    def preferred_height(self, cli, width, max_available_height):
        return LayoutDimension()

    def _mouse_handler(self, cli, mouse_event):
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self._scroll_pos = min(0, self._scroll_pos + 3)
        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            max_scroll = min(max(0, self.screen.max_y - self.screen.lines), self.screen.get_history_limit())
            self._scroll_pos = max(-max_scroll, self._scroll_pos - 3)

    def write_to_screen(self, cli, screen, mouse_handlers, write_position):
        """
        Write window to screen. This renders the user control, the margins and
        copies everything over to the absolute position at the given screen.
        """
        self._tab.set_size(write_position.width, write_position.height)

        xmin = write_position.xpos
        xmax = xmin + write_position.width
        ymin = write_position.ypos
        ymax = ymin + write_position.height
        mouse_handlers.set_mouse_handler_for_range(xmin, xmax, ymin, ymax, self._mouse_handler)

        # Render UserControl.
        temp_screen = self.screen.pt_screen

        # Write body to screen.
        self._copy_body(cli, temp_screen, screen, write_position, write_position.width)

    def _copy_body(self, cli, temp_screen, new_screen, write_position, width):
        """
        Copy characters from the temp screen that we got from the `UIControl`
        to the real screen.
        """
        xpos = write_position.xpos
        ypos = write_position.ypos
        height = write_position.height

        temp_buffer = temp_screen.data_buffer
        new_buffer = new_screen.data_buffer
        temp_screen_height = temp_screen.height

        vertical_scroll = self.screen.line_offset
        y = 0

        # Now copy the region we need to the real screen.
        for y in range(0, height):
            # We keep local row variables. (Don't look up the row in the dict
            # for each iteration of the nested loop.)
            new_row = new_buffer[y + ypos]

            if y >= temp_screen_height and y >= write_position.height:
                # Break out of for loop when we pass after the last row of the
                # temp screen. (We use the 'y' position for calculation of new
                # screen's height.)
                break
            else:
                temp_row = temp_buffer[y + vertical_scroll + self._scroll_pos]

                # Copy row content, except for transparent tokens.
                # (This is useful in case of floats.)
                for x in range(0, width):
                    new_row[x + xpos] = temp_row[x]

        new_screen.cursor_position = Point(
            y=temp_screen.cursor_position.y + ypos - vertical_scroll,
            x=temp_screen.cursor_position.x + xpos)
        new_screen.show_cursor = temp_screen.show_cursor and self._scroll_pos == 0

        # Update height of the output screen. (new_screen.write_data is not
        # called, so the screen is not aware of its height.)
        new_screen.height = max(new_screen.height, ypos + y + 1)

    def walk(self, cli):
        # Only yield self. A window doesn't have children.
        yield self
