# k3zkutil

[![Action-CI](https://github.com/pykit3/k3zkutil/actions/workflows/python-package.yml/badge.svg)](https://github.com/pykit3/k3zkutil/actions/workflows/python-package.yml)
[![Documentation Status](https://readthedocs.org/projects/k3zkutil/badge/?version=stable)](https://k3zkutil.readthedocs.io/en/stable/?badge=stable)
[![Package](https://img.shields.io/pypi/pyversions/k3zkutil)](https://pypi.org/project/k3zkutil)

Helper functions for ZooKeeper with kazoo. Provides distributed locking, configuration management, ACL utilities, and CAS operations.

k3zkutil is a component of [pykit3](https://github.com/pykit3) project: a python3 toolkit set.

## Installation

```bash
pip install k3zkutil
```

## Quick Start

```python
import k3zkutil

# Create a distributed lock
with k3zkutil.ZKLock('my_lock', zk_client):
    # Do something with exclusive access
    pass
```

## API Reference

::: k3zkutil

## License

The MIT License (MIT) - Copyright (c) 2015 Zhang Yanpo (张炎泼)
