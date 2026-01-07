import logging

from kazoo.exceptions import BadVersionError

import k3txutil

from .zkconf import kazoo_client_ext
from . import zkutil

logger = logging.getLogger(__name__)


def cas_loop(zkclient, path, json=True):
    # while True:
    #     curr_val, zstat = zkclient.get(path)
    # new_val = curr_val + ':foo'
    # try:
    #     zkclient.set(path, new_val, version=zstat.version)
    # except BadVersionError as e:
    #     continue
    # else:
    #     return
    """
    A helper generator for doing CAS(check and set or compare and swap) on zk.
    See [CAS](https://en.wikipedia.org/wiki/Compare-and-swap)

    A general CAS loop is like following(check the version when update):
    :param zkclient: is a `KazooClient` instance connected to zk.
    It can also be a string, in which case it is treated as a comma separated
    hosts list, and a `zkclient` is created with default setting.
    It can also be a `dict` or an instance of `ZKConf`, in which case it create
    a `zkclient` with `ZKConf` defined setting.
    :param path: is the zk-node path to get and set.
    :param json: whether to do a json load after reading the value from zk and to do a json dump
    before updating the value to zk.
    :return: a generator yields a `tuple` of 2 element:
    """
    zkclient, owning_zk = kazoo_client_ext(zkclient, json=json)

    def setter(path, val, zstat):
        zkclient.set(path, val, version=zstat.version)

    try:
        for curr in k3txutil.cas_loop(zkclient.get, setter, args=(path,), conflicterror=BadVersionError):
            yield curr
    finally:
        if owning_zk:
            zkutil.close_zk(zkclient)
