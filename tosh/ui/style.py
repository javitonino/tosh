"""
Tosh style loader. Loads the specified style on top of the default style.

Tosh styles include:
 - style: pygments style dictionary, mapping tokens to attributes
 - templates: a dictionary for UI element templates

 See the default style for a complete example. Copy into with a different name and overwrite as desired.
"""
from collections import ChainMap
from importlib import import_module
from prompt_toolkit.styles import style_from_dict, Style, Attrs
from prompt_toolkit.styles.utils import split_token_in_parts, merge_attrs


def _load_style(name):
    try:
        return import_module('tosh.ui.styles.' + name)
    except:
        raise NameError('Style not found: ' + name)


class ToshStyle(Style):

    """
    Represents a Tosh style, including styling and UI templates.

    From Pymux project. In order to proxy all the output from the processes (BetterScreen),
    it interprets all tokens starting with ('C,) as tokens that describe their own style.
    Also adds templates.
    """

    def __init__(self, style):
        """Initialize the style given the name."""
        base_module = _load_style('default')
        module = _load_style(style)

        self._style = style_from_dict(ChainMap(module.style, base_module.style))
        self._token_to_attrs_dict = None
        self._templates = ChainMap(module.templates, base_module.templates)

    def get_attrs_for_token(self, token):
        """Get the attributes for a token. Part of prompt_toolkit Style interface."""
        result = []
        for part in split_token_in_parts(token):
            result.append(self._get_attrs_for_token(part))
        return merge_attrs(result)

    def _get_attrs_for_token(self, token):
        if token and token[0] == 'C':
            # Token starts with ('C',). Token describes its own style.
            return Attrs(*token[1:])
        else:
            # Take styles from UI style.
            return self._style.get_attrs_for_token(token)

    def invalidation_hash(self):
        """Part of prompt_toolkit Style interface."""
        return None

    def get_template(self, template_name, mouse_handler=None, **kwargs):
        """Return the tokens corresponding to applying the kwargs to a template given by name."""
        template = self._templates[template_name]
        return [self._apply_template(token, mouse_handler, **kwargs) for token in template]

    @staticmethod
    def _apply_template(token, mouse_handler, **kwargs):
        style, text = token
        text = text.format(**kwargs)
        if mouse_handler:
            return style, text, mouse_handler
        else:
            return style, text
