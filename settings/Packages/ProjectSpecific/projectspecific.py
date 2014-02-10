#
# Copyright 2012 by Kay-Uwe (Kiwi) Lorenz
# Published under New BSD License, see LICENSE.txt for details.
#

import sublime, sublime_plugin, sys, hashlib, os, glob, json, re
import os.path as P

DEBUG = False
def debug(s, *args):
    if DEBUG:
        sys.stderr.write(s % args)

SUBLIME_DRV = re.compile('^/([A-Z])/')

def get_active_project(window, current_view=None):

    def get_session_file(auto=False):
        if auto:
            ses_file = 'Auto Save Session.sublime_session'
        else:
            ses_file = 'Session.sublime_session'

        settings_dir = os.path.join(sublime.packages_path(), '..', 'Settings')
        window_info = {}

        ses_file = os.path.join(settings_dir, ses_file)
        if os.path.exists(ses_file):
            with open(ses_file, 'r') as input:
                return json.loads(input.read(), strict=False)

        return {}

    ses = get_session_file(auto=True)
    if not ses:
        sys.stderr.write("auto session file does not exist\n")
        return ""
        #window.ok_cancel_dialog("Auto Save Session File does not exist")

    window_id = window.id()
    for w in ses['windows']:
        if w['window_id'] == window_id:
            project = w['workspace_name']
	    if not project: return ""
            if sublime.platform() == 'windows':
                project =  os.path.normpath(SUBLIME_DRV.sub('\\1:/', project))
            return project

    sys.stderr.write("could not find window id in auto session file\n")
    return ""
    #WIN_DRV = re.compile('^[A-Za-z]:')


