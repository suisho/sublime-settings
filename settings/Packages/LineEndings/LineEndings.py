import sublime, sublime_plugin

def plugin_loaded():
	global s, Pref
	s = sublime.load_settings('LineEndings.sublime-settings')
	Pref = Pref()
	Pref.load()
	s.add_on_change('reload', lambda:Pref.load())

class Pref:
	def load(self):
		Pref.show_line_endings_on_status_bar          = s.get('show_line_endings_on_status_bar', True)
		Pref.alert_when_line_ending_is                = [s.lower() for s in s.get('alert_when_line_ending_is', [])]
		Pref.auto_convert_line_endings_to             = s.get('auto_convert_line_endings_to', '')

class StatusBarLineEndings(sublime_plugin.EventListener):

	def on_load(self, view):
		if view.line_endings().lower() in Pref.alert_when_line_ending_is:
			sublime.message_dialog(view.line_endings()+' line endings detected on file:\n\n'+view.file_name());

	def on_pre_save(self, view):
		if Pref.auto_convert_line_endings_to != '' and view.line_endings().lower() != Pref.auto_convert_line_endings_to.lower():
			view.set_line_endings(Pref.auto_convert_line_endings_to)

class SetLineEndingWindowCommand(sublime_plugin.TextCommand):

	def run(self, view, type):
		for view in sublime.active_window().views():
			view.set_line_endings(type)
		StatusBarLineEndings().on_load(sublime.active_window().active_view())

	def is_enabled(self):
		return len(sublime.active_window().views()) > 0

class SetLineEndingViewCommand(sublime_plugin.TextCommand):

	def run(self, view, type):
		view = sublime.active_window().active_view()
		view.set_line_endings(type)
		StatusBarLineEndings().on_load(view)

	def is_enabled(self):
		return len(sublime.active_window().views()) > 0

	def is_checked(self, type):
		if self.view.line_endings().lower() == type:
			return True
		else:
			return False

class ConvertIndentationWindowCommand(sublime_plugin.TextCommand):

	def run(self, view, type):
		for view in sublime.active_window().views():
			if type == 'spaces':
				view.run_command('expand_tabs', {"set_translate_tabs":True})
			else:
				view.run_command('unexpand_tabs', {"set_translate_tabs":True})
		StatusBarLineEndings().on_load(sublime.active_window().active_view())

	def is_enabled(self):
		return len(sublime.active_window().views()) > 0
