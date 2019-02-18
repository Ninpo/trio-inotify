from cffi import FFI

ffi = FFI()
ffi.cdef("""
#define FIONREAD ...
""")

ffi.set_source("trio_inotify._ioctl_c", """
#include <sys/ioctl.h>
""", libraries=[])

if __name__ == "__main__":
    ffi.compile()
