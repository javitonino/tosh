"""HTTP link parsing and variables."""
from urllib.parse import urlparse
import aiodns

from ..tasks import task, Task
from ..variable import Variable, LoadVariableTask


class _LoadLinkTask(LoadVariableTask):
    def __init__(self, tosh, return_type, url, loader):
        super().__init__(tosh, return_type, url)
        self._loader = loader

    async def run(self):
        self._status = Task.Status.Running
        self._tosh.refresh()
        try:
            result = await self._loader._load(self._argument, self)
            self._status = Task.Status.Success
            return result
        except BaseException as e:
            self._status = Task.Status.Error
            raise e
        finally:
            self._tosh.refresh()


class Link(Variable):
    """
    Pseudo-variable representing any link.

    Actually returns one of the Link variables depending on the domain of the link.
    """

    prefix = 'l'
    _classes = []

    @staticmethod
    def _link_type(url):
        urlparts = urlparse(url)
        for link_cls in Link._classes:
            return_type = link_cls.return_type(urlparts)
            if return_type:
                return (link_cls, return_type)
        raise ValueError("Don't know what to do with link " + url)

    @classmethod
    def load_task(cls, tosh, argument):
        """Return a task to initialize an instance of this variable."""
        return _LoadLinkTask(tosh, Link._link_type(argument)[1], argument, Link._link_type(argument)[0])

    @classmethod
    @task("Loading {pos[0].class_name} {pos[1]}")
    async def load(cls, argument, *, task):
        """Initialize and instance of this variable."""
        return (await Link._link_type(argument)[0]._load(argument, task))


def register_link(cls):
    """Decorator, register a link subclass."""
    Link._classes.append(cls)
    return cls
