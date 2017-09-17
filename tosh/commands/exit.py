"""Command to open standby connections to servers in all clouds."""
import sys

from ..command import Command


class ExitCommand(Command):
    """Closes tosh."""

    title = 'Bye bye'

    command = 'exit'

    async def _run(self):
        self._tosh._cli.exit()
