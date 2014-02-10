import json, re, os
import shutil, zipfile
import sublime, sublime_plugin

# Import default package for ST3 only. Needed to determine its path.
if not int(sublime.version()) < 3000:
  import Default

class QuickRefCommand(sublime_plugin.ApplicationCommand):
  def __init__(self):
    # Initialize list of commands. Needs to happen here since this value will 
    # determine whether to open or close the quick panel.
    self.command_list = None
    # Running Sublime Text 2?
    self.is_st2 = int(sublime.version()) < 3000

  def run(self, **kwargs):
    # Get paths.
    self.paths = self.get_paths()

    # Get OS platform.
    self.platform = sublime.platform()
    self.platform = self.platform[0].upper() + self.platform[1:].lower()

    # If the command list has not be defined, run the plugin.
    if not self.command_list:
      # Set a window reference.
      self.window = sublime.active_window()

      # Get settings.
      self.settings = self.get_settings()
      self.settings['regular_run_mode'] = kwargs['regular_run_mode'] if 'regular_run_mode' in kwargs else False

      try:
        self.command_list = []
        self.run_commands = []
        self.favourites = []

        self.fav_command_list = []
        self.fav_run_commands = []

        # Get favourites from file.
        if self.settings['show_favourites']:
          self._add_favourites()

        # Keep track of contexts to avoid duplicates.
        self.added_contexts = []

        # Keep track of commands to avoid duplicates. User commands should always
        # overwrite defualt key bindings and user key bidnings. User key bindings
        # should always overwrite default key bidnings.
        self.added_user_commands = []
        self.added_commands = []
        
        # Add commands.
        if self.settings['show_user_commands']:
          self._add_user_commands()
        if self.settings['show_user_key_bindings']:
          self._add_user_key_bindings()
        if self.settings['show_default_key_bindings']:
          self._add_default_key_bindings()

        # Sort lists alphabetically. Both lists have to be sorted in order to keep them
        # synchronized with each other.
        if self.settings['sort_alphabetically']:
          self.command_list.sort(key = lambda list: list[0].lower())
          self.run_commands.sort(key = lambda list: list[0].lower())

        # Always sort favourites.
        self.fav_command_list.sort(key = lambda list: list[0].lower())
        self.fav_run_commands.sort(key = lambda list: list[0].lower())

        # Concatenate favourites and other commands to one list.
        self.command_list = self.fav_command_list + self.command_list
        self.run_commands = self.fav_run_commands + self.run_commands

        # @todo: Disabled for now.
        # if os.path.exists(self.default_path + '/show_update_splash'):
        #   self.command_list = [['- QuickRef has been updated!', '- Select to remove this item and see what\'s new.']] + self.command_list
        #   self.run_commands = [['Show update']] + self.run_commands

        # Show quick panel with commands. Set a timeout to allow panel get ready before opening.
        sublime.set_timeout(lambda: self.window.show_quick_panel(self.command_list, self._on_select), 10)
      except Exception as e:
        sublime.status_message('QuickRef says: "_run() is misbehaving. Here\'s what happened: ' + str(e) + '"')

    # Otherwise close the quick panel.
    else:
      self.window.run_command('hide_overlay')

  def _add_favourites(self):
    """
    Add favourites from favourites file.
    """
    favourites = os.path.join(self.paths['user_data'], 'favourites.txt')
    if os.path.exists(favourites):
      with open(favourites, 'r') as content:
        for command in content:
          self.favourites.append(command.rstrip())

  def _add_user_commands(self):
    """
    Add commands specified in QuickRef user settings.
    """
    # Parse commands from user settings file.
    user_commands = self.settings['commands']

    for command in user_commands:
      # Put keys on one line, separate with commas.
      keys = ', '.join(command['keys'])
      # Add items.
      self._prepare_command(command, keys)
      # Add command to list of added commands.
      self.added_user_commands.append(command['command'])

  def _add_user_key_bindings(self):
    """
    Add user specified key bindings.
    """
    # Load and parse commands from user keymap file.
    user_key_bindings_path = os.path.join(self.paths['user'], 'Default (' + self.platform + ').sublime-keymap')
    user_key_bindings = self.parse_json_file(user_key_bindings_path, True)

    for command in user_key_bindings:
      # Put keys on one line, separate with commas.
      keys = ', '.join(command['keys'])
      # Add items.
      self._prepare_command(command, keys)
      # Add command to list of added commands.
      self.added_user_commands.append(command['command'])

  def _add_default_key_bindings(self):
    """
    Add default key bindings.
    """
    # Load and parse commands from default keymap file.
    default_keymap = self.get_default_keymap()
    default_key_bindings = self.parse_json_file(default_keymap, True)

    if self.settings['key_filter']:
      # Only add commands with specific shortcut keys.
      if not any(x in keys for x in self.settings['key_filter']):
        return

    for command in default_key_bindings:
      # Put keys on one line, separate with commas.
      keys = ', '.join(command['keys'])
      # Add items.
      self._prepare_command(command, keys)
      # Add command to list of added commands.
      self.added_commands.append(command['command'])

  def _prepare_command(self, command, keys):
    """
      Prepare commands for adding to command lists.
    """
    # Check if command is a favourite.
    self.is_favourite = True if command['command'] + ',' + keys in self.favourites else False
    # Ignore duplicates of user added or user keymap commands.
    if command['command'] in self.added_user_commands:
      return

    # If there is a user added caption, display that in the list instead of the command.
    caption = command['caption'] if 'caption' in command else command['command']
    # Add context associated with the command (if any).
    context = command['context'] if 'context' in command else ''
    # Add arguments associated with the command (if any).
    args = command['args'] if 'args' in command else ''

    if context and self.settings['show_command_contexts']:
      for sub_context in context:
        # Ignore commands with duplicate contexts.
        if self.settings['remove_duplicate_contexts']:
          if command['command'] + sub_context['key'] in self.added_contexts:
            continue

        # Beautify commands and prepare them for output.
        caption = self._beautify_caption(command, sub_context)
        # Add command to command lists.
        self._add_command(caption, command, keys, args, context)
        # Add sub context key to list of contexts.
        self.added_contexts.append(command['command'] + sub_context['key'])
    else:
      # Ignore duplicates of default commands.
      if self.settings['remove_duplicates']:
        if command['command'] in self.added_commands:
          return

      # Beautify commands and prepare them for output.
      caption = self._beautify_caption(command, '')
      # Add command to command lists.
      self._add_command(caption, command, keys, args, context)

  def _add_command(self, caption, command, keys, args, context):
    """
    Add command to command lists.
    """
    # Add caption and keyboard shortcuts.
    list_item = [caption] + [keys]
    # Add caption, command, arguments and context for each context.
    command_item = [caption] + [command['command']] + [args] + [context]

    # Divide favourites from other commands.        
    if self.is_favourite:
      self.fav_command_list.append(list_item)
      self.fav_run_commands.append(command_item)
    else:
      self.command_list.append(list_item)
      self.run_commands.append(command_item)

  def _beautify_caption(self, command, sub_context):
    """
    Make captions prettier.
    """
    if 'caption' in command:
      # Use supplied caption.
      caption = command['caption']
    elif self.settings['beautify_captions']:
      # Remove low dashes and capitalize first letter.
      caption = command['command'].replace('_', ' ').capitalize()
    else:
      # Keep command name as-is.
      caption = command['command']
    # If macro command, add macro name.
    if 'run_macro_file' == command['command']:
      caption += ' - ' + command['args']['file'].replace('Packages/Default/', '').replace('.sublime-macro', '')
    # Add context.
    if sub_context:
      caption += ' (' + sub_context['key'].replace('_', ' ').replace('setting.', '') + ')'
    # Add prefix to favourites only if showing favourites.
    if self.is_favourite and self.settings['show_favourites']:
      caption = '* ' + caption

    return caption

  def _on_select(self, idx):
    """
    On list item selection.
    """
    # If command list has items and one was selected (index equals zero or more).
    if self.command_list and idx > -1:
      # @todo: Disabled for now.
      # # Show latest updates in new window.
      # if 'Show update' == self.run_commands[idx][0]:
      #   # Undefine command list in order to "reset" the plugin (see run()).
      #   self.command_list = None
      #   # Open file with latest changes from change log.
      #   self.window.open_file(self.default_path + '/InThisVersion.txt', sublime.TRANSIENT)
      #   # Remove splash control file to indicate that no splash should be shown.
      #   os.remove(self.default_path + '/show_update_splash')

      # Add favourites to file.
      if not self.settings['regular_run_mode']:
        try:
          # Open a (new) favourites file.
          favourites = open(os.path.join(self.paths['user_data'], 'favourites.txt'), 'w')
          # Concatenate the complete command.
          command = self.run_commands[idx][1] + ',' + self.command_list[idx][1]          
          # Add command if not in favourites list.
          if not command in self.favourites:
            favourites.write(command + '\n')
          # Add all commands in favourites list except the selected one (will remove the command if already present).
          for saved_command in self.favourites:
            if saved_command != command:
              favourites.write(saved_command + '\n')
          # Close file.
          favourites.close()

          # Undefine command list in order to "reset" the plugin (see run()).
          self.command_list = None
          # Run QuickRef again.
          self.run()
        except Exception as e:
          sublime.status_message('QuickRef says: "_on_select() is misbehaving. Here\'s what happened: ' + str(e) + '"')

      # Do not run command if plugin is in hardcore mode (learn by not doing!).
      elif not self.settings['hardcore_mode']:
        # Run the command that corresponds with the selected item's caption.
        if not self.is_st2:
          # In ST3 it is necessary to explicitly call run_command() for TextCommand (ST2 can handle all types from ApplicationCommand).
          self.window.active_view().run_command(self.run_commands[idx][1], self.run_commands[idx][2])
        # Run command.
        self.window.run_command(self.run_commands[idx][1], self.run_commands[idx][2])
        # Undefine command list in order to "reset" the plugin (see run()).
        self.command_list = None
    else:
      # Undefine command list in order to "reset" the plugin (see run()).
      self.command_list = None

  def parse_json_file(self, file, clean_json = False):
    """
    Parses a JSON file and removes invalid patterns.
    """
    try:
      if clean_json:
        # Regular expression for comments.
        comment_re = re.compile(
          '(^)?[^\S\n]*/(?:\*(.*?)\*/[^\S\n]*|/[^\n]*)($)?',
          re.DOTALL | re.MULTILINE
        )

        with open(file, 'r') as f:
          content = ''.join(f.readlines())
          # Remove illegal commas (,) from last item in JSON arrays.
          content = re.sub(r',\n\s+]', '\n]', content)
          # @todo: Fix.
          # Colons (:) make json module raise an exception, so the whole problematic part is remowed.
          # Unfortunately this will also render all macros unable to run from QuickRef.
          content = re.sub(r'res://', '', content)
          # Look for comments.
          match = comment_re.search(content)
          while match:
            content = content[:match.start()] + content[match.end():]
            match = comment_re.search(content)

        json_object = json.loads(content)

      else:
        with open(file, 'r') as f:
          content = ''.join(f.readlines())
          json_object = json.loads(content)

      return json_object

    except (ValueError, Exception) as e:
      sublime.status_message('QuickRef says: "We have a JSON error. Here\'s what happened: ' + str(e) + '"')

  def get_paths(self):
    """
    Fetches important paths.
    """
    sublime_packages_path = sublime.packages_path()
    paths = {
      'user': os.path.join(sublime_packages_path, 'User'),
      'user_data': os.path.join(sublime_packages_path, 'User', 'QuickRefData')
    }

    return paths

  def get_settings(self):
    """
    Fetches settings.
    """
    # Get paths.
    paths = self.get_paths()
    # Make sure there is a data directory.
    if not os.path.isdir(paths['user_data']):
      os.makedirs(paths['user_data'])

    # Load settings file.
    settings_object = sublime.load_settings('QuickRef.sublime-settings')

    # Get settings and commands.
    settings = settings_object.get('settings')
    settings['commands'] = settings_object.get('commands')

    return settings

  def get_default_keymap(self):
    """
    Fetches default key bindings.
    """
    # Get paths.
    paths = self.get_paths()
    # Prepare settings filename.
    keymap_file = 'Default (' + self.platform + ').sublime-keymap'
    # Set data directory path.
    user_data_keymap = os.path.join(paths['user_data'], keymap_file)

    if self.is_st2:
      return os.path.join(sublime.packages_path(), 'Default', keymap_file)
    else:
      default_package = os.path.dirname(Default.__file__)
      
      # Check if there is a default keymap
      if not os.path.exists(user_data_keymap):
        # Extract and copy the default keymap to data directory.
        with zipfile.ZipFile(default_package, 'r') as zip:
          zip.extract(keymap_file, paths['user_data'])

      # Check if the default keymap in the data directory is outdated.
      if os.path.getmtime(default_package) > os.path.getmtime(user_data_keymap):
        # Extract and copy the default keymap to data directory.
        with zipfile.ZipFile(default_package, 'r') as zip:
          zip.extract(keymap_file, paths['user_data'])

      return user_data_keymap