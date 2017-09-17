from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.key_binding.registry import ConditionalRegistry, MergedRegistry
from prompt_toolkit.keys import Keys
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding.bindings.basic import load_mouse_bindings

from pymux.key_mappings import prompt_toolkit_key_to_vt100_key


def _active_tab(cli):
    return cli.application.layout.active_tab()


def _in_prompt_tab(cli):
    return _active_tab(cli).prompt_key_bindings


def _in_interactive_tab(cli):
    return not _active_tab(cli).prompt_key_bindings


def get_key_bindings(tosh):
    global_registry = KeyBindingManager.for_prompt(enable_all=Condition(_in_prompt_tab)).registry

    mouse_registry = ConditionalRegistry(load_mouse_bindings(), Condition(_in_interactive_tab))
    prompt_registry = ConditionalRegistry(filter=Condition(_in_prompt_tab))
    interactive_registry = ConditionalRegistry(filter=Condition(_in_interactive_tab))

    @global_registry.add_binding(Keys.BracketedPaste)
    def _paste(event):
        tosh.window.active_tab().paste(event)

    @prompt_registry.add_binding(Keys.ControlW)
    @interactive_registry.add_binding(Keys.ControlB, 'w')
    def _close_tab(event):
        tosh.window.active_tab().close()

    @prompt_registry.add_binding(Keys.ControlT)
    @interactive_registry.add_binding(Keys.ControlB, 't')
    def _new_prompt_tab(event):
        from .tosh_tab import ToshTab
        tosh.window.add_tab(ToshTab(tosh))

    @interactive_registry.add_binding(Keys.Any)
    def _forward_to_session(event):
        tosh.window.active_tab().write_to_ssh(prompt_toolkit_key_to_vt100_key(event.key_sequence[0].key, True))

    @global_registry.add_binding(Keys.ControlB, '1')
    @global_registry.add_binding(Keys.ControlB, '2')
    @global_registry.add_binding(Keys.ControlB, '3')
    @global_registry.add_binding(Keys.ControlB, '4')
    @global_registry.add_binding(Keys.ControlB, '5')
    @global_registry.add_binding(Keys.ControlB, '6')
    @global_registry.add_binding(Keys.ControlB, '7')
    @global_registry.add_binding(Keys.ControlB, '8')
    @global_registry.add_binding(Keys.ControlB, '9')
    def _change_tab(event):
        tosh.window.switch_tab(int(event.key_sequence[-1].key) - 1)

    @global_registry.add_binding(Keys.ControlB, Keys.Left)
    def _prev_tab(_):
        tosh.window.prev_tab()

    @global_registry.add_binding(Keys.ControlB, Keys.Right)
    def _next_tab(_):
        tosh.window.next_tab()

    return MergedRegistry([global_registry, prompt_registry, interactive_registry, mouse_registry])
