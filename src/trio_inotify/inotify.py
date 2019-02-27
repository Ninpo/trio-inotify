"""Tools to interact with the inotify interface
"""
import array
import fcntl
import os
import attr
import trio
from enum import Flag
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Type
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
    """Add, remove and track watches on an inotify interface.
    """

    _watches: Dict[str, int] = attr.ib(init=False, default={})
    _rev_watches: Dict[int, str] = attr.ib(init=False, default={})
    recursive: bool = attr.ib(init=False, default=False)
    inotify_fd: int = attr.ib(init=False, default=inotify_init())
    inotify_event_flags: Type[InotifyMasks] = attr.ib(init=False, default=InotifyMasks)

    def _add_watch_keys(self, wd: int, path: str) -> None:
        """Add new watch to internal lookup dictionaries.

        :param int wd: Watch descriptor
        :param str path: File/directory being watched
        :return: None
        """
        self._watches[path] = wd
        self._rev_watches[wd] = path

    def _del_watch_keys(self, path: str):
        """Remove watches from internal lookup dictionaries.

        :param str path: File/directory no longer being watched.
        :return: None
        """
        watch_key: int = self._watches[path]
        del self._watches[path]
        del self._rev_watches[watch_key]

    def add_watch(
        self, path: str, event_mask: InotifyMasks = None, recursive: bool = False
    ) -> None:
        """Add new watch to inotify interface and track.

        :param str path: File/directory to watch.
        :param InotifyMasks event_mask: inotify events to watch for.
        :param bool recursive: Include subdirectories/newly created directories.
        :return: None
        """
        if not event_mask:
            event_mask = self.inotify_event_flags.IN_ALL_EVENTS
        wd: int = inotify_add_watch(
            self.inotify_fd, path.encode("utf-8"), event_mask.value
        )
        self._add_watch_keys(wd, path)
        if recursive:
            self.recursive: bool = True
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

    def del_watch(self, path: str) -> None:
        """Remove a watch.  Removes recursively if removing a recursive watch member.

        :param str path: File/directory to stop watching.
        :return: None
        """
        watch_key: int = self._watches[path]
        inotify_rm_watch(self.inotify_fd, watch_key)
        self._del_watch_keys(path)
        if self.recursive:
            for root, dirs, _ in os.walk(path):
                for directory in dirs:
                    full_path: str = Path(root, directory).absolute().as_posix()
                    wd: int = self._watches[full_path]
                    inotify_rm_watch(self.inotify_fd, wd)
                    self._del_watch_keys(full_path)


@attr.s(auto_attribs=True)
class InotifyEvent:
    """Unpacked inotify event bytes.

    :ivar int wd: Watch file descriptor.
    :ivar InotifyMasks mask: Inotify event mask.
    :ivar int cookie: Inotify event cookie if applicable.
    :ivar bytes file_name: File path associated with event.
    """

    wd: int = attr.ib()
    mask: InotifyMasks = attr.ib()
    cookie: int = attr.ib()
    file_name: bytes = attr.ib()


@attr.s(auto_attribs=True)
class Watcher:
    """Watch for inotify events on established watches.  Optionally pass events to an event handler.
    """

    watch_manager: WatchManager = attr.ib()
    event_handler: Callable = attr.ib(default=None)

    def _get_fd_buffer_length(self) -> int:
        """Check length of inotify file descriptor.

        :return int: Length in bytes of the inotify file descriptor.
        """
        buffer = array.array("I", [0])
        fcntl.ioctl(self.watch_manager.inotify_fd, ioctl_lib.FIONREAD, buffer)
        return buffer[0]

    def _unpack_inotify_event(self, new_inotify_event) -> List[InotifyEvent]:
        """Unpack bytes from inotify file descriptor.

        :param bytes new_inotify_event:
        :return list inotify_events:
        """

        inotify_events: List[InotifyEvent] = []
        event_struct_size: int = inotify_ffi.sizeof("struct inotify_event")
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

    async def get_inotify_event(self) -> List[InotifyEvent]:
        """Read bytes from inotify descriptor if available.

        :return list: One or more ``NamedTuple`` objects containing event data.
        """
        await trio.hazmat.checkpoint_if_cancelled()
        while True:
            try:
                new_inotify_event: bytes = os.read(
                    self.watch_manager.inotify_fd, self._get_fd_buffer_length()
                )
            except BlockingIOError:
                pass
            else:
                await trio.hazmat.cancel_shielded_checkpoint()
                return self._unpack_inotify_event(new_inotify_event)
            await trio.hazmat.wait_readable(self.watch_manager.inotify_fd)
