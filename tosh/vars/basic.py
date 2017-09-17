"""Basic variable types."""
import functools

from ..variable import Variable


class List(Variable):
    """List of things."""

    class _ListAttributes:
        def __init__(self, item_class):
            self._item_class = item_class
            self.list_attributes = {
                "count": (String, List.count)
            }

        def __getitem__(self, key):
            try:
                return (self._item_class, functools.partial(List.get_item, key=int(key)))
            except ValueError:
                return self.list_attributes[key]

    def __init__(self, item_class, items=None):
        """
        Create a list of things.

        Just passing the item_class can be used to represent the type of this list to use as a return_type.
        Passing both the type and list of items (even if empty) creates the actual list.
        """
        self.attributes = List._ListAttributes(item_class)
        self._item_class = item_class
        self._items = items

    @property
    def class_name(self):
        """Class name of the list, uses brackets to mark it as such."""
        return "[{}]".format(self._item_class.class_name)

    @property
    def default_var_name(self):
        """Default variable name, built by adding an `s` to the end of the item type."""
        return self._item_class.default_var_name + 's'

    def get_item(self, key):
        """
        Get an item in the list.

        This is actually an attribute (any number) defined in _ListAttributes.
        """
        return self._items[key]

    def count(self):
        """
        Get the number of elements on the list.

        This is an attribute, see _ListAttributes.
        """
        return len(self._items)

    def tokens(self):
        """Show the elements inside the list."""
        tokens = []
        for idx, it in enumerate(self._items):
            tokens.append(self._token(' [{:>02}] '.format(idx)))
            tokens += it.tokens()
            tokens.append(self._token('\n'))
        return tokens

    def type(self):
        """The type of the list, when this class is acting as the metaclass."""
        return self


class String(Variable):
    """Represents a string."""

    def __init__(self, tosh, string):
        """Wrap a string in a variable."""
        super().__init__(tosh)
        self.string = string

    def tokens(self):
        """Representation of this string."""
        return [self._token(self.string)]

    @staticmethod
    async def _load(string, task):
        return String(task._tosh, string)


class Integer(Variable):
    """Represents an integer."""

    def __init__(self, tosh, integer):
        """Wrap an integer in a variable."""
        super().__init__(tosh)
        self._integer = integer

    def tokens(self):
        """Representation of the integer."""
        return [self._token(str(self._integer))]

    @staticmethod
    async def _load(integer, task):
        return Integer(task._tosh, integer)
