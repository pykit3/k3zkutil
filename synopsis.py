import k3zkutil

"""
config.zk_acl      # (('xp', '123', 'cdrwa'), ('foo', 'bar', 'rw'))
config.zk_auth     # ('digest', 'xp', '123')
config.zk_hosts    # '127.0.0.1:2181'
config.zk_node_id  # 'web-01'
config.zk_lock_dir # 'lock/'
"""
with k3zkutil.ZKLock(
    "foo_lock",
    zkconf=dict(
        hosts="127.0.0.1:2181",
        acl=(("xp", "123", "cdrwa"),),
        auth=("digest", "xp", "123"),
        node_id="web-3",
        lock_dir="my_locks/",
    ),
):
    print("do something")
lock = k3zkutil.ZKLock("foo")
try:
    for holder, ver in lock.acquire_loop(timeout=3):
        print("lock is currently held by:", holder, ver)

    print("lock is acquired")
except k3zkutil.LockTimeout:
    print('timeout to acquire "foo"')
