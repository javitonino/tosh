from prompt_toolkit.layout import controls
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.shortcuts import create_prompt_layout
from prompt_toolkit.token import Token
from prompt_toolkit.layout.containers import ScrollOffsets, HSplit
from prompt_toolkit.layout.lexers import PygmentsLexer

from ..parser import CommandLineLexer
from .scroll_window import ScrollWindow
from .tab import Tab


class ToshTab(Tab):
    def __init__(self, tosh):
        super().__init__(tosh, prompt_key_bindings=True)
        self.layout = ToshWindow(tosh)
        self.title = 'Prompt'

    def paste(self, event):
        event.current_buffer.insert_text(event.data)

class ToshWindow(HSplit):
    def __init__(self, tosh):
        self._tosh = tosh
        super().__init__(self.create_layout())

    def get_prompt_tokens(self, cli):
        return self._tosh.style.get_template('prompt')

    def create_layout(self):
        self.prompt_layout = create_prompt_layout(
            get_prompt_tokens=self.get_prompt_tokens,
            reserve_space_for_menu=4,
            display_completions_in_columns=True,
            lexer=CommandLineLexer(self._tosh)
        )
        layout = [
            ScrollWindow(
                controls.TokenListControl(self._tosh.tasks.get_tokens),
                wrap_lines=True,
                scroll_offsets=ScrollOffsets(top=0, bottom=10000),
                height=D(preferred=10000)
            ),
            self.prompt_layout
        ]
        return layout
