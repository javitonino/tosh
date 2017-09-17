import asyncio
import traceback

from .tasks import Task
from .command import CommandFailedException

class Statement(Task):
    def __init__(self, tosh):
        from .parser import CommandLineLexer
        super().__init__(tosh)
        self._output = []
        self._lexer = CommandLineLexer(self._tosh)

    def set_cmdline(self, cmdline):
        self._status_line_tokens = self._lexer.lex_cmdline(cmdline, show_errors=False)

    async def run(self):
        self._status = Task.Status.Running
        self._tosh.refresh()
        try:
            result = await self._run()
            self._status = Task.Status.Success
            return result
        except CommandFailedException:
            self._status = Task.Status.Error
        except BaseException as e:
            self._status = Task.Status.Error
            self._set_output_text(traceback.format_exc())
        finally:
            self._tosh.refresh()

class CommandStatement(Statement):
    def __init__(self, tosh, task):
        super().__init__(tosh)
        self._task = task

    async def _run(self):
        await self.sub(self._task)

class AssignmentStatement(Statement):
    def __init__(self, tosh, variable, task):
        super().__init__(tosh)
        self._task = task
        self._varname = variable

    async def _run(self):
        if not self._task.return_type:
            raise AttributeError("Right hand side expression does not returns a variable")
        result = await self.sub(self._task)
        self._tosh.variables[self._varname] = result
        result.var_name = self._varname
        out_line = [self._token("{} = ".format(self._varname))] + result.tokens()
        self._output_token_lines = [out_line]

class ErrorStatement(Statement):
    def __init__(self, tosh, cmdline, error):
        super().__init__(tosh)
        self._set_output_text(error)
        self._status = Task.Status.Error
        self.set_cmdline(cmdline)
