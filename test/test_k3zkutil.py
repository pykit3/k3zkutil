import os
import time
import unittest
import uuid

from kazoo import security
from kazoo.client import KazooClient
from kazoo.exceptions import ConnectionClosedError
from kazoo.exceptions import NoNodeError
from kazoo.handlers.threading import KazooTimeoutError
from k3confloader import conf

import k3net
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


class Testk3zkutil(unittest.TestCase):
    def test_lock_id(self):
        k = k3zkutil.lock_id("a")
        dd(k)
        elts = k.split("-")

        self.assertEqual(4, len(elts))

        self.assertEqual("a", elts[0])
        self.assertTrue(k3net.is_ip4(elts[1]))
        self.assertEqual(os.getpid(), int(elts[2]))

    def test_lock_id_default(self):
        expected = "%012x" % uuid.getnode()

        k = k3zkutil.lock_id()
        dd(conf)
        dd(k)
        self.assertEqual(expected, k.split("-")[0])

        k = k3zkutil.lock_id(node_id=None)
        dd(k)
        self.assertEqual(expected, k.split("-")[0])

        conf.zk_node_id = "a"
        k = k3zkutil.lock_id(node_id=None)
        dd(k)
        self.assertEqual("a", k.split("-")[0])

    def test_parse_lock_id(self):
        cases = (
            ("", ("", None, None)),
            ("-", ("", "", None)),
            ("--", ("", "", None)),
            ("1-", ("1", "", None)),
            ("1-a", ("1", "a", None)),
            ("1-a-x", ("1", "a", None)),
            ("1-a-1", ("1", "a", 1)),
        )

        for inp, expected in cases:
            rst = k3zkutil.parse_lock_id(inp)

            self.assertEqual(set(["node_id", "ip", "process_id", "uuid", "txid"]), set(rst.keys()))

            self.assertEqual(expected, (rst["node_id"], rst["ip"], rst["process_id"]))

    def test_parse_lock_id_with_txid(self):
        rst = k3zkutil.parse_lock_id("txid:123-a-b-x")
        self.assertEqual("txid:123", rst["node_id"])
        self.assertEqual("123", rst["txid"])

    def test_make_digest(self):
        cases = (("aa:", "E/ZoYMT80fFT7vhICWyvMdWNt7o="), ("username:password", "+Ir5sN1lGJEEs8xBZhZXKvjLJ7c="))

        for inp, expected in cases:
            rst = k3zkutil.make_digest(inp)
            self.assertEqual(expected, rst)

    def test_make_acl_entry(self):
        username = "zookeeper_user"
        password = "MT80fFT7vh"
        perm_cases = [
            "",
            "rw",
            "cdrwa",
            [],
            ["c"],
            ["c", "r", "r"],
            (),
            ("c",),
            ("c", "r", "w"),
            iter("cdrwa"),
        ]

        for inp in perm_cases:
            if isinstance(inp, type(iter(""))):
                perm = "cdrwa"
            else:
                perm = "".join(inp)

            dd("inp=", inp)
            dd("perm=", perm)
            rst = k3zkutil.make_acl_entry(username, password, inp)

            rst_splited = rst.split(":")
            self.assertEqual(4, len(rst_splited))
            self.assertEqual(("digest", username, perm), (rst_splited[0], rst_splited[1], rst_splited[3]))

        cases = (
            ((username, password, ""), "digest:zookeeper_user:Ds8aM7UNwfAlTN3IRdkBoCno9FM=:"),
            (("aabb", "abc123", "cdrwa"), "digest:aabb:t9MeAsoEPfdQEQjqbWtw8EHD9T0=:cdrwa"),
        )

        for inp, expected in cases:
            rst = k3zkutil.make_acl_entry(inp[0], inp[1], inp[2])
            self.assertEqual(expected, rst)

        invalid_perm_cases = (
            "abc",
            ["cde"],
            ["a", "v"],
            ("rw",),
            ("a", "b", "c"),
        )

        for inp in invalid_perm_cases:
            with self.assertRaises(k3zkutil.PermTypeError):
                k3zkutil.make_acl_entry(username, password, inp)

    def test_permission_convert(self):
        perm_cases = (
            ("", [], ""),
            ("rw", ["read", "write"], "rw"),
            ("cdrwa", ["create", "delete", "read", "write", "admin"], "cdrwa"),
            ([], [], ""),
            (["c"], ["create"], "c"),
            (["c", "r", "r"], ["create", "read", "read"], "crr"),
            ((), [], ""),
            (("c",), ["create"], "c"),
            (("c", "r", "w"), ["create", "read", "write"], "crw"),
            (iter("cdrwa"), ["create", "delete", "read", "write", "admin"], "cdrwa"),
        )

        for inp, lng, short in perm_cases:
            rst = k3zkutil.perm_to_long(inp)
            self.assertEqual(lng, rst)

            rst = k3zkutil.perm_to_short(lng)
            self.assertEqual(short, rst)

        # invalid short format

        invalid_short = (
            "abc",
            ["cde"],
            ["a", "v"],
            ("rw",),
            ("a", "b", "c"),
        )

        for inp in invalid_short:
            self.assertRaises(k3zkutil.PermTypeError, k3zkutil.perm_to_long, inp)

        # invalid long format

        invalid_long = (
            "abc",
            ["foo"],
        )

        for inp in invalid_long:
            self.assertRaises(k3zkutil.PermTypeError, k3zkutil.perm_to_short, inp)

    def test_permission_convert_case(self):
        self.assertEqual(["CREATE", "DELETE", "READ", "WRITE", "ADMIN"], k3zkutil.perm_to_long("cdrwa", lower=False))

        self.assertEqual(["CREATE", "DELETE", "READ", "WRITE", "ADMIN"], k3zkutil.perm_to_long("CDRWA", lower=False))

        self.assertEqual(["create", "delete", "read", "write", "admin"], k3zkutil.perm_to_long("CDRWA"))

        self.assertEqual("CDRWA", k3zkutil.perm_to_short(["create", "delete", "read", "write", "admin"], lower=False))

        self.assertEqual("CDRWA", k3zkutil.perm_to_short(["CREATE", "DELETE", "READ", "WRITE", "ADMIN"], lower=False))
        self.assertEqual("cdrwa", k3zkutil.perm_to_short(["CREATE", "DELETE", "READ", "WRITE", "ADMIN"]))

    def test_make_kazoo_digest_acl(self):
        inp = (("foo", "bar", "cd"), ("xp", "123", "cdrwa"))

        dd(inp)

        rst = k3zkutil.make_kazoo_digest_acl(inp)
        dd(rst)

        self.assertEqual(2, len(rst))

        ac = rst[0]
        self.assertEqual("digest", ac.id.scheme)
        self.assertEqual("foo", ac.id.id.split(":")[0])
        self.assertEqual(set(["CREATE", "DELETE"]), set(ac.acl_list))

        ac = rst[1]
        self.assertEqual("digest", ac.id.scheme)
        self.assertEqual("xp", ac.id.id.split(":")[0])
        self.assertEqual(set(["ALL"]), set(ac.acl_list))

        self.assertIsNone(k3zkutil.make_kazoo_digest_acl(None))

    def test_parse_kazoo_acl(self):
        inp = (
            security.make_acl("world", "anyone", all=True),
            security.make_digest_acl("foo", "bar", create=True, read=True),
            security.make_digest_acl("xp", "123", all=True),
        )
        expected = (("world", "anyone", "cdrwa"), ("digest", "foo", "rc"), ("digest", "xp", "cdrwa"))

        dd(inp)

        rst = k3zkutil.parse_kazoo_acl(inp)
        dd(rst)

        self.assertEqual(expected, tuple(rst))

    def test_is_backward_locking(self):
        cases = (
            ([], "a", False, None),
            (["a"], "a", False, AssertionError),
            (["a", "c"], "a", True, AssertionError),
            (["a", "c"], "c", True, AssertionError),
            (["a", "c"], "", True, None),
            (["a", "c"], "b", True, None),
            (["a", "c"], "d", False, None),
        )

        for locked, key, expected, err in cases:
            if err is None:
                rst = k3zkutil.is_backward_locking(locked, key)
                self.assertEqual(expected, rst)
            else:
                self.assertRaises(err, k3zkutil.is_backward_locking, locked, key)


