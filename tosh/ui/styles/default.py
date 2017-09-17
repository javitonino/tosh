"""Default style."""

from prompt_toolkit.token import Token

style = {
    # Used from the main code
    Token.Task.Result:          '',

    Token.Lexer.BareWord:        '#8364C5',
    Token.Lexer.Variable:        '#73C86B',
    Token.Lexer.Command:         '#FFFFFF',
    Token.Lexer.Literal:         '#73C86B',
    Token.Lexer.String:          '#1785FB',
    Token.Lexer.Integer:         '#1785FB',
    Token.Lexer.Assign:          '#f24440',
    Token.Lexer.Access:          '#f24440',
    Token.Lexer.StartSubCommand: '#f24440',
    Token.Lexer.EndSubCommand:   '#f24440',
    Token.Lexer.Error:           'bg:#f24440 #000',
    Token.Lexer.InterToken:      '#FFFFFF',

    # Used only in templates
    Token.Tabs:                 'bg:#647083',
    Token.Tabs.Tab:             '#1785FB',
    Token.Tabs.Tab.Text:        'bg:#1785FB #222',
    Token.Tabs.Tab.Active:      '#73C86B',
    Token.Tabs.Tab.Active.Text: 'bg:#73C86B #222',

    Token.Task.Status.Waiting:  '#647083',
    Token.Task.Status.Running:  '#1785FB',
    Token.Task.Status.Success:  '#73C86B',
    Token.Task.Status.Error:    '#f24440',

    Token.Prompt:               '#f24440',
    Token.Prompt.Text:          '#fff bg:#f24440',
}

def _tab_template(tab_style):
    """Helper for tab templates given a style (tab active)."""
    return [(tab_style, '▐'), (tab_style.Text, '[{index}] {tab.title}'), (tab_style, '▌')]

templates = {
    # Tabs
    'tab':           _tab_template(Token.Tabs.Tab),
    'tab.active':    _tab_template(Token.Tabs.Tab.Active),
    'tab.separator': [],

    # Tasks
    'task.status.waiting': [(Token.Task.Status.Waiting, '■')],
    'task.status.running': [(Token.Task.Status.Running, '●')],
    'task.status.success': [(Token.Task.Status.Success, '✔')],
    'task.status.error':   [(Token.Task.Status.Error,   '✖')],

    # Prompt
    'prompt': [(Token.Prompt.Text, 'tosh'), (Token.Prompt, '▌')]
}
