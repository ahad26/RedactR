"""Talks to the start-up splash screen of the portable exe.

The PyInstaller bootloader shows the splash image immediately and lists the files
it unpacks. Once Python is running, these helpers replace that text with the
app's own loading steps and close the splash when the main window is ready.
When running from source there is no splash, so every call does nothing.
"""

try:
    import pyi_splash  # only exists inside a PyInstaller build that has a splash screen
except ImportError:
    pyi_splash = None


def update(message: str):
    if pyi_splash is not None:
        try:
            pyi_splash.update_text(message)
        except Exception:
            pass


def close():
    global pyi_splash
    if pyi_splash is not None:
        try:
            pyi_splash.close()
        except Exception:
            pass
        pyi_splash = None
