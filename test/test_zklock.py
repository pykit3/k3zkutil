import time
import unittest

from kazoo.client import KazooClient
from kazoo.exceptions import ConnectionClosedError
from kazoo.handlers.threading import KazooTimeoutError

import k3thread
import k3ut
import k3utdocker
import k3utfjson
import k3zkutil
from k3confloader import conf

dd = k3ut.dd

zk_test_name = "zk_test"
zk_test_tag = "zookeeper:3.9"


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


zk_test_auth = ("digest", "xp", "123")
zk_test_acl = (("xp", "123", "cdrw"),)

# zookeeper docker env vars:
# https://hub.docker.com/_/zookeeper/
#
# Example stack.yml for zookeeper:
#
# version: '3.1'
# services:
#   zoo1:
#     image: zookeeper
#     restart: always
#     hostname: zoo1
#     ports:
#       - 2181:2181
#     environment:
#       ZOO_MY_ID: 1
#       ZOO_SERVERS: server.1=0.0.0.0:2888:3888 server.2=zoo2:2888:3888 server.3=zoo3:2888:3888
#   zoo2: ...
#   zoo3: ...
#
# ZOO_TICK_TIME          : Defaults to 2000. ZooKeeper's tickTime
# ZOO_INIT_LIMIT         : Defaults to 5. ZooKeeper's initLimit
# ZOO_SYNC_LIMIT         : Defaults to 2. ZooKeeper's syncLimit
# ZOO_MAX_CLIENT_CNXNS   : Defaults to 60. ZooKeeper's maxClientCnxns
# ZOO_STANDALONE_ENABLED : Defaults to false. Zookeeper's standaloneEnabled
# ZOO_MY_ID
# ZOO_SERVERS
#
# Where to store data
#       This image is configured with volumes at /data and /datalog to hold the Zookeeper in-memory database snapshots and the transaction log of updates to the database, respectively.


