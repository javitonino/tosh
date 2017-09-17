# tosh - the nonsense shell

This is a framework for writing asynchronous shells. Some features:
- Commands. Subclass the `Command` class to create custom commands.
- Variables. They store the result from other commands. They can have attributes that can be accessed on the fly (it calls a method). Subclass `Variable`.
- SSH sessions that can run commands on a machine or be switched to a fully interactive session.
- Customizable styles
- Very basic autocompletion

This was born as a side-project for fun, and it is still very much a work in progress, but it's starting to be useful.
Testers and suggestions welcome.

## What can I do?

Not much without some example commands. Try https://github.com/javitonino/toshql for a sample package and some usage examples.

