class Tab:
    def __init__(self, tosh, prompt_key_bindings=False):
        self._tosh = tosh
        self.title = 'Tab'
        self.layout = None
        self.prompt_key_bindings = prompt_key_bindings

    def close(self):
        self._tosh.window.close_tab(self)
