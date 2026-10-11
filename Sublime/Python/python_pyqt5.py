import sublime
import sublime_plugin

import os
import subprocess

class Command(object):
    """Base class for external commands"""
    def __init__(self, command):
        self.command = command
        self.proc = None

    def launch(self):
        """Launch the external process"""
        kwargs = {
            'cwd': os.path.dirname(os.path.abspath(__file__)),
            'bufsize': -1
        }

        if sublime.platform() == 'windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs['startupinfo'] = startupinfo

        sub_args = [self.command] + self.options
        self.proc = subprocess.Popen(sub_args, **kwargs)

class PyUicCommand(Command):
    def __init__(self, window):
        self.window = window
        self.options = []

        command = "pyuic5"
        if command is None:
            self.is_valid = False
            sublime.error_message(
                'PyQt5-uic application path is not configured'
            )
        else:
            self.is_valid = True
            super(PyUicCommand, self).__init__(command)

    def compile(self, filename=None):
        """Compile a UI file"""

        if filename is None:
            filename = self.window.active_view().file_name()
        
        
        self.options += ['-o', filename.replace('.ui', '_UI.py'), filename]
        self.launch()

class CompileUiCommand(sublime_plugin.WindowCommand):
    """Compile Qt UI file"""
    def run(self, files=[]):
        if not files:
            PyUicCommand(self.window).compile()
        else:
            for filename in files:
                PyUicCommand(self.window).compile(filename)

    def is_enabled(self, files=[]):
        """Determine if the command is enabled"""
        if not files:
            if (not self.window.active_view() or not
                    self.window.active_view().file_name().endswith('.ui')):
                return False
        else:
            for filename in files:
                if not filename.endswith('.ui'):
                    return False

        return True
