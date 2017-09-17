"""Base class and task for commands."""
import traceback

from .tasks import Task


class CommandFailedException(BaseException):
    """Class to represent a failure in a command. Used to avoid printing multiple tracebacks on nested commands."""
    pass


class _CommandMeta(type):
    """
    Metaclass (object that represents a class) for Commands.

    Does command registration.
    """
    all_commands = {}

    @property
    def bare_word(cls):
        """All commands are bare_word equivalent to the command."""
        return cls.command

    def __getitem__(cls, class_name):
        """Returns a command by name. Use like `Command["rails"]`."""
        return cls.all_commands[class_name]

    def __prepare__(name, bases):
        """Add a default `return_type` to all commands."""
        return {'return_type': None}

    def __init__(self, name, bases, attrs):
        """Register the command."""
        super().__init__(name, bases, attrs)

        # Register this command
        if hasattr(self, 'command'):
            self.all_commands[self.command] = self


class Command(Task, metaclass=_CommandMeta):
    """
    A task that runs a command.

    To implement a command, inherit from this class and:
     - Include a class attribute `command = "cmd"` to specify the name of the command.
     - Implement a coroutine _run() which runs the command.
    """

    def __init__(self, tosh, arguments):
        """Initialize the command, given its arguments (list of tasks or bare words)."""
        super().__init__(tosh)
        self._arguments = arguments
        self._output = []
        self._status_line_tokens = [self._token(self.title)]

    async def run(self):
        """Run the command, updating the status. Delegates actual work to `_run`."""
        self._status = Task.Status.Running
        self._tosh.refresh()
        try:
            result = await self._run()
            self._status = Task.Status.Success
            return result
        except CommandFailedException:
            self._status = Task.Status.Error
            raise CommandFailedException()
        except BaseException as e:
            self._status = Task.Status.Error
            self._set_output_text(traceback.format_exc())
            raise CommandFailedException()
        finally:
            self._tosh.refresh()

    @staticmethod
    def completions():
        return []

# Loads all commands
from . import commands
