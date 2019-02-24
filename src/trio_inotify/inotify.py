import array
import fcntl
import os
import attr
import trio
from collections import namedtuple
from enum import Flag
from pathlib import Path
from trio_inotify._inotify_bridge import (
    ffi as inotify_ffi,
    lib as inotify_lib,
    inotify_init,
    inotify_add_watch,
    inotify_rm_watch,
)
from trio_inotify._ioctl_c import lib as ioctl_lib

InotifyMasks = Flag(
    "InotifyMasks",
    [
        (mask_name, getattr(inotify_lib, mask_name))
        for mask_name in dir(inotify_lib)
        if mask_name.startswith("IN_")
    ],
)


@attr.s(auto_attribs=True)
class WatchManager:
    _watches: dict = attr.ib(init=False, default={})
    _rev_watches: dict = attr.ib(init=False, default={})
    recursive: bool = attr.ib(init=False, default=False)
    inotify_fd: int = attr.ib(init=False, default=inotify_init())
    inotify_event_flags: InotifyMasks = attr.ib(init=False, default=InotifyMasks)

    def _add_watch_keys(self, wd, path):
        self._watches[path] = wd
        self._rev_watches[wd] = path

    def _del_watch_keys(self, path):
        watch_key = self._watches[path]
        del self._watches[path]
        del self._rev_watches[watch_key]

    def add_watch(self, path, event_mask=None, recursive=False):
        if not event_mask:
            event_mask = self.inotify_event_flags.IN_ALL_EVENTS
        wd = inotify_add_watch(self.inotify_fd, path.encode("utf-8"), event_mask.value)
        self._add_watch_keys(wd, path)
        if recursive:
            self.recursive = True
            event_mask = (
                event_mask
                | self.inotify_event_flags.IN_ISDIR
                | self.inotify_event_flags.IN_CREATE
                | self.inotify_event_flags.IN_DELETE
            )
            for root, dirs, _ in os.walk(path):
                for directory in dirs:
                    full_path_str = Path(root, directory).absolute().as_posix()
                    wd = inotify_add_watch(
                        self.inotify_fd, full_path_str.encode("utf-8"), event_mask.value
                    )
                    self._add_watch_keys(wd, full_path_str)

    def del_watch(self, path):
        watch_key = self._watches[path]
        inotify_rm_watch(self.inotify_fd, watch_key)
        self._del_watch_keys(path)
        if self.recursive:
            for root, dirs, _ in os.walk(path):
                for directory in dirs:
                    full_path_str = Path(root, directory).absolute().as_posix()
                    wd = self._watches[full_path_str]
                    inotify_rm_watch(self.inotify_fd, wd)
                    self._del_watch_keys(full_path_str)


@attr.s(auto_attribs=True)
class Watcher:
    watch_manager: WatchManager = attr.ib()
    event_handler: callable = attr.ib(default=None)

    def _get_fd_buffer_length(self):
        buffer = array.array("I", [0])
        fcntl.ioctl(self.watch_manager.inotify_fd, ioctl_lib.FIONREAD, buffer)
        return buffer[0]

    def _unpack_inotify_event(self, new_inotify_event):
        InotifyEvent = namedtuple("InotifyEvent", "wd mask cookie file_name")
        inotify_events = []
        event_struct_size = inotify_ffi.sizeof("struct inotify_event")
        string_buffer = inotify_ffi.new("char[]", len(new_inotify_event))
        string_buffer[0 : len(new_inotify_event)] = new_inotify_event
        i = 0
        while i < len(string_buffer):
            inotify_event = inotify_ffi.cast(
                "struct inotify_event *", string_buffer[i : i + event_struct_size]
            )
            file_name_start = i + event_struct_size
            file_name_end = file_name_start + inotify_event.len
            file_name = inotify_ffi.string(string_buffer[file_name_start:file_name_end])
            inotify_events.append(
                InotifyEvent(
                    inotify_event.wd,
                    self.watch_manager.inotify_event_flags(inotify_event.mask),
                    inotify_event.cookie,
                    file_name,
                )
            )
            i += event_struct_size + inotify_event.len
        return inotify_events

    async def get_inotify_event(self):
        await trio.hazmat.checkpoint_if_cancelled()
        while True:
            try:
                new_inotify_event = os.read(
                    self.watch_manager.inotify_fd, self._get_fd_buffer_length()
                )
            except BlockingIOError:
                pass
            else:
                await trio.hazmat.cancel_shielded_checkpoint()
                return self._unpack_inotify_event(new_inotify_event)
            await trio.hazmat.wait_readable(self.watch_manager.inotify_fd)