class ProjectSpecific(sublime_plugin.EventListener):
    active = None
    projects = {}
    files = []
    backup_settings = {}
    activating = {}
    PROJECT_SPECIFIC_DIR = os.path.join(sublime.packages_path(), 'User', 
		    'Project-Specific')
    current_view = None

    #def __init__(self):
        #self.project_manager = ProjectManager()

    def get_on_change(self, settings, name, key):
        '''on changing a setting, remove the backup, that we do not override it'''

        def on_change(*args, **kargs):
            del self.backup_settings[name][key]
            settings.clear_on_change(key)

        return on_change

    def deactivate(self, project):
        project_name = os.path.splitext(os.path.basename(project))[0]
        for f in glob.glob("%s/%s/*.last" % (self.PROJECT_SPECIFIC_DIR, project_name)):
            os.remove(f)

        for f in self.files:
            if P.exists(f):
                os.rename(f, f+'.last')

        for setting, values in self.backup_settings.items():
            settings = sublime.load_settings(setting)
            for k,v in values.items():
                sys.stderr.write("%s: %s\n" % (k,v))
                settings.clear_on_change(k)
                if v is None:
                    settings.erase(k)
                else:
                    settings.set(k, v)

        self.backup_settings.clear()
        self.files = []
        self.active = None

    def get_make_commands(self, project):
        # create make file target sublime commands
        project_dir = os.path.dirname(project)
        makefile    = os.path.join(project_dir, "Makefile")
        #sys.stderr.write("Makefile: %s\n" % makefile)

        commands = []
        if os.path.exists(makefile):

            with open(makefile, 'rb') as f:
                content = f.read()

            sublime_targets = re.search(r"""(?x)
                    (?m) ^\.SUBLIME_TARGETS:\s+
                         ([^\n]*((?<=\\)\n[^\n]*)*)\n""", content)
            if sublime_targets:
                sublime_targets = sublime_targets.group(1).replace("\\\n", " ").split()

            else:
                sublime_targets = []
                for m in re.finditer(r'(?m)^(\w[\w\-]*):', content):
                    sublime_targets.append(m.group(1))

            for t in sublime_targets:
                commands.append({
    				"command": "exec",
    				"caption": ":make %s" % t,
    				"args": {
    					"cmd": ["make", t ],
    					"working_dir": project_dir,
    				}
    			})

        return commands


    def do_activate(self, project, settings):
        self.deactivate(project)

        self.active = project

        self.backup_settings.clear()

        if 0:
            make_commands = self.get_make_commands(project)
        else:
            make_commands = []
        #sys.stderr.write("make_commands: %s\n" % make_commands)

        prjspec = settings.get('project-specific', {})
        #sys.stderr.write("prjspec: %s\n" % prjspec)
        if not prjspec and not len(make_commands): return

        project_name = os.path.splitext(os.path.basename(project))[0]

        prjdir = os.path.join(self.PROJECT_SPECIFIC_DIR, project_name)
        if not os.path.exists(prjdir):
            os.makedirs(prjdir)

        if len(make_commands):
            if 'sublime-commands' not in prjspec:
                prjspec['sublime-commands'] = []

        self.files = []
        for k,v in prjspec.items():
            if k == 'sublime-commands':
                if isinstance(v, list):
                    v = {project_name: v}
                else:
                    v = v.copy()

                if len(make_commands):
                    v['project-specific-make-commands'] = make_commands

            #if k == 'DIRECTORY':
            #    if isinstance(v, basestring):
            #        v = [ v ]
            #    for dir in v:
            #        for 
            if isinstance(v, list):
                if k == 'sublime-keymap':
                    fn = P.join(prjdir, "%s.%s" % ('Default', k))
                else:
                    fn = P.join(prjdir, "%s.%s" % (project_name, k))

                with open(fn, 'wb') as f:
                    json.dump(v, f)
                    f.write("\n")

                self.files.append(fn)

            if isinstance(v, dict):
                for xk, xv in v.items():
                    if k == 'sublime-settings': # this must be done locally
                        settings_name = "%s.%s" % (xk, k)
                        settings = sublime.load_settings(settings_name)
                        backup = self.backup_settings[settings_name] = {}

                        if not isinstance(xv, dict): continue

                        for yk,yv in xv.items():
                            backup[yk] = settings.get(yk, None)
                            settings.set(yk, yv)
                            settings.add_on_change(yk, 
                                self.get_on_change(settings, settings_name, yk))

                        continue
                        
                    if k == 'sublime-keymap':
                        if 'linux' in xk.lower():
                            fn = P.join(prjdir, "Default (Linux).sublime-keymap")
                        elif 'windows' in xk.lower():
                            fn = P.join(prjdir, "Default (Windows).sublime-keymap")
                        elif 'osx' in xk.lower():
                            fn = P.join(prjdir, "Default (OSX).sublime-keymap")
                        else:
                            fn = P.join(prjdir, "Default.sublime-keymap")
                    else:
                        fn = P.join(prjdir, "%s.%s" % (xk, k))

                    with open(fn, 'wb') as f:
                        json.dump(xv, f)
                        f.write("\n")
                    self.files.append(fn)
            
    def activate(self, view):
        win_id = None
        try:
            window = view.window()
            if not window: return

            win_id = window.id()
            self.activating[win_id] = True

            file_name = view.file_name()

            project = None

            try:
                # sublime text 3
                project = window.project_file_name()
            except AttributeError:
                if file_name is None:
                    pass
                elif file_name.endswith('.sublime-project'):
                    project = view.file_name()
                else:
                    project = get_active_project(window, self.current_view)
    
            if self.current_view:
                window.focus_view(self.current_view)

            if not project:
                if self.active:
                    self.deactivate(self.active)

            else:
                if project != self.active:
                    self.do_activate(project, view.settings())
        finally:
            if win_id:
                self.activating[win_id] = False


    def on_activated(self, view):
        if not view.window(): return
        win_id = view.window().id()

        if win_id not in self.activating:
            self.activating[win_id] = False

        if not self.activating[win_id]:
            debug("on_activated: %s\n" % view.file_name())
            sublime.set_timeout(lambda: self.activate(view), 1)

    if 0:
      def on_deactivated(self, view):
        if not view.window(): return
        win_id = view.window().id()

        if win_id not in self.activating:
            self.activating[win_id] = False

        if not self.activating[win_id]:
            self.current_view = view

    def on_post_save(self, view):
        win_id = view.window().id()
        if win_id not in self.activating:
            self.activating[win_id] = False

        if not self.activating[win_id]:
            if view.file_name() == self.active:
                try:
                    self.activating[win_id] = True
                    self.do_activate(self.active, view.settings())
                finally:
                    self.activating[win_id] = False


class ProjectSpecificHelpCommand(sublime_plugin.WindowCommand):

    def run(self, **kargs):
        import webbrowser
        webbrowser.open("https://bitbucket.org/klorenz/projectspecific")

