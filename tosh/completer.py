import re

from prompt_toolkit.completion import Completer, Completion

from .parser import CommandLineLexer
from .command import Command
from .variable import Variable

class CommandLineCompleter(Completer):
    """Quick and dirty completer that sucks in many ways."""
    def __init__(self, tosh):
        self._tosh = tosh
        self._lexer = CommandLineLexer(self._tosh)

    def _commands(self):
        return Command.all_commands.keys()

    def _tokens(self, data):
        self._lexer.lexer.input(data)
        return list(self._lexer.lexer)

    def _expressions(self, prefix_commands, start_position=0):
        for n, v in self._tosh.variables.items():
            yield Completion(n, start_position, display='{} ({})'.format(n, v.class_name))

        for n, c in Command.all_commands.items():
            cmd = '(' + n if prefix_commands else n
            yield Completion(cmd, start_position, display="{} ({})".format(cmd, c.title))

        for p, c in Variable.by_prefix.items():
            yield Completion(p + '""', start_position, display='{}"" ({})'.format(p, c.class_name))

    def _add_space(self, iterator, fix):
        for i in iterator:
            i.start_position = fix
            yield i

    def get_completions(self, document, complete_event):
        fix = not re.search(r'[.=( ]$', document.text)
        for c in self._get_completions(document.text, fix):
            yield c

    def _get_completions(self, text, fix):
        try:
            tokens = self._tokens(text)
        except:
            return
        if tokens and fix:
            last_token = tokens.pop(-1)
            try:
                fix = -len(last_token.value.bare_word)
            except:
                try:
                    fix = -len(last_token.value)
                except:
                    return
        else:
            fix = 0
        if not tokens:
            # Start of line, complete variables and commands
            for i in self._add_space(self._expressions(False), fix):
                yield i
        else:
            # Multiple tokens, try to do something smart
            if tokens[-1].type == '=':
                # After an equal, return expressions
                for i in self._add_space(self._expressions(True), fix):
                    yield i
            elif tokens[-1].type == '(':
                # After a parens, return commands
                for i in self._add_space(self._commands(), fix):
                    yield i
            elif tokens[-1].type == '.':
                # After a dot, return attributes
                try:
                    var = tokens[-2].value.return_type
                    for c in self._add_space([Completion(a) for a in var.attributes.keys()], fix):
                        yield c
                except BaseException:
                    pass
            elif tokens[-1].type == 'COMMAND':
                # After a command, arguments
                try:
                    subcmds = tokens[-1].value.completions()
                    if subcmds:
                        for i in self._add_space([Completion(s) for s in subcmds], fix):
                            yield i
                    else:
                        for i in self._add_space(self._expressions(True), fix):
                            yield i
                except BaseException:
                    pass
            elif not fix and len(tokens) > 1 and tokens[-2].type == 'COMMAND':
                for i in self._add_space(self._expressions(True), fix):
                    yield i
