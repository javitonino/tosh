import asyncio
import traceback
import sys

from importlib import import_module
from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.shortcuts import create_asyncio_eventloop, create_output
from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer, AcceptAction
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from .ui.key_bindings import get_key_bindings
from .ui.main_window import MainWindow
from .ui.style import ToshStyle
from .tasks import TaskManager
from .parser import CommandLineParser
from .completer import CommandLineCompleter
from .statements import Statement, ErrorStatement

class Tosh:
    def __init__(self, base_dir, config):
        for module in config.get('modules'):
            import_module(module)

        self.tasks = TaskManager(self)
        self.window = MainWindow(self)
        self.style = ToshStyle(config.get('ui', 'style'))
        self._parser = CommandLineParser(self, base_dir)
        self.config = config
        self.variables = {}

        application = Application(
            layout=self.window,
            buffer=Buffer(
                enable_history_search=True,
                complete_while_typing=False,
                is_multiline=False,
                history=FileHistory(base_dir + "/history"),
                # validator=validator,
                completer=CommandLineCompleter(self),
                auto_suggest=AutoSuggestFromHistory(),
                accept_action=AcceptAction(self.run_command),
            ),
            mouse_support=config.get('ui', 'mouse'),
            style=self.style,
            key_bindings_registry=get_key_bindings(self),
            use_alternate_screen=True
        )

        self._cli = CommandLineInterface(
            application=application,
            eventloop=create_asyncio_eventloop(),
            output=create_output(true_color=True)
        )

    def refresh(self):
        self._cli.request_redraw()

    def _exception_handler(self, loop, context):
        self._cli.reset()
        print(context['message'])
        if 'exception' in context:
            traceback.print_exc()
        sys.exit(1)

    def run(self):
        for cmd in self.config.get('autostart'):
            cmd_task = self._parser.parse(cmd)
            cmd_task.set_cmdline(cmd)
            self.tasks._tasks.append(cmd_task)
            asyncio.ensure_future(cmd_task.run())

        asyncio.get_event_loop().set_exception_handler(self._exception_handler)
        try:
            asyncio.get_event_loop().run_until_complete(self._cli.run_async())
        except EOFError:
            pass

    def run_command(self, _, document):
        if not document.text:
            return
        try:
            cmd_task = self._parser.parse(document.text)
            if isinstance(cmd_task, Statement):
                cmd_task.set_cmdline(document.text)
                document.reset(append_to_history=True)
                self.tasks._tasks.append(cmd_task)
                asyncio.ensure_future(cmd_task.run())
            else:
                self.tasks._tasks.append(ErrorStatement(self, document.text, "Parser returned no task"))
                document.reset(append_to_history=False)
        except BaseException as e:
            # Last resort error handler
            self.tasks._tasks.append(ErrorStatement(self, document.text, traceback.format_exc()))
            document.reset(append_to_history=False)
