import array
import fcntl
import os
import attr
import trio
from collections import namedtuple
from enum import Flag
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
class TrioInotify:
    _watches: dict = attr.ib(init=False, default={})
    _rev_watches: dict = attr.ib(init=False, default={})
    _inotify_fd: int = attr.ib(init=False, default=inotify_init())
    _inotify_event_flags: InotifyMasks = attr.ib(init=False, default=InotifyMasks)

    def _get_fd_buffer_length(self):
        buffer = array.array("I", [0])
        fcntl.ioctl(self._inotify_fd, ioctl_lib.FIONREAD, buffer)
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
                    self._inotify_event_flags(inotify_event.mask),
                    inotify_event.cookie,
                    file_name,
                )
            )
            i += event_struct_size + inotify_event.len
        return inotify_events

    def add_watch(self, path, watch_mask=None, recursive=False):
        if not watch_mask:
            watch_mask = self._inotify_event_flags.IN_ALL_EVENTS.value
        if not recursive:
            wd = inotify_add_watch(
                self._inotify_fd,
                path.encode("utf-8"),
                watch_mask
            )
        else:
            raise NotImplemented("Recursive watches aren't implemented....yet.")
        self._watches[wd] = path
        self._rev_watches[path] = wd

    def del_watch(self, path):
        watch_key = self._rev_watches[path]
        inotify_rm_watch(self._inotify_fd, watch_key)
        del self._watches[watch_key]
        del self._rev_watches[path]

    async def get_inotify_event(self):
        await trio.hazmat.checkpoint_if_cancelled()
        while True:
            try:
                new_inotify_event = os.read(
                    self._inotify_fd, self._get_fd_buffer_length()
                )
            except BlockingIOError:
                pass
            else:
                await trio.hazmat.cancel_shielded_checkpoint()
                return self._unpack_inotify_event(new_inotify_event)
            await trio.hazmat.wait_readable(self._inotify_fd)
