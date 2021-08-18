.. k3zkutil documentation master file, created by
   sphinx-quickstart on Thu May 14 16:58:55 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

k3zkutil
============

.. automodule:: k3zkutil

Documentation for the Code
**************************

Exceptions
----------

.. autoexception::  PermTypeError

.. autoexception::  ZKWaitTimeout

.. autoexception::  LockTimeout

.. autoexception::  ZkPathError


Classes
----------

.. autoclass::  KazooClientExt

.. autoclass::  ZKConf

.. autoclass::  ZKLock

.. autoclass::  CachedReader


Functions
---------

.. autofunction::  cas_loop

.. autofunction::  kazoo_client_ext

.. autofunction::  close_zk

.. autofunction::  init_hierarchy

.. autofunction::  export_hierarchy

.. autofunction::  is_backward_locking

.. autofunction::  lock_id

.. autofunction::  make_acl_entry

.. autofunction::  make_digest

.. autofunction::  make_kazoo_digest_acl

.. autofunction::  parse_kazoo_acl

.. autofunction::  parse_lock_id

.. autofunction::  perm_to_long

.. autofunction::  perm_to_short

.. autofunction::  get_next

.. autofunction::  make_identifier

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`