class TestZKLock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        k3utdocker.pull_image(zk_test_tag)

    def setUp(self):
        conf.zk_acl = zk_test_acl
        conf.zk_auth = zk_test_auth

        self.counter = 0
        self.running = True

        k3utdocker.create_network()
        k3utdocker.start_container(
            zk_test_name,
            zk_test_tag,
            port_bindings={
                2181: 21811,
            },
        )

        self.zk = wait_for_zk("127.0.0.1:21811")
        scheme, name, passw = zk_test_auth
        self.zk.add_auth(scheme, name + ":" + passw)

        # create lock base dir
        acl = k3zkutil.make_kazoo_digest_acl(zk_test_acl)
        self.zk.create("lock/", acl=acl)

        self.lck = k3zkutil.ZKLock("foo_name", zkclient=self.zk)

    def tearDown(self):
        self.zk.stop()
        k3utdocker.remove_container(zk_test_name)

    def _on_conn_change(self, state):
        self.lsn_count += 1

    def test_bounded_listener(self):
        # ensure that adding a bounded listener(self.on_xxx) is ok

        self.lsn_count = 0

        self.zk.add_listener(self._on_conn_change)
        self.zk.add_listener(self._on_conn_change)

        self.zk.stop()

        self.assertEqual(1, self.lsn_count)

    def _loop_acquire(self, n, ident):
        zk = KazooClient(hosts="127.0.0.1:21811")
        zk.start()
        scheme, name, passw = zk_test_auth
        zk.add_auth(scheme, name + ":" + passw)

        for ii in range(n):
            lock = k3zkutil.ZKLock("foo_name", zkclient=zk)
            with lock:
                self.total += 1
                self.counter += 1

                self.assertTrue(self.counter == 1)

                time.sleep(0.01)
                self.counter -= 1

                dd(
                    "id={ident:0>2} n={ii:0>2} got and released lock: {holder}".format(
                        ident=ident, ii=ii, holder=lock.lock_holder
                    )
                )

        zk.stop()

    def test_concurrent(self):
        self.running = True
        self.total = 0
        n_repeat = 40
        n_thread = 5

        ths = []
        for ii in range(n_thread):
            t = k3thread.daemon(
                self._loop_acquire,
                args=(
                    n_repeat,
                    ii,
                ),
            )
            ths.append(t)

        for th in ths:
            th.join()

        self.running = False
        self.assertEqual(n_repeat * n_thread, self.total)

    def test_persistent(self):
        lock = k3zkutil.ZKLock("foo_name", ephemeral=False, on_lost=lambda: True)
        try:
            with lock:
                lock.zkclient.stop()
        except ConnectionClosedError:
            pass

        self.assertRaises(k3zkutil.LockTimeout, self.lck.acquire, timeout=0.2)

    def test_timeout(self):
        l1 = k3zkutil.ZKLock("foo_name", on_lost=lambda: True)
        l2 = k3zkutil.ZKLock("foo_name", on_lost=lambda: True)

        with l1:
            with k3ut.Timer() as t:
                self.assertRaises(k3zkutil.LockTimeout, l2.acquire, timeout=0.2)
                self.assertAlmostEqual(0.2, t.spent(), places=1)

            with k3ut.Timer() as t:
                self.assertRaises(k3zkutil.LockTimeout, l2.acquire, timeout=-1)
                self.assertAlmostEqual(0.0, t.spent(), delta=0.01)

        try:
            l2.acquire(timeout=-1)
        except k3zkutil.LockTimeout:
            self.fail("timeout<0 should could acquire")

    def test_lock_holder(self):
        a = k3zkutil.ZKLock("foo_name", on_lost=lambda: True)
        b = k3zkutil.ZKLock("foo_name", on_lost=lambda: True)

        with a:
            self.assertIsInstance(a.identifier, dict)
            self.assertIsNone(a.identifier["val"], None)

            self.assertEqual((a.identifier, 0), a.lock_holder)
            val, zstate = self.zk.get(a.lock_path)
            val = k3utfjson.load(val)

            self.assertEqual((val, zstate.version), a.lock_holder)

            locked, holder, ver = b.try_acquire()
            self.assertFalse(locked)
            self.assertEqual((a.identifier, 0), (holder, ver))
            self.assertEqual((val, zstate.version), (holder, ver))

    def test_watch_acquire(self):
        a = k3zkutil.ZKLock("foo", on_lost=lambda: True)
        b = k3zkutil.ZKLock("foo", on_lost=lambda: True)

        # no one locked

        n = 0
        for holder, ver in a.acquire_loop():
            n += 1
        self.assertEqual(0, n, "acquired directly")

        # watch node change

        it = b.acquire_loop()

        holder, ver = next(it)
        self.assertEqual((a.identifier, 0), (holder, ver))

        a.identifier["val"] = "xx"
        value = k3utfjson.dump(a.identifier).encode("utf-8")
        self.zk.set(a.lock_path, value)

        holder, ver = next(it)
        self.assertEqual(("xx", 1), (holder["val"], ver), "watched node change")

        a.release()
        try:
            holder, ver = next(it)
            self.fail("should not have next yield")
        except StopIteration:
            pass

        self.assertTrue(b.is_locked())

    def test_set_locked_key(self):
        l1 = k3zkutil.ZKLock("foo_name", on_lost=lambda: True)

        with l1:
            val, zstate = self.zk.get(l1.lock_path)
            val = k3utfjson.load(val)
            self.assertEqual(val, l1.identifier)
            self.assertEqual((val, zstate.version), l1.lock_holder)

            self.assertIsInstance(val, dict)
            self.assertIsNone(val["val"], None)

            l1.set_lock_val("foo_val", zstate.version)

            val, zstate = self.zk.get(l1.lock_path)
            val = k3utfjson.load(val)
            self.assertEqual(val, l1.identifier)

            self.assertIsInstance(val, dict)
            self.assertEqual(val["val"], "foo_val")

    def test_try_lock(self):
        l1 = k3zkutil.ZKLock("foo_name", on_lost=lambda: True)
        l2 = k3zkutil.ZKLock("foo_name", on_lost=lambda: True)

        with l1:
            with k3ut.Timer() as t:
                locked, holder, ver = l2.try_acquire()
                self.assertFalse(locked)
                self.assertEqual(l1.identifier, holder)
                self.assertGreaterEqual(ver, 0)

                self.assertAlmostEqual(0.0, t.spent(), delta=0.05)

        with k3ut.Timer() as t:
            locked, holder, ver = l2.try_acquire()
            self.assertTrue(locked)
            self.assertEqual(l2.identifier, holder)
            self.assertEqual(ver, 0)

            self.assertAlmostEqual(0.0, t.spent(), delta=0.05)

    def test_try_release(self):
        l1 = k3zkutil.ZKLock("foo_name", on_lost=lambda: True)
        l2 = k3zkutil.ZKLock("foo_name", on_lost=lambda: True)

        released, holder, ver = l1.try_release()
        self.assertEqual((True, l1.identifier, -1), (released, holder, ver))

        with l2:
            released, holder, ver = l1.try_release()
            self.assertEqual((False, l2.identifier, 0), (released, holder, ver))

            released, holder, ver = l2.try_release()
            self.assertEqual((True, l2.identifier, 0), (released, holder, ver))

    def test_zk_lost(self):
        sess = {"acquired": True}

        def watch(state):
            dd("zk node state changed to: ", state)
            sess["acquired"] = False

        self.zk.add_listener(watch)

        # test zk close

        lock = k3zkutil.ZKLock("foo_name", zkclient=self.zk)

        lock.acquire()
        self.zk.stop()
        time.sleep(0.1)
        self.assertFalse(sess["acquired"])

        # test node delete

        sess["acquired"] = True
        self.zk.start()
        self.zk.add_listener(watch)

        lock = k3zkutil.ZKLock("foo_name", zkclient=self.zk)

        with lock:
            time.sleep(0.1)
            self.zk.delete(lock.zkconf.lock("foo_name"))
            time.sleep(0.1)
            self.assertFalse(sess["acquired"])

    def test_node_change_after_acquired(self):
        sess = {"acquired": True}

        def on_lost():
            sess["acquired"] = False

        lock = k3zkutil.ZKLock("foo_name", zkclient=self.zk, on_lost=on_lost)

        with lock:
            sess["acquired"] = True
            self.zk.delete(lock.zkconf.lock("foo_name"))
            time.sleep(0.1)
            self.assertFalse(sess["acquired"])

        lock = k3zkutil.ZKLock("foo_name", zkclient=self.zk, on_lost=on_lost)

        with lock:
            sess["acquired"] = True
            self.zk.set(lock.zkconf.lock("foo_name"), b"xxx")
            time.sleep(0.1)
            self.assertFalse(sess["acquired"])

    def test_node_change_after_released(self):
        sess = {"acquired": True}

        def on_lost():
            sess["acquired"] = False

        lock = k3zkutil.ZKLock("foo_name", zkclient=self.zk, on_lost=on_lost)

        with lock:
            sess["acquired"] = True

        time.sleep(0.1)
        self.assertTrue(sess["acquired"])

    def test_is_locked(self):
        lock = k3zkutil.ZKLock("foo_name", zkclient=self.zk)

        with lock:
            pass

        self.assertFalse(lock.is_locked())

        lock = k3zkutil.ZKLock("foo_name", zkclient=self.zk)
        lock.acquire()
        self.assertTrue(lock.is_locked())
        lock.try_release()
        self.assertFalse(lock.is_locked())

    def test_conn_lost_when_blocking_acquiring(self):
        l2 = k3zkutil.ZKLock("foo_name", on_lost=lambda: True)

        th = k3thread.daemon(target=self.zk.stop, after=0.5)
        with l2:
            try:
                self.lck.acquire(timeout=1)
                self.fail("expected connection error")
            except ConnectionClosedError:
                pass

        th.join()

    def test_internal_zkclient(self):
        sess = {"acquired": True}

        def on_lost():
            sess["acquired"] = False

        # There must be a listener specified to watch connection issue
        self.assertRaises(ValueError, k3zkutil.ZKLock, "foo_name")

        lock = k3zkutil.ZKLock("foo_name", on_lost=on_lost)

        with lock:
            self.zk.delete(lock.zkconf.lock("foo_name"))
            time.sleep(0.1)
            self.assertFalse(sess["acquired"])

    def test_acl(self):
        with self.lck:
            acls, zstat = self.zk.get_acls(self.lck.lock_path)

        dd(acls)
        self.assertEqual(1, len(acls))

        acl = acls[0]
        expected = k3zkutil.perm_to_long(zk_test_acl[0][2], lower=False)

        self.assertEqual(set(expected), set(acl.acl_list))
        self.assertEqual("digest", acl.id.scheme)
        self.assertEqual(zk_test_acl[0][0], acl.id.id.split(":")[0])

    def test_config(self):
        old = (conf.zk_acl, conf.zk_auth, conf.zk_node_id)

        conf.zk_acl = (("foo", "bar", "cd"), ("xp", "123", "cdrwa"))

        conf.zk_auth = ("digest", "xp", "123")
        conf.zk_node_id = "abc"

        lock = k3zkutil.ZKLock("foo_name", on_lost=lambda: True)

        dd(lock.zkconf.acl())

        def _check_ac(ac):
            self.assertEqual("digest", ac.id.scheme)
            self.assertEqual("foo", ac.id.id.split(":")[0])
            self.assertEqual(set(["CREATE", "DELETE"]), set(ac.acl_list))

        _check_ac(lock.zkconf.kazoo_digest_acl()[0])

        with lock:
            # should have created lock node
            data, zstate = self.zk.get(lock.lock_path)
            data = k3utfjson.load(data)["id"]
            dd(data)

            self.assertEqual("abc", data.split("-")[0])

            acls, zstate = self.zk.get_acls(lock.lock_path)
            dd(acls)

            _check_ac(acls[0])

        (conf.zk_acl, conf.zk_auth, conf.zk_node_id) = old

    def test_hosts(self):
        lock = k3zkutil.ZKLock(
            "foo_name",
            zkconf=dict(
                hosts="127.0.0.1:21811",
            ),
            on_lost=lambda: True,
        )

        with lock:
            self.assertEqual("127.0.0.1:21811", lock._hosts)

    def test_specify_identifier(self):
        a = k3zkutil.ZKLock(
            "foo_name",
            zkconf=dict(
                hosts="127.0.0.1:21811",
            ),
            identifier="faked",
            on_lost=lambda: True,
        )

        b = k3zkutil.ZKLock(
            "foo_name",
            zkconf=dict(
                hosts="127.0.0.1:21811",
            ),
            identifier="faked",
            on_lost=lambda: True,
        )

        a.acquire()
        b.acquire()
        dd("a and b has the same identifier thus they both can acquire the lock")

    def test_release_listener_removed(self):
        self.lck.release()
        self.assertNotIn(self.lck.on_connection_change, self.zk.state_listeners)

    def test_release_owning_client_stopped(self):
        lock = k3zkutil.ZKLock(
            "foo_name",
            zkconf=dict(
                hosts="127.0.0.1:21811",
            ),
            on_lost=lambda: True,
        )

        lock.release()
        self.assertTrue(lock.zkclient._stopped.is_set())
