import time
import unittest

from kazoo.client import KazooClient
from kazoo.handlers.threading import KazooTimeoutError

import k3thread
import k3utdocker
import k3ut
import k3zkutil

dd = k3ut.dd

zk_tag = "zookeeper:3.9"
zk_name = "zk_test"


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


class TestAcid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        k3utdocker.pull_image(zk_tag)

    def setUp(self):
        k3utdocker.create_network()
        k3utdocker.start_container(
            zk_name,
            zk_tag,
            port_bindings={2181: 21811},
        )

        self.zk = wait_for_zk("127.0.0.1:21811")

        dd("start zk-test in docker")

        self.path = "a"
        self.zk.create(self.path, b"1")

    def tearDown(self):
        self.zk.stop()
        k3utdocker.remove_container(zk_name)

    def test_cas(self):
        for curr in k3zkutil.cas_loop(self.zk, self.path):
            curr.v += 2

        final_val, zstat = self.zk.get(self.path)
        dd(final_val, zstat)
        self.assertEqual(b"3", final_val)

    def test_cas_abort(self):
        for curr in k3zkutil.cas_loop(self.zk, self.path):
            curr.v += 2
            break

        final_val, zstat = self.zk.get(self.path)
        dd(final_val, zstat)
        self.assertEqual(b"1", final_val, "a break statement cancel set_val()")

    def test_cas_create_zk(self):
        for first_arg in (
            "127.0.0.1:21811",
            {"hosts": "127.0.0.1:21811"},
            k3zkutil.ZKConf(hosts="127.0.0.1:21811"),
        ):
            self.zk.set(self.path, b"1")

            for curr in k3zkutil.cas_loop(first_arg, self.path):
                curr.v += 2

            final_val, zstat = self.zk.get(self.path)
            dd(final_val, zstat)
            self.assertEqual(b"3", final_val)

    def test_cas_non_json(self):
        for curr in k3zkutil.cas_loop(self.zk, self.path, json=False):
            self.assertIsInstance(curr.v, bytes)
            curr.v += b"a"

        final_val, zstat = self.zk.get(self.path)
        dd(final_val, zstat)
        self.assertEqual(b"1a", final_val)

    def test_cas_concurrent(self):
        def _update():
            for ii in range(10):
                for curr in k3zkutil.cas_loop("127.0.0.1:21811", self.path):
                    curr.v += 1

        ths = [k3thread.daemon(_update) for _ in range(5)]

        for th in ths:
            th.join()

        final_val, zstat = self.zk.get(self.path)
        dd(final_val, zstat)

        self.assertEqual(b"51", final_val)
