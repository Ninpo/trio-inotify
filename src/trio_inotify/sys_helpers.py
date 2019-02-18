import array
import fcntl
from trio_inotify._ioctl_c import ffi, lib


def get_fd_buffer_length(inotify_fd):
    buffer = array.array("I", [0])
    fcntl.ioctl(inotify_fd, lib.FIONREAD, buffer)
    return buffer[0]
