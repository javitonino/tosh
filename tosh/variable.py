"""Definition of base variable and loading tasks."""
import re

from prompt_toolkit.token import Token

from .tasks import task, Task


class LoadVariableTask(Task):
    """Task to load a variable from a variable literal or similar."""

    def __init__(self, tosh, return_type, argument):
        """Create a task to laod a variable given an argument (e.g: username)."""
        super().__init__(tosh)
        self.return_type = Variable[return_type]
        self._argument = argument
        self.bare_word = argument
        self._status_line_tokens = [self._token('Loading {} {}'.format(self.return_type.class_name, self._argument))]

    async def run(self):
        """Run this task, that will load the variable by calling `_load`."""
        self._status = Task.Status.Running
        self._tosh.refresh()
        try:
            result = await self.return_type._load(self._argument, self)
            self._status = Task.Status.Success
            return result
        except BaseException as e:
            self._status = Task.Status.Error
            raise e
        finally:
            self._tosh.refresh()


class AttributeAccessTask(Task):
    """Task to access the attribute of a variable."""

    def __init__(self, tosh, base_task, attr_name):
        """
        Create a task to access an attribute.

        Checks that the attribute is part of the first variable before evaluating the task (checks return_type)
         - base_task is a Task returning a variable.
         - attr_name is the name of the attribute.
        """
        super().__init__(tosh)
        base_type = Variable[base_task.return_type]
        return_type = base_type.attributes[attr_name][0]
        self.return_type = Variable[return_type]
        self._attr_name = attr_name
        self._base_task = base_task
        self._status_line_tokens = [self._token('Accessing {}.{}'.format(base_type.class_name, attr_name))]

    async def run(self):
        """Run the task."""
        self._status = Task.Status.Running
        self._tosh.refresh()
        try:
            base_object = await self.sub(self._base_task)
            result = await base_object.attribute(self._attr_name, self)
            self._status = Task.Status.Success
            return result
        except BaseException as e:
            self._status = Task.Status.Error
            raise e
        finally:
            self._tosh.refresh()


class GetVariableTask(Task):
    """
    Task to return a variable from memory.

    This operation is no asynchronous so there is no need for a task. It is here for API compatibility, so
    all commands can operate on tasks.
    """

    def __init__(self, tosh, varname):
        """Create a task to return a variable."""
        super().__init__(tosh)
        self._varname = varname
        self.return_type = self._var().type()
        self._status_line_tokens = [self._token('Get variable {} ({})'.format(varname, self.return_type.class_name))]

    async def run(self):
        """Just return the variable synchronously."""
        self._status = Task.Status.Success
        return self._var()

    def _var(self):
        return self._tosh.variables[self._varname]

    @property
    def bare_word(self):
        """Bare word (what the user wrote in the cli) for this variable, see CommandLineLexer."""
        return self._varname


class _VariableMeta(type):
    """
    Metaclass (object that represents a class) for Variables.

    Does attribute and variable registration.
    """

    by_class_name = {}
    by_prefix = {}

    class _AttributesDict(dict):
        # Decorator
        def register(self, name, return_type):
            def register_decorator(func):
                self[name] = (return_type, func)
                return func
            return register_decorator

    def __getitem__(cls, class_name):
        """
        Return a class given its name.

        Call like this: `Variable['User']`.

        This is neccessary to avoid circular dependencies between variables that have crossed references to each other,
        as imports won't work in such cases.
        """
        from .vars.basic import List
        if isinstance(class_name, type) or isinstance(class_name, List):
            return class_name
        elif isinstance(class_name, list):
            return List(cls[class_name[0]])

        if class_name.startswith('['):
            return List(cls[class_name[1:-1]])
        return cls.by_class_name[class_name]

    def __prepare__(name, bases):
        """Add an attribute registry to all variables."""
        return {'attributes': _VariableMeta._AttributesDict()}

    def __init__(self, name, bases, attrs):
        """Register the variable on class creation, and add missing attributes."""
        super().__init__(name, bases, attrs)

        # Register this variable
        self.by_class_name[name] = self
        if hasattr(self, 'prefix'):
            self.by_prefix[self.prefix] = self

        # Add default class/variable names
        if 'class_name' not in attrs:
            self.class_name = name
            self.default_var_name = re.sub(r'([A-Z])', r'_\1', name).lower()


class Variable(metaclass=_VariableMeta):
    """
    Class representing a Variable.

    Subclasses must/can implement:
     - `__init__`, calling the parent with a tosh instance
     - `prefix` attribute if they want to be loaded as literals, e.g: u"username" (optional)
     - `_load()` to initialize the variable, called from a task
     - `tokens()` for screen representation
     - `load_in_box()` to be executed when opening an interactive rails session with this variable (optional)

    Attributes can be registered like this (they can be plain functions or tasks (@task)):
    ```
    @attributes.register("attribute", Type)
    def attribute(self):
        pass
    ```
    """

    def __init__(self, tosh):
        """Initialize the Variable."""
        self._tosh = tosh
        self._var_name = None

    @classmethod
    def load_task(cls, tosh, argument):
        """Return a task to initialize an instance of this variable."""
        return LoadVariableTask(tosh, cls, argument)

    @classmethod
    @task("Loading {pos[0].class_name} {pos[1]}")
    async def load(cls, argument, *, task):
        """Initialize and instance of this variable."""
        return (await cls._load(argument, task))

    def _token(self, text, style=Token.Task.Result):
        return (style, text)

    async def load_in_box(self, handler):
        """Called to load this variable in a rails session in the box."""
        pass

    def type(self):
        """Return the type of this variable."""
        return self.__class__

    @property
    def var_name(self):
        """Return the name of this variable if specified (variable saved) or a default otherwise."""
        if self._var_name:
            return self._var_name
        else:
            return self.default_var_name

    @var_name.setter
    def var_name(self, varname):
        """Set the name of the variable."""
        self._var_name = varname

    async def attribute(self, attrname, task=None):
        """Load an attribute of this task, whether it is defined as a function or a task."""
        def _is_task_function(func):
            """Determine if a function is a task generator (@task decorated)."""
            try:
                return func._returns_task
            except:
                return False

        def _autobox(result):
            """Wrap a plan Python object in its variable counterpart."""
            from .vars import String, Integer
            if isinstance(result, str):
                return String(self._tosh, result)
            elif isinstance(result, int):
                return Integer(self._tosh, result)
            return result

        attribute_task = self.attributes[attrname][1]
        if _is_task_function(attribute_task):
            if task:
                result = await task.sub(attribute_task, self)
            else:
                result = await attribute_task(self)
        else:
            result = attribute_task(self)
        return _autobox(result)

# Loads all variables
from . import vars
