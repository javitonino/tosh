"""Lexer/parser for command line."""
from ply import lex, yacc
from prompt_toolkit.layout.lexers import Lexer
from prompt_toolkit.token import Token

from .command import Command
from .variable import Variable, GetVariableTask, AttributeAccessTask
from .vars import String, Integer
from .statements import CommandStatement, AssignmentStatement


class BareWord:
    """
    Represent a simple bare word.

    A bare word is anything you write in the command line that can be interpreted as a text constant.
    This class only represents words that have no other meaning.

    For example, commands are represented by a CommandTask that also has a bare_word attribute. This way, if the
    command is at the beginning of the line, it will be run as a command, but if used in the middle, it will
    be interpreted as a bare word, allowing it to be a constant parameter to another command.
    """

    def __init__(self, word):
        """Set the bare_word attribute."""
        self.bare_word = word


class CommandLineLexer(Lexer):
    """Lexer for the command line. See PLY dcos for details on the syntax."""
    tokens = ('BARE_WORD', 'VARIABLE', 'COMMAND', 'LITERAL', 'STRING', 'INTEGER')
    literals = ('=', '.', '(', ')')
    TOKEN_MAP = {
        'BARE_WORD': Token.Lexer.BareWord,
        'VARIABLE':  Token.Lexer.Variable,
        'COMMAND':   Token.Lexer.Command,
        'LITERAL':   Token.Lexer.Literal,
        'STRING':    Token.Lexer.String,
        'INTEGER':   Token.Lexer.Integer,
        '=':         Token.Lexer.Assign,
        '.':         Token.Lexer.Access,
        '(':         Token.Lexer.StartSubCommand,
        ')':         Token.Lexer.EndSubCommand
    }

    t_ignore = " \t"

    def __init__(self, tosh):
        """Initialize the lexer."""
        self._tosh = tosh
        self.lexer = lex.lex(module=self)

    def lex_document(self, cli, document):
        """Called from prompt_toolkit for command line highlighting."""
        lines = document.lines

        def _get_line(lineno, show_errors=True):
            return self.lex_cmdline(lines[lineno])
        return _get_line

    def lex_cmdline(self, cmdline, show_errors=True):
        """
        Return the tokens for the given line.

        Uses the subyacent PLY lexer for parsing the line and maps lexer tokens to prompt toolkit tokens.
        """

        def _get_text(t):
            try:
                return t.value.bare_word
            except:
                return str(t.value)
        try:
            self.lexer.input(cmdline)
            tokens = []
            pos = 0
            try:
                for t in self.lexer:
                    tokens.append((CommandLineLexer.TOKEN_MAP[t.type], cmdline[pos:self.lexer.lexpos]))
                    pos = self.lexer.lexpos
            except BaseException as e:
                tokens.append((Token.Lexer.Error, cmdline[pos:]))
                if show_errors:
                    tokens.append((Token.Lexer.InterToken, ' (' + str(e) + ')'))
            if pos < len(cmdline):
                tokens.append((Token.Lexer.InterToken, cmdline[pos:]))
            return tokens
        except IndexError:
            return []

    def t_LITERAL(self, t):
        r'\w+".*?"'
        (prefix, value, _) = t.value.split('"')
        try:
            varclass = Variable.by_prefix[prefix]
            t.value = varclass.load_task(self._tosh, value)
            return t
        except KeyError:
            raise KeyError("Unknown literal prefix {0}".format(prefix))

    def t_LINK(self, t):
        r'[a-z]+://[-\w/?&=%.#:]*'
        t.type = 'LITERAL'
        t.value = Variable["Link"].load_task(self._tosh, t.value)
        return t

    def t_STRING(self, t):
        r'".*?"'
        if t.value.strip('"').startswith('http'):
            t.type = 'LITERAL'
            t.value = Variable["Link"].load_task(self._tosh, t.value.strip('"'))
        else:
            t.value = String.load_task(self._tosh, t.value)
        return t

    def t_BARE_WORD(self, t):
        r'[^\W\d]\w*'
        if t.value in Command.all_commands:
            t.type = 'COMMAND'
            t.value = Command[t.value]
        elif t.value in self._tosh.variables:
            t.type = 'VARIABLE'
            t.value = GetVariableTask(self._tosh, t.value)
        else:
            t.type = 'BARE_WORD'
            t.value = BareWord(t.value)

        return t

    def t_INTEGER(self, t):
        r'\d+'
        t.value = Integer.load_task(self._tosh, t.value)
        return t

    def t_error(self, t):
        raise SyntaxError("Illegal character '%s'" % t.value[0])


class CommandLineParser:
    """Syntax parser for the command line. See PLY docs for details."""

    def __init__(self, tosh, base_dir):
        """Initialize the syntax parser."""
        self._tosh = tosh
        self._lexer = CommandLineLexer(tosh)
        self.tokens = self._lexer.tokens  # parser needs lexing tokens
        self._parser = yacc.yacc(module=self, picklefile=base_dir + '/parser.pickle')

    def parse(self, commandline):
        """Parse a command line."""
        return self._parser.parse(commandline, lexer=self._lexer.lexer)

    def p_assignment_statement(self, t):
        """
        statement : VARIABLE '=' expression
                  | VARIABLE '=' command
                  | BARE_WORD '=' expression
                  | BARE_WORD '=' command
        """
        t[0] = AssignmentStatement(self._tosh, t[1].bare_word, t[3])

    def p_autoassignment_statement(self, t):
        """
        statement : expression
        """
        t[0] = AssignmentStatement(self._tosh, Variable[t[1].return_type].default_var_name, t[1])

    def p_command_statement(self, t):
        "statement : command"
        return_type = t[1].return_type
        if return_type:
            t[0] = AssignmentStatement(self._tosh, Variable[t[1].return_type].default_var_name, t[1])
        else:
            t[0] = CommandStatement(self._tosh, t[1])

    def p_command(self, t):
        "command : COMMAND params"
        t[0] = t[1](self._tosh, t[2])

    def p_bare_command(self, t):
        "command : COMMAND"
        t[0] = t[1](self._tosh, [])

    def p_params(self, t):
        "params : params param"
        t[0] = t[1] + [t[2]]

    def p_params_last(self, t):
        "params : param"
        t[0] = [t[1]]

    def p_expression_literal(self, t):
        """
        expression : VARIABLE
                   | STRING
                   | LITERAL
                   | INTEGER
        """
        t[0] = t[1]

    def p_expression_access(self, t):
        "expression : expression '.' name"
        t[0] = AttributeAccessTask(self._tosh, t[1], t[3].bare_word)

    def p_expression_subcommand(self, t):
        "expression : '(' command ')'"
        t[2]._cmdline = '(' + str(t[2]) + ')'
        t[0] = t[2]

    # Expression has priority over name (bare word)
    def p_param(self, t):
        """
        param : expression
              | name
        """
        t[0] = t[1]

    def p_name(self, t):
        """
        name : COMMAND
             | VARIABLE
             | BARE_WORD
             | INTEGER
        """
        t[0] = t[1]

    def p_error(self, t):
        if t:
            raise SyntaxError("Syntax error at '%s'" % t.value)
        else:
            raise SyntaxError("Syntax error")
