import functools

from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import TokenListControl
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.token import Token

from .tosh_tab import ToshTab


class MainWindow(HSplit):
    def __init__(self, tosh):
        self._tosh = tosh
        self._tabs = [ToshTab(tosh)]
        self._active_tab = 0
        layout = [
            Window(
                TokenListControl(
                    self._get_tabs_tokens,
                    default_char=Char(' ', Token.Tabs),
                ),
                height=D(max=1)
            ),
            self._tabs[0].layout
        ]
        super().__init__(layout)

    def add_tab(self, tab, switch_to=False):
        self._tabs.append(tab)
        if switch_to:
            self.switch_tab(len(self._tabs) - 1)
        self._tosh.refresh()

    def switch_tab(self, idx):
        if idx < 0 or idx >= len(self._tabs):
            return
        self._active_tab = idx
        self.children[1] = self._tabs[self._active_tab].layout
        self._tosh.refresh()

    def next_tab(self):
        self.switch_tab((self._active_tab + 1) % len(self._tabs))

    def prev_tab(self):
        self.switch_tab((self._active_tab - 1) % len(self._tabs))

    def active_tab(self):
        return self._tabs[self._active_tab]

    def close_tab(self, tab):
        if self.active_tab() == tab:
            self.switch_tab(self._active_tab - 1)
        self._tabs.remove(tab)
        self._tosh.refresh()
        if not self._tabs:
            self._tosh._cli.exit()

    def _get_tabs_tokens(self, _):
        tokens = []
        for idx, tab in enumerate(self._tabs):
            if idx != 0:
                tokens += self._tosh.style.get_template('tab.separator')
            template = 'tab.active' if idx == self._active_tab else 'tab'
            tokens += self._tosh.style.get_template(template, index=idx + 1, tab=tab,
                                                       mouse_handler=functools.partial(self._mouse_handler, idx))

        return tokens

    def _mouse_handler(self, tab_index, _, event):
        if event.event_type == MouseEventType.MOUSE_DOWN:
            self.switch_tab(tab_index)
        else:
            return NotImplemented
