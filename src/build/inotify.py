from cffi import FFI

ffi = FFI()
ffi.cdef("""
/*
 * struct inotify_event - structure read from the inotify device for each event
 *
 * When you are watching a directory, you will receive the filename for events
 * such as IN_CREATE, IN_DELETE, IN_OPEN, IN_CLOSE, ..., relative to the wd.
 */
struct inotify_event {
        int           wd;
        uint32_t      mask;
        uint32_t      cookie;
        uint32_t      len;
//        char          name[0]; # we calculate this manually in str_to_event
};

/* the following are legal, implemented events that user-space can watch for */
#define IN_ACCESS        ...  /* File was accessed */
#define IN_MODIFY        ...  /* File was modified */
#define IN_ATTRIB        ...  /* Metadata changed */
#define IN_CLOSE_WRITE   ...  /* Writable file was closed */
#define IN_CLOSE_NOWRITE ...  /* Unwritable file closed */
#define IN_OPEN          ...  /* File was opened */
#define IN_MOVED_FROM    ...  /* File was moved from X */
#define IN_MOVED_TO      ...  /* File was moved to Y */
#define IN_CREATE        ...  /* Subfile was created */
#define IN_DELETE        ...  /* Subfile was deleted */
#define IN_DELETE_SELF   ...  /* Self was deleted */
#define IN_MOVE_SELF     ...  /* Self was moved */

/* the following are legal events.  they are sent as needed to any watch */
#define IN_UNMOUNT       ...  /* Backing fs was unmounted */
#define IN_Q_OVERFLOW    ...  /* Event queued overflowed */
#define IN_IGNORED       ...  /* File was ignored */

/* helper events */
#define IN_CLOSE         ...  /* close */
#define IN_MOVE          ...  /* moves */

/* special flags */
#define IN_ONLYDIR       ...  /* only watch the path if it is a directory */
#define IN_DONT_FOLLOW   ...  /* don't follow a sym link */
#define IN_EXCL_UNLINK   ...  /* exclude events on unlinked objects */
#define IN_MASK_ADD      ...  /* add to the mask of an already existing watch */
#define IN_ISDIR         ...  /* event occurred against dir */
#define IN_ONESHOT       ...  /* only send event once */

/*
 * All of the events - we build the list by hand so that we can add flags in
 * the future and not break backward compatibility.  Apps will get only the
 * events that they originally wanted.  Be sure to add new events here!
 */
#define IN_ALL_EVENTS  ...

/* Flags for sys_inotify_init1.  */
#define IN_CLOEXEC  ...
#define IN_NONBLOCK ...

int inotify_init(void);
int inotify_init1(int flags);
int inotify_add_watch(int fd, const char *pathname, uint32_t mask);
int inotify_rm_watch(int fd, int wd);
""")

ffi.set_source("trio_inotify._inotify_c", """
#include <sys/inotify.h>
#include <sys/ioctl.h>
""", libraries=[])

if __name__ == "__main__":
    ffi.compile()
