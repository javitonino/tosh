"""
Library for connection to SSH servers.

Support multiple sessions per server, including batch console sessions and interactive sessions.
"""

import asyncio
import functools
import json
import re

import asyncssh

from tosh.tasks import task

_connections = {}
_connections_locks = {}


@task('Connecting to {pos[0]}')
async def get_connection(hostname, *, task):
    """Return a connection to the given server, creating it if no previous connection exists."""
    lock = _connections_locks.get(hostname, asyncio.Lock())
    with (await lock):
        if hostname not in _connections:
            parts = hostname.split(':')
            if len(parts) > 2:
                raise ValueError("Hostname invalid: " + hostname)
            if len(parts) == 2:
                conn = _SSHConnection(task._tosh, parts[0], port=int(parts[1]))
            else:
                conn = _SSHConnection(task._tosh, hostname)
            await conn.connect()
            _connections[hostname] = conn
    return _connections[hostname]


class _SSHConnection:
    """
    Connection to an SSH server.

    Can contain multiple sessions, normally one for running carto.sh command
    and an interactive one to connect directly to the UI for user use.
    """

    def __init__(self, tosh, hostname, port=22):
        self._tosh = tosh
        self._lock = asyncio.Lock()
        self._hostname = hostname
        self._port = port
        self.connection = None
        self._sessions = []

    async def connect(self):
        """Connect to the server, get_connection from this module automatically calls this."""
        options = {
            'username':    self._tosh.config.get('ssh', 'username'),
            'port':        self._port,
            'known_hosts': None
        }
        client_keys = self._tosh.config.get('ssh', 'client_keys')
        if client_keys is not None:
            options['client_keys'] = client_keys

        self.connection = await asyncssh.connect(self._hostname, **options)

    @task("Opening session with {pos[1].__name__} at {pos[0]._hostname}")
    async def get_session(self, session_class, **args):
        """Return a switchable session using the specified handler."""
        task = args.pop('task')
        with (await self._lock):
            try:
                return next(filter(lambda s: isinstance(s._handler, session_class), self._sessions))
            except StopIteration:
                new_session = await session_class.create_session(self, task._tosh, **args)
                self._sessions.append(new_session)
                return new_session

    def remove_session(self, session):
        """Remove a session from this connection."""
        if session in self._sessions:
            self._sessions.remove(session)

    def add_session(self, session):
        """Add a session to this connection."""
        self._sessions.append(session)


class _SSHSwitchableSession(asyncssh.SSHClientSession):
    """
    A class representing a single SSH session, which delegates its work to a handler.

    A handler is a class inheriting from _SSHHandler, which implements reading and writing to this session.
    The session allows to change the handler on the fly (switch_handler), which is specially useful to convert
    an existing console session (for scripting) to an interactive session (for direct human use).

    Access to its handler is serialized via asyncio locks. To get the handler, use an async context manager:

        with (await session) as handler:
            handler.do_something()

    This enforces that the handler is only accessed from a context manager, ensuring its correct release.
    """

    def __init__(self, connection, initial_handler):
        self.channel = None
        self._connection = connection
        self._handler = initial_handler(self)
        self._lock = asyncio.Lock()

    def switch_handler(self, new_handler):
        """
        Switch the current handler with another one.

        :param new_handler callable: Constructor for the new handler.
        """
        if not self._lock.locked():
            raise RuntimeError('Call switch_handler with a locked session (use the session context manager)')
        self._connection.remove_session(self)
        self._handler = new_handler(self)
        self._connection.add_session(self)

    def connection_made(self, chan):
        self.channel = chan

    def data_received(self, data, datatype):
        self._handler.data_received(data, datatype)

    def connection_lost(self, exc):
        self._connection.remove_session(self)
        self._handler.connection_lost(exc)

    @task('Adquiring lock for SSH session')
    async def handler(self, *, task):
        await self._lock.acquire()
        return self

    def __enter__(self):
        if not self._lock.locked():
            raise RuntimeError('Use the session context manager with "await"')
        return self._handler

    def __exit__(self, *_):
        self._lock.release()

    async def __aenter__(self):
        await self._lock.acquire()
        return self._handler

    async def __aexit__(self, *_):
        self._lock.release()


