"""The generator application's core: finding the game, world codes, history, installation.

Nothing here draws a window. The window ([ADR 0004](docs/adr/0004-generator-application.md))
is a thin layer over these functions, so the same logic serves the command line, the
tests and whatever toolkit the packaged application uses.
"""
