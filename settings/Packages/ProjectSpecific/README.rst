Project-Specific
================

This extension enables you to add project specific configuration
to Sublime Text 2.

Example::

   {
       "folders": ...
       "settings": {
           "project-specific": {
               "sublime-keymap": [
                   {"keys": [ "ctrl+B"], 
                    "command": "exec", 
                    "args": ["echo", "my build"]
                   }
               ],
               "sublime-commands": [
                   {"caption": "My Command", 
                    "command": "open_file", 
                    "args": {"file": "my file.x"} }
               ]
               "sublime-macro": {
                   "macro1": [ ... ],
                   "macro2": [ ... ]
               }
           }
       }

   }

Each time you switch to a project, the configuration files in 
``User/Project-Specific`` will be updated.  For example above, there 
would be created:

* ``User/Project-Specific/Default.sublime-keymap``
* ``User/Project-Specific/<project-name>.sublime-commands``
* ``User/Project-Specific/<project-name> macro1.sublime-macro``
* ``User/Project-Specific/<project-name> macro2.sublime-macro``

Basically there will be created a file ``<project-name>.<key>`` for each 
key of *project-specific* dictionary, if value is a list.  If value is
a dictionary with subkey, then files ``<project-name> <subkey>.<key>`` 
will be created.

*sublime-keymap* configuration is an exception, because file-name 
must be ``Default``.  If you use here a subdictionary, your key can
contain (case-insensitive) *linux*, *osx*, *windows* for os-specific 
keymaps, any other key will be mapped to ``Default`` (if there are
multiple keys mapped to ``Default`` only the last processed is taken,
values are not merged!).

