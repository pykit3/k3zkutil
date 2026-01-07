"""
Some helper function to make life easier with zookeeper.

"""

from importlib.metadata import version

__version__ = version("k3zkutil")

from .exceptions import (
    ZKWaitTimeout,
)

from .zkacid import (
    cas_loop,
)

from .zkconf import (
    KazooClientExt,
    ZKConf,
    kazoo_client_ext,
)

from .zkutil import (
    PermTypeError,
    ZkPathError,
    close_zk,
    init_hierarchy,
    export_hierarchy,
    is_backward_locking,
    lock_id,
    make_acl_entry,
    make_digest,
    make_kazoo_digest_acl,
    parse_kazoo_acl,
    parse_lock_id,
    perm_to_long,
    perm_to_short,
    wait_absent,
    get_next,
)

from .zklock import (
    ZKLock,
    LockTimeout,
    make_identifier,
)

from .cached_reader import (
    CachedReader,
)

__all__ = [
    "PermTypeError",
    "ZKWaitTimeout",
    "ZkPathError",
    "cas_loop",
    "KazooClientExt",
    "ZKConf",
    "kazoo_client_ext",
    "close_zk",
    "init_hierarchy",
    "export_hierarchy",
    "is_backward_locking",
    "lock_id",
    "make_acl_entry",
    "make_digest",
    "make_kazoo_digest_acl",
    "parse_kazoo_acl",
    "parse_lock_id",
    "perm_to_long",
    "perm_to_short",
    "wait_absent",
    "get_next",
    "ZKLock",
    "LockTimeout",
    "CachedReader",
    "make_identifier",
]
