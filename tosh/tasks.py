import asyncio
from enum import Enum
import os
import traceback

from prompt_toolkit.token import Token
from prompt_toolkit.mouse_events import MouseEventType

class TaskManager:
    def __init__(self, tosh):
        self.tosh = tosh
        self._tasks = []

    def get_tokens(self, _):
        if not self._tasks:
            return [(Token.Result, 'No tasks\n')]

        tokens = []
        for index, task in enumerate(self._tasks):
            if index > 0:
                tokens.append((Token.Task.Separator, '\n'))
            tokens += task.tokens()

        return tokens

    def refresh(self):
        self.tosh.refresh()


class Task:
    Status = Enum('Status', ['Waiting', 'Running', 'Success', 'Error'])

    def __init__(self, tosh):
        self._tosh = tosh
        self._status = Task.Status.Waiting
        self._status_line_tokens = []
        self._output_token_lines = []
        self._children = []

    def _set_output_text(self, text):
        self._output_token_lines = [[self._token(line)] for line in text.split('\n')]

    def tokens(self):
        tokens = []
        for line in self._token_lines():
            tokens += line + [self._token('\n')]
        return tokens

    def _token_lines(self):
        status_line = self._status_tokens() + [self._token(' ')] + self._status_line_tokens
        return [status_line] + self._children_token_lines() + self._output_token_lines

    def _children_token_lines(self):
        token_lines = []
        active_children = any(child._status is not Task.Status.Success for child in self._children)
        if self._children and active_children:
            for child in self._children[:-1]:
                lines = child._token_lines()
                token_lines.append([self._token('├╴')] + lines[0])
                for l in lines[1:]:
                    token_lines.append([self._token('│ ')] + l)
                pass
            last_child = self._children[-1]
            lines = last_child._token_lines()
            token_lines.append([self._token('└╴')] + lines[0])
            for l in lines[1:]:
                token_lines.append([self._token('  ')] + l)
        return token_lines

    def _token(self, text, style=Token.Task.Result):
        return (style, text, self._mouse_handler)

    def _status_tokens(self):
        STATUS_TEMPLATES = {
            Task.Status.Waiting: 'task.status.waiting',
            Task.Status.Running: 'task.status.running',
            Task.Status.Success: 'task.status.success',
            Task.Status.Error:   'task.status.error'
        }
        template = STATUS_TEMPLATES[self._status]
        return self._tosh.style.get_template(template, mouse_handler=self._mouse_handler)

    def _mouse_handler(self, _, event):
        if event.event_type == MouseEventType.MOUSE_DOWN:
            return self._clicked()
        else:
            return NotImplemented

    def _clicked(self):
        pass

    async def sub(self, task_or_func, *args, **kwargs):
        if isinstance(task_or_func, Task):
            _task = task_or_func
        else:
            _task = task_or_func(*args, **kwargs, _tosh=self._tosh)
            assert isinstance(_task, Task), str(task_or_func) + ' is not a task'
        self._children.append(_task)
        result = await _task.run()
        return result

    async def parallel(self, tasks):
        _parallel_tasks = []
        for (task_func, args, kwargs) in tasks:
            _task = task_func(*args, **kwargs, _tosh=self._tosh)
            assert isinstance(_task, Task), str(task_func) + ' is not a task'
            self._children.append(_task)
            _parallel_tasks.append(asyncio.ensure_future(_task.run()))

        results = await asyncio.gather(*_parallel_tasks, return_exceptions=True)
        return results

class CoroutineTask(Task):
    def __init__(self, tosh, coroutine, title):
        super().__init__(tosh)
        self._coroutine = coroutine
        self._status_line_tokens = [self._token(title)]

    async def run(self):
        self._status = Task.Status.Running
        self._tosh.refresh()
        try:
            result = await self._coroutine
            self._status = Task.Status.Success
            return result
        except BaseException as e:
            self._status = Task.Status.Error
            raise e
        finally:
            self._tosh.refresh()


class FakeTask:
    async def sub(self, task_func, *args, **kwargs):
        if isinstance(task_func, Task):
            return (await task_func.run())
        else:
            return (await task_func(*args, **kwargs))

# Decorator
def task(title):
    def task_decorator(func):
        def task_method(*args, **kwargs):
            try:
                tosh = kwargs.pop('_tosh')
                _task = CoroutineTask.__new__(CoroutineTask)
                _task.__init__(tosh, func(*args, **kwargs, task=_task), title.format(pos=args, kw=kwargs))
                return _task
            except KeyError:
                return func(*args, **kwargs, task=FakeTask())
        task_method._returns_task = True  # Ugly hack, see variable.AttributeAccessTask._is_task_function
        return task_method
    return task_decorator
