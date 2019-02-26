Usage
=====

Installation:
*************
.. code-block:: console

   pip install https://github.com/ninpo/trio-inotify.git

Examples
********
   
Creating a single watch for all events on a path
------------------------------------------------
.. code-block:: python
   
   import trio
   from trio_inotify.inotify import WatchManager, Watcher, InotifyMasks

   wm = WatchManager()
   wm.add_watch("/path/to/file")
   watcher = Watcher(watch_manager=wm)
   events = trio.run(watcher.get_inotify_event)

Recursively watch a directory for file writes
---------------------------------------------
.. code-block:: python

   import trio
   from trio_inotify.inotify import WatchManager, Watcher, InotifyMasks

   wm = WatchManager()
   wm.add_watch("/path/to/directory", watch_mask=InotifyMasks.IN_CLOSE_WRITE, recursive=True)
   watcher = Watcher(watch_manager=wm)
   events = trio.run(watcher.get_inotify_event)

Because this is a recursive watch, in addition to IN_CLOSE_WRITE events, any events containing IS_DIR such as new directories being created or deleted will also be returned.
