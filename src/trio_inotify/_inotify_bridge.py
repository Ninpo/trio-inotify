import errno
from os import strerror
from trio_inotify._inotify_c import ffi, lib


def handle_errors(ffi_error):
    if ffi_error in errno.errorcode.keys():
        raise OSError(strerror(ffi_error))
    else:
        raise Exception("Unknown error occurred")


def inotify_init():
    inotify_fd = lib.inotify_init1(lib.IN_NONBLOCK)

    if inotify_fd < 0:
        handle_errors(ffi.errno)

    return inotify_fd


def inotify_add_watch(inotify_fd, path, watch_mask):
    watch_descriptor = lib.inotify_add_watch(inotify_fd, path, watch_mask)

    if watch_descriptor < 0:
        handle_errors(ffi.errno)

    return watch_descriptor


def inotify_rm_watch(inotify_fd, watch_descriptor):
    rm_result = lib.inotify_rm_watch(inotify_fd, watch_descriptor)

    if rm_result < 0:
        handle_errors(ffi.errno)