class _SSHHandler:
    def __init__(self, session):
        self._session = session

    def write(self, data):
        return self._session.channel.write(data)

    @classmethod
    async def _create_switchable_session(cls, connection, **kwargs):
        switchable_constructor = functools.partial(_SSHSwitchableSession, connection, cls)
        _, switchable = await connection.connection.create_session(switchable_constructor, **kwargs)
        return switchable


class _SSHInteractiveHandler(_SSHHandler):
    def __init__(self, tab, session):
        super().__init__(session)
        self._tab = tab

    def data_received(self, data, _: 'datatype'):
        self._tab.write_to_screen(data)

    def connection_lost(self, exc):
        self._tab.close()


class SSHConsoleHandler(_SSHHandler):
    _PROMPT_MATCHER = None

    '''
    An SSH session with functionality to wait for prompts and run commands
    '''
    def __init__(self, session):
        super().__init__(session)
        self._lock = asyncio.Lock()
        self._line_buffer = ''
        self._at_prompt = False
        self._waiter = None
        self._out_buffer = ''

    @classmethod
    async def create_session(cls, connection, tosh):
        '''
        Creates a console session using the default remote shell
        '''
        switchable = await cls._create_switchable_session(connection, term_type='vt100')
        await switchable._handler._wait_for_prompt()
        return switchable

    async def _wait_for_prompt(self):
        if not self._at_prompt:
            try:
                self._waiter = asyncio.Future()
                await self._waiter
                self._at_prompt = True
            finally:
                self._waiter = None

    async def run_command(self, command):
        with (await self._lock):
            # Wait for prompt and reset buffers
            await self._wait_for_prompt()
            self._out_buffer = ''
            self._line_buffer = ''

            # Run the command and wait for results
            self.write(command + '\n')
            self._at_prompt = False
            await self._wait_for_prompt()

            # Remove the command (first line) and prompt (last line) from the results
            return '\n'.join(self._out_buffer.split('\n')[1:-1])

    def data_received(self, data, _: 'datatype'):
        """
        Called by asyncssh when data is received.

        Adds the data to the command result buffer. Parses last line to look for the prompt if any.
        """
        self._out_buffer += data
        self._line_buffer += data
        lines = self._line_buffer.split('\n')
        self._line_buffer = lines[-1]

        if self._waiter:
            for l in lines:
                if self._PROMPT_MATCHER.search(l):
                    self._waiter.set_result(None)
                    break

    def connection_lost(self, exc):
        """Called when the connection is closed."""
        pass


class SSHRailsHandler(SSHConsoleHandler):
    _PROMPT_MATCHER = re.compile(r'irb\(main\):\d+:0> ')
    _OUTPUT_MARKER = 'to.sh>'

    @classmethod
    async def create_session(cls, connection, tosh, command_key):
        '''
        Creates a console session using the Rails console.
        '''
        switchable = await cls._create_switchable_session(
            connection,
            command=tosh.config.get('ssh', 'commands', command_key),
            term_type='vt100'
        )
        await switchable._handler._wait_for_prompt()
        return switchable

    @task('Running Rails command: {pos[1]}')
    async def get_object(self, command, *, task):
        """
        Run a command and returns the parsed response as a dictionary.

        This wraps the command, ading `to_json` in order to parse it easily.
        """
        wrapped_command = "puts '{}' + ({}).to_json".format(self._OUTPUT_MARKER, command)
        result = await self.run_command(wrapped_command)
        try:
            line = next(l[len(self._OUTPUT_MARKER):] for l in result.split('\n') if l.startswith(self._OUTPUT_MARKER))
            return json.loads(line)
        except StopIteration:
            raise RuntimeError("Command returned no results: " + result)


class SSHPsqlHandler(SSHConsoleHandler):
    _PROMPT_MATCHER = re.compile(r'\S+=# ')

    async def set_read_only(self):
        """Set the database to read-only (just in case)."""
        await self.run_command('SET default_transaction_read_only = on;')

    @classmethod
    async def create_session(cls, connection, tosh):
        '''
        Creates a console session using the Rails console.
        '''
        switchable = await cls._create_switchable_session(
            connection,
            command=tosh.config.get('ssh', 'commands', 'psql'),
            term_type='vt100'
        )
        await switchable._handler._wait_for_prompt()
        return switchable

    @task('Connecting to database: {pos[1]}')
    async def connect_db(self, dbname, *, task):
        await asyncio.sleep(2)
        result = await self.run_command("\c " + dbname)
        if 'FATAL' in result:
            raise RuntimeError("Database does not exist: " + result)
        await self.set_read_only()
