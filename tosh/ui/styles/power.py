"""Fancy style for fonts with Powerline symbols."""

from prompt_toolkit.token import Token

style = {
    Token.Tabs.Tab:             '#bbb',
    Token.Tabs.Tab.Text:        'bg:#bbb #222',
    Token.Tabs.Tab.Active:      '#0bb',
    Token.Tabs.Tab.Active.Text: 'bg:#0bb #222',
}


def _tab_template(tab_style):
    """Helper for tab templates given a style (tab active)."""
    return [(tab_style, '\ue0ba'), (tab_style.Text, '[{index}] {tab.title}'), (tab_style, '\ue0b8')]

templates = {
    'tab':           _tab_template(Token.Tabs.Tab),
    'tab.active':    _tab_template(Token.Tabs.Tab.Active),

    'prompt': [(Token.Prompt.Text, 'tosh'), (Token.Prompt, '\ue0b4 ')]
}