class TestZKinit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        k3utdocker.pull_image(zk_tag)

    def setUp(self):
        k3utdocker.create_network()

        k3utdocker.start_container(zk_name, zk_tag, port_bindings={2181: 21811})

        # Wait for zookeeper to be ready
        zk = wait_for_zk("127.0.0.1:21811")
        zk.stop()

        dd("start zk-test in docker")

    def tearDown(self):
        k3utdocker.stop_container(zk_name)
        k3utdocker.remove_container(zk_name)

        dd("remove_container: " + zk_name)

    def test_init_hierarchy(self):
        auth = ("digest", "aa", "pw_aa")
        hosts = "127.0.0.1:21811"
        users = {"aa": "pw_aa", "bb": "pw_bb", "cc": "pw_cc"}
        hierarchy = {
            "node1": {
                "__val__": b"node1_val",
                "__acl__": {"aa": "cdrwa", "bb": "rw"},
                "node11": {
                    "__val__": b"node11_val",
                    "__acl__": {"aa": "cdrwa", "cc": "r"},
                },
                "node12": {"__val__": b"node12_val", "node121": {"__val__": "node121_val"}},
                "node13": {"__acl__": {"aa": "cdrwa"}},
            },
            "node2": {
                "__val__": b"node2_val",
                "node21": {"__val__": b"node21_val"},
                "node22": {"__acl__": {"aa": "rwa"}},
            },
            "node3": {"__acl__": {"aa": "carw", "cc": "r"}, "node31": {"node311": {"node3111": {}, "node3112": {}}}},
        }

        k3zkutil.init_hierarchy(hosts, hierarchy, users, auth)

        zkcli = KazooClient(hosts)
        zkcli.start()
        zkcli.add_auth("digest", "aa:pw_aa")

        expected_nodes = (
            (
                "/node1",
                b'"node1_val"',
                [("digest", "aa", "cdrwa"), ("digest", "bb", "rw")],
                set(["node11", "node12", "node13"]),
            ),
            ("/node1/node11", b'"node11_val"', [("digest", "aa", "cdrwa"), ("digest", "cc", "r")], set([])),
            ("/node1/node12", b'"node12_val"', [("digest", "aa", "cdrwa"), ("digest", "bb", "rw")], set(["node121"])),
            ("/node1/node12/node121", b'"node121_val"', [("digest", "aa", "cdrwa"), ("digest", "bb", "rw")], set([])),
            ("/node1/node13", b"{}", [("digest", "aa", "cdrwa")], set([])),
            ("/node2", b'"node2_val"', [("world", "anyone", "cdrwa")], set(["node21", "node22"])),
            ("/node2/node21", b'"node21_val"', [("world", "anyone", "cdrwa")], set([])),
            ("/node2/node22", b"{}", [("digest", "aa", "rwa")], set([])),
            ("/node3", b"{}", [("digest", "aa", "rwca"), ("digest", "cc", "r")], set(["node31"])),
            ("/node3/node31", b"{}", [("digest", "aa", "rwca"), ("digest", "cc", "r")], set(["node311"])),
            (
                "/node3/node31/node311",
                b"{}",
                [("digest", "aa", "rwca"), ("digest", "cc", "r")],
                set(["node3111", "node3112"]),
            ),
            ("/node3/node31/node311/node3111", b"{}", [("digest", "aa", "rwca"), ("digest", "cc", "r")], set([])),
            ("/node3/node31/node311/node3112", b"{}", [("digest", "aa", "rwca"), ("digest", "cc", "r")], set([])),
        )

        for node, val, acl, children in expected_nodes:
            actual_acl = k3zkutil.parse_kazoo_acl(zkcli.get_acls(node)[0])
            self.assertEqual(val, zkcli.get(node)[0])
            self.assertEqual(acl, actual_acl)
            self.assertEqual(children, set(zkcli.get_children(node)))

        zkcli.stop()

    def test_export_hierarchy(self):
        auth = ("digest", "aa", "pw_aa")
        hosts = "127.0.0.1:21811"
        users = {"aa": "pw_aa", "bb": "pw_bb", "cc": "pw_cc"}

        hierarchy = {
            "node0": {"__val__": b"", "__acl__": {"aa": "cdrwa", "bb": "rw"}},
            "node1": {
                "__val__": b"node1_val",
                "__acl__": {"aa": "cdrwa", "bb": "rw"},
                "node11": {
                    "__val__": b"node11_val",
                    "__acl__": {"aa": "cdrwa", "cc": "r"},
                },
                "node12": {"__val__": b"node12_val", "node121": {"__val__": "node121_val"}},
                "node13": {"__acl__": {"aa": "cdrwa"}},
            },
            "node2": {
                "__val__": b"node2_val",
                "node21": {"__val__": b"node21_val"},
                "node22": {"__acl__": {"aa": "rwa"}},
            },
            "node3": {"__acl__": {"aa": "carw", "cc": "r"}, "node31": {"node311": {"node3111": {}, "node3112": {}}}},
        }

        k3zkutil.init_hierarchy(hosts, hierarchy, users, auth)

        zkcli = KazooClient(hosts)
        zkcli.start()
        zkcli.add_auth("digest", "aa:pw_aa")

        invalid_zkpath_cases = ("a", "a/", "a/b")

        for zkpath in invalid_zkpath_cases:
            with self.assertRaises(k3zkutil.ZkPathError):
                k3zkutil.zkutil.export_hierarchy(zkcli, zkpath)

        valid_cases = (
            (
                "/",
                {
                    "__acl__": {"anyone": "cdrwa"},
                    "__val__": b"",
                    "node0": {"__acl__": {"aa": "cdrwa", "bb": "rw"}, "__val__": b'""'},
                    "node1": {
                        "__acl__": {"aa": "cdrwa", "bb": "rw"},
                        "__val__": b'"node1_val"',
                        "node11": {"__acl__": {"aa": "cdrwa", "cc": "r"}, "__val__": b'"node11_val"'},
                        "node12": {
                            "__acl__": {"aa": "cdrwa", "bb": "rw"},
                            "__val__": b'"node12_val"',
                            "node121": {"__acl__": {"aa": "cdrwa", "bb": "rw"}, "__val__": b'"node121_val"'},
                        },
                        "node13": {"__acl__": {"aa": "cdrwa"}, "__val__": b"{}"},
                    },
                    "node2": {
                        "__acl__": {"anyone": "cdrwa"},
                        "__val__": b'"node2_val"',
                        "node21": {"__acl__": {"anyone": "cdrwa"}, "__val__": b'"node21_val"'},
                        "node22": {"__acl__": {"aa": "rwa"}, "__val__": b"{}"},
                    },
                    "node3": {
                        "__acl__": {"aa": "rwca", "cc": "r"},
                        "__val__": b"{}",
                        "node31": {
                            "__acl__": {"aa": "rwca", "cc": "r"},
                            "__val__": b"{}",
                            "node311": {
                                "__acl__": {"aa": "rwca", "cc": "r"},
                                "__val__": b"{}",
                                "node3111": {"__acl__": {"aa": "rwca", "cc": "r"}, "__val__": b"{}"},
                                "node3112": {"__acl__": {"aa": "rwca", "cc": "r"}, "__val__": b"{}"},
                            },
                        },
                    },
                    "zookeeper": {
                        "__acl__": {"anyone": "cdrwa"},
                        "__val__": b"",
                        "quota": {"__acl__": {"anyone": "cdrwa"}, "__val__": b""},
                    },
                },
            ),
            ("/node0", {"__acl__": {"aa": "cdrwa", "bb": "rw"}, "__val__": b'""'}),
            (
                "/node1",
                {
                    "__acl__": {"aa": "cdrwa", "bb": "rw"},
                    "__val__": b'"node1_val"',
                    "node11": {"__acl__": {"aa": "cdrwa", "cc": "r"}, "__val__": b'"node11_val"'},
                    "node12": {
                        "__acl__": {"aa": "cdrwa", "bb": "rw"},
                        "__val__": b'"node12_val"',
                        "node121": {"__acl__": {"aa": "cdrwa", "bb": "rw"}, "__val__": b'"node121_val"'},
                    },
                    "node13": {"__acl__": {"aa": "cdrwa"}, "__val__": b"{}"},
                },
            ),
            ("/node1/node11", {"__acl__": {"aa": "cdrwa", "cc": "r"}, "__val__": b'"node11_val"'}),
            (
                "/node2",
                {
                    "__acl__": {"anyone": "cdrwa"},
                    "__val__": b'"node2_val"',
                    "node21": {"__acl__": {"anyone": "cdrwa"}, "__val__": b'"node21_val"'},
                    "node22": {"__acl__": {"aa": "rwa"}, "__val__": b"{}"},
                },
            ),
            (
                "/node3",
                {
                    "__acl__": {"aa": "rwca", "cc": "r"},
                    "__val__": b"{}",
                    "node31": {
                        "__acl__": {"aa": "rwca", "cc": "r"},
                        "__val__": b"{}",
                        "node311": {
                            "__acl__": {"aa": "rwca", "cc": "r"},
                            "__val__": b"{}",
                            "node3111": {"__acl__": {"aa": "rwca", "cc": "r"}, "__val__": b"{}"},
                            "node3112": {"__acl__": {"aa": "rwca", "cc": "r"}, "__val__": b"{}"},
                        },
                    },
                },
            ),
        )

        for path, expected_rst in valid_cases:
            rst = k3zkutil.export_hierarchy(zkcli, path)
            # Remove zookeeper system node for version-agnostic comparison
            # (ZK 3.9 adds different system nodes than older versions)
            if "zookeeper" in rst:
                del rst["zookeeper"]
            if "zookeeper" in expected_rst:
                expected_rst = dict(expected_rst)  # copy to avoid modifying original
                del expected_rst["zookeeper"]
            self.assertEqual(rst, expected_rst)

        zkcli.stop()


