# trio-inotify
Inotify interface implemented in Trio

## Note: This is a PRE-ALPHA project
API is currently subject to change with each release.

## Installation
```
pip install git+https://github.com/ninpo/trio-inotify
```

## Usage:

### Simple File Watch for Deletes:
```python
import trio
from trio_inotify.inotify import WatchManager, Watcher, InotifyMasks
wm = WatchManager()
wm.add_watch("/path/to/file/or/dir", watch_mask=InotifyMasks.IN_DELETE)
watcher = Watcher(watch_manager=wm)
events = trio.run(watcher.get_inotify_event)
```
This will block until there are inotify events, at which point you'll be returned a list of events.
```python
wm.del_watch("/path/to/file/or/dir")
```
Deletes a watch.
### Recursive Directory Watch for File Write Events:
```python
import trio
from trio_inotify.inotify import WatchManager, Watcher, InotifyMasks
wm = WatchManager()
wm.add_watch("/path/to/dir", watch_mask=InotifyMasks.IN_CLOSE_WRITE, recursive=True)
watcher = Watcher(watch_manager=wm)
events = trio.run(watcher.get_inotify_event)

```
`del_watch()` on a recursive watch will remove _all_ watches including from any watched sub-dirs.
You can also selectively drop sub-dir watches from a recursive watch while keeping watches for other dirs:
#### Scenario: Watching /home/user/logs
```python
wm.add_watch("/home/user/logs", watch_mask=InotifyMasks.IN_CLOSE_WRITE, recursive=True)
# Watches /home/user/logs, /home/user/logs/subdir1, /home/user/logs/subdir2 etc..
wm.del_watch("/home/user/logs/subdir2")
# Stops watching /home/user/logs/subdir2 and all child 
# directories/files, but still watches /home/user/logs and /home/user/logs/subdir1

```

## Coming Soon:
- Automatic addition/removal of directory watches when recursively watching a directory on `IS_DIR|IN_CREATE`/`IS_DIR|IN_DELETE` events
- Pass a custom event handler to Watcher
