Introduction
============

``trio_inotify`` is a library intended to be used in applications that make use of the `Trio <https://github.com/python-trio/>`_ asynchronous I/O library.

Primary Goal
************

It is the aim of this library to provide flexible and dynamic interactions with the inotify interface.

Current Features
****************

- Watch for changes on a single file or directory path with optional event filtering.  Events can be retrieved with :py:meth:`Watcher.get_inotify_event`.
- Watch for changes recursively on a directory with optional event filtering.  Creates a watch list for all current subdirectories of a given directory with :py:meth:`WatchManager.add_watch`.

Upcoming Features
*****************

- Ability to provide a user defined event handler to :py:class:`Watcher`.
- Automatically grow and shrink recursive watches as directories are created/deleted.
- Ensure race conditions such as multiple subdirectory trees being created between inotify event and new watch creation are accounted for.