class TestWait(unittest.TestCase):
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

    def tearDown(self):
        self.zk.stop()
        k3utdocker.remove_container(zk_name)

    def test_wait_absent(self):
        for wait_time in (
            -1,
            0.0,
            0.1,
            1,
        ):
            dd("no node wait:", wait_time)

            with k3ut.Timer() as t:
                k3zkutil.wait_absent(self.zk, "a", wait_time)
                self.assertAlmostEqual(0, t.spent(), delta=0.2)

    def test_wait_absent_no_timeout(self):
        def _del():
            time.sleep(1)
            self.zk.delete("a")

        for kwargs in (
            {},
            {"timeout": None},
        ):
            self.zk.create("a")
            th = k3thread.daemon(target=_del)

            with k3ut.Timer() as t:
                k3zkutil.wait_absent(self.zk, "a", **kwargs)
                self.assertAlmostEqual(1, t.spent(), delta=0.1)

            th.join()

    def test_wait_absent_timeout(self):
        self.zk.create("a")

        for wait_time in (
            -1,
            0.0,
            0.1,
            1,
        ):
            dd("node present wait:", wait_time)
            expected = max([0, wait_time])

            with k3ut.Timer() as t:
                self.assertRaises(k3zkutil.ZKWaitTimeout, k3zkutil.wait_absent, self.zk, "a", timeout=wait_time)
                self.assertAlmostEqual(expected, t.spent(), delta=0.2)

        self.zk.delete("a")

    def test_wait_absent_delete_node(self):
        delete_after = 0.2

        for wait_time in (
            0.5,
            1,
        ):
            dd("node present wait:", wait_time)

            self.zk.create("a")

            def _del():
                time.sleep(delete_after)
                self.zk.delete("a")

            th = k3thread.daemon(target=_del)
            with k3ut.Timer() as t:
                k3zkutil.wait_absent(self.zk, "a", wait_time)
                self.assertAlmostEqual(delete_after, t.spent(), delta=0.1)

            th.join()

    def test_wait_absent_change_node(self):
        self.zk.create("a")

        change_after = 0.2

        for wait_time in (
            0.5,
            1,
        ):
            dd("node present wait:", wait_time)
            expected = max([0, wait_time])

            def _change():
                time.sleep(change_after)
                self.zk.set("a", b"bbb")

            th = k3thread.daemon(target=_change)
            with k3ut.Timer() as t:
                self.assertRaises(k3zkutil.ZKWaitTimeout, k3zkutil.wait_absent, self.zk, "a", timeout=wait_time)
                self.assertAlmostEqual(expected, t.spent(), delta=0.1)

            th.join()

        self.zk.delete("a")

    def test_wait_absent_connection_lost(self):
        self.zk.create("a")

        def _close():
            time.sleep(0.3)
            self.zk.stop()

        th = k3thread.daemon(target=_close)

        with k3ut.Timer() as t:
            self.assertRaises(ConnectionClosedError, k3zkutil.wait_absent, self.zk, "a")
            self.assertAlmostEqual(0.3, t.spent(), delta=0.1)

        th.join()

    def test_get_next_no_version(self):
        cases = (
            -1,
            0.0,
            0.1,
            1,
        )

        for timeout in cases:
            self.zk.create("a", b"a-val")

            with k3ut.Timer() as t:
                k3zkutil.get_next(self.zk, "a", timeout=timeout, version=-1)
                self.assertAlmostEqual(0, t.spent(), delta=0.2)

            with k3ut.Timer() as t:
                k3zkutil.get_next(self.zk, "a", timeout=timeout)
                self.assertAlmostEqual(0, t.spent(), delta=0.2)

            self.zk.delete("a")

    def test_get_next_timeout(self):
        cases = (
            -1,
            0.0,
            0.2,
            1,
        )

        for timeout in cases:
            expected = max([timeout, 0])
            self.zk.create("a", b"a-val")

            with k3ut.Timer() as t:
                self.assertRaises(k3zkutil.ZKWaitTimeout, k3zkutil.get_next, self.zk, "a", timeout=timeout, version=0)
                self.assertAlmostEqual(expected, t.spent(), delta=0.2)

            self.zk.delete("a")

    def test_get_next_changed(self):
        cases = (
            0.4,
            1,
        )

        def _set_a():
            self.zk.set("a", b"changed")

        for timeout in cases:
            self.zk.create("a", b"a-val")
            th = k3thread.daemon(target=_set_a, after=0.3)

            with k3ut.Timer() as t:
                val, zstat = k3zkutil.get_next(self.zk, "a", timeout=timeout, version=0)
                self.assertAlmostEqual(0.3, t.spent(), delta=0.2)
                self.assertEqual(b"changed", val)
                self.assertEqual(1, zstat.version)

            th.join()
            self.zk.delete("a")

    def test_get_next_changed_but_unsatisfied(self):
        cases = (
            0.4,
            1,
        )

        def _set_a():
            self.zk.set("a", b"changed")

        for timeout in cases:
            self.zk.create("a", b"a-val")
            th = k3thread.daemon(target=_set_a, after=0.3)

            with k3ut.Timer() as t:
                self.assertRaises(k3zkutil.ZKWaitTimeout, k3zkutil.get_next, self.zk, "a", timeout=timeout, version=5)
                self.assertAlmostEqual(timeout, t.spent(), delta=0.2)

            th.join()
            self.zk.delete("a")

    def test_get_next_deleted(self):
        cases = (
            0.4,
            1,
        )

        def _del_a():
            self.zk.delete("a")

        for timeout in cases:
            self.zk.create("a", b"a-val")
            th = k3thread.daemon(target=_del_a, after=0.3)

            with k3ut.Timer() as t:
                self.assertRaises(NoNodeError, k3zkutil.get_next, self.zk, "a", timeout=timeout, version=0)
                self.assertAlmostEqual(0.3, t.spent(), delta=0.2)

            th.join()

    def test_get_next_conn_lost(self):
        self.zk.create("a", b"a-val")
        th = k3thread.daemon(target=self.zk.stop, after=0.3)

        with k3ut.Timer() as t:
            self.assertRaises(ConnectionClosedError, k3zkutil.get_next, self.zk, "a", timeout=1, version=0)
            self.assertAlmostEqual(0.3, t.spent(), delta=0.2)

        th.join()
