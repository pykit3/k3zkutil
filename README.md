# k3zkutil

[![Action-CI](https://github.com/pykit3/k3zkutil/actions/workflows/python-package.yml/badge.svg)](https://github.com/pykit3/k3zkutil/actions/workflows/python-package.yml)
[![Build Status](https://travis-ci.com/pykit3/k3zkutil.svg?branch=master)](https://travis-ci.com/pykit3/k3zkutil)
[![Documentation Status](https://readthedocs.org/projects/k3zkutil/badge/?version=stable)](https://k3zkutil.readthedocs.io/en/stable/?badge=stable)
[![Package](https://img.shields.io/pypi/pyversions/k3zkutil)](https://pypi.org/project/k3zkutil)

Some helper function to make life easier with zookeeper.

k3zkutil is a component of [pykit3] project: a python3 toolkit set.


Some helper function to make life easier with zookeeper.




# Install

```
pip install k3zkutil
```

# Synopsis

```python

from k3zkutil import config
"""
config.zk_acl      # (('xp', '123', 'cdrwa'), ('foo', 'bar', 'rw'))
config.zk_auth     # ('digest', 'xp', '123')
config.zk_hosts    # '127.0.0.1:2181'
config.zk_node_id  # 'web-01'
config.zk_lock_dir # 'lock/'
"""
with k3zkutil.ZKLock('foo_lock',
                   zkconf=dict(
                       hosts='127.0.0.1:2181',
                       acl=(('xp', '123', 'cdrwa'),),
                       auth=('digest', 'xp', '123'),
                       node_id='web-3',
                       lock_dir='my_locks/'
                   )):
    print("do something")
lock = k3zkutil.ZKLock('foo')
try:
    for holder, ver in lock.acquire_loop(timeout=3):
        print('lock is currently held by:', holder, ver)

    print('lock is acquired')
except k3zkutil.LockTimeout as e:
    print('timeout to acquire "foo"')
```

#   Author

Zhang Yanpo (张炎泼) <drdr.xp@gmail.com>

#   Copyright and License

The MIT License (MIT)

Copyright (c) 2015 Zhang Yanpo (张炎泼) <drdr.xp@gmail.com>


[pykit3]: https://github.com/pykit3