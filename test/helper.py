"""Shared test utilities for k3zkutil tests."""

import time
import unittest

import k3utdocker
from kazoo.client import KazooClient
from kazoo.handlers.threading import KazooTimeoutError


def wait_for_zk(hosts, timeout=60):
    """Wait for zookeeper to be ready, retrying until timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        zk = KazooClient(hosts=hosts)
        try:
            zk.start(timeout=5)
            return zk
        except KazooTimeoutError:
            zk.stop()
            zk.close()
            time.sleep(1)
    raise KazooTimeoutError(f"Zookeeper not ready after {timeout}s")


def skip_without_docker():
    """Skip the calling test class when the Docker daemon cannot be reached.

    The probe uses the client that `k3utdocker` gives the tests, so it sees
    the daemon the tests would use.
    """
    try:
        k3utdocker.get_client().ping()
    except Exception as e:
        # Any failure here means the tests would fail in setup, for a reason
        # that has nothing to do with k3zkutil.
        raise unittest.SkipTest(f"Docker daemon is not available: {e!r}") from e
