# DO NOT EDIT!!! built with `python _building/build_setup.py`
import setuptools
setuptools.setup(
    name="k3zkutil",
    packages=["k3zkutil"],
    version="0.1.0",
    license='MIT',
    description='Some helper function to make life easier with zookeeper.',
    long_description='# k3zkutil\n\n[![Action-CI](https://github.com/pykit3/k3zkutil/actions/workflows/python-package.yml/badge.svg)](https://github.com/pykit3/k3zkutil/actions/workflows/python-package.yml)\n[![Build Status](https://travis-ci.com/pykit3/k3zkutil.svg?branch=master)](https://travis-ci.com/pykit3/k3zkutil)\n[![Documentation Status](https://readthedocs.org/projects/k3zkutil/badge/?version=stable)](https://k3zkutil.readthedocs.io/en/stable/?badge=stable)\n[![Package](https://img.shields.io/pypi/pyversions/k3zkutil)](https://pypi.org/project/k3zkutil)\n\nSome helper function to make life easier with zookeeper.\n\nk3zkutil is a component of [pykit3] project: a python3 toolkit set.\n\n\nSome helper function to make life easier with zookeeper.\n\n\n\n\n# Install\n\n```\npip install k3zkutil\n```\n\n# Synopsis\n\n```python\n\nfrom k3zkutil import config\n"""\nconfig.zk_acl      # ((\'xp\', \'123\', \'cdrwa\'), (\'foo\', \'bar\', \'rw\'))\nconfig.zk_auth     # (\'digest\', \'xp\', \'123\')\nconfig.zk_hosts    # \'127.0.0.1:2181\'\nconfig.zk_node_id  # \'web-01\'\nconfig.zk_lock_dir # \'lock/\'\n"""\nwith k3zkutil.ZKLock(\'foo_lock\',\n                   zkconf=dict(\n                       hosts=\'127.0.0.1:2181\',\n                       acl=((\'xp\', \'123\', \'cdrwa\'),),\n                       auth=(\'digest\', \'xp\', \'123\'),\n                       node_id=\'web-3\',\n                       lock_dir=\'my_locks/\'\n                   )):\n    print("do something")\nlock = k3zkutil.ZKLock(\'foo\')\ntry:\n    for holder, ver in lock.acquire_loop(timeout=3):\n        print(\'lock is currently held by:\', holder, ver)\n\n    print(\'lock is acquired\')\nexcept k3zkutil.LockTimeout as e:\n    print(\'timeout to acquire "foo"\')\n```\n\n#   Author\n\nZhang Yanpo (张炎泼) <drdr.xp@gmail.com>\n\n#   Copyright and License\n\nThe MIT License (MIT)\n\nCopyright (c) 2015 Zhang Yanpo (张炎泼) <drdr.xp@gmail.com>\n\n\n[pykit3]: https://github.com/pykit3',
    long_description_content_type="text/markdown",
    author='Zhang Yanpo',
    author_email='drdr.xp@gmail.com',
    url='https://github.com/pykit3/k3zkutil',
    keywords=['python', 'zookeeper'],
    python_requires='>=3.0',

    install_requires=['k3ut>=0.1.15,<0.2', 'k3utfjson>=0.1.1,<0.2', 'kazoo>=2.8.0', 'k3net>=0.1.0,<0.2', 'k3thread>=0.1.0,<0.2', 'k3txutil>=0.1.0,<0.2', 'k3utdocker>=0.1.0,<0.2', 'k3confloader>=0.1.1,<0.2'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
    ] + ['Programming Language :: Python :: 3'],
)
