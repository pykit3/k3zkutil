import unittest
from unittest import mock

import k3ut
from k3confloader import conf
from kazoo.client import KazooClient
from kazoo.exceptions import AuthFailedError

import k3zkutil

dd = k3ut.dd


class TestZKConf(unittest.TestCase):
    def test_specified(self):
        c = k3zkutil.ZKConf(
            hosts="hosts",
            tx_dir="tx_dir/",
            record_dir="record_dir/",
            seq_dir="seq_dir/",
            lock_dir="lock_dir/",
            node_id="node_id",
            auth=("digest", "a", "b"),
            acl=(("foo", "bar", "cd"), ("xp", "123", "cdrwa")),
        )

        self.assertEqual("hosts", c.hosts())
        self.assertEqual("tx_dir/", c.tx_dir())
        self.assertEqual("record_dir/", c.record_dir())
        self.assertEqual("seq_dir/", c.seq_dir())
        self.assertEqual("lock_dir/", c.lock_dir())
        self.assertEqual("node_id", c.node_id())
        self.assertEqual(("digest", "a", "b"), c.auth())

        self.assertEqual((("foo", "bar", "cd"), ("xp", "123", "cdrwa")), c.acl())

        self.assertEqual("lock_dir/", c.lock())
        self.assertEqual("lock_dir/a", c.lock("a"))
        self.assertEqual("record_dir/", c.record())
        self.assertEqual("record_dir/a", c.record("a"))
        self.assertEqual("tx_dir/alive/", c.tx_alive())
        self.assertEqual("tx_dir/alive/a", c.tx_alive("a"))
        self.assertEqual("tx_dir/alive/0000000001", c.tx_alive(1))
        self.assertEqual("tx_dir/state/", c.tx_state())
        self.assertEqual("tx_dir/state/a", c.tx_state("a"))
        self.assertEqual("tx_dir/state/0000000001", c.tx_state(1))
        self.assertEqual("tx_dir/journal/", c.journal())
        self.assertEqual("tx_dir/journal/a", c.journal("a"))
        self.assertEqual("tx_dir/journal/journal_id0000000001", c.journal(1))
        self.assertEqual("tx_dir/journal_id_set", c.journal_id_set())
        self.assertEqual("tx_dir/txid_maker", c.txid_maker())
        self.assertEqual("seq_dir/", c.seq())
        self.assertEqual("seq_dir/a", c.seq("a"))

        self.assertEqual(
            k3zkutil.make_kazoo_digest_acl((("foo", "bar", "cd"), ("xp", "123", "cdrwa"))), c.kazoo_digest_acl()
        )
        self.assertEqual(("digest", "a:b"), c.kazoo_auth())

    def test_default(self):
        old = (
            conf.zk_hosts,
            conf.zk_tx_dir,
            conf.zk_record_dir,
            conf.zk_lock_dir,
            conf.zk_node_id,
            conf.zk_auth,
            conf.zk_acl,
        )

        conf.zk_hosts = "HOSTS"
        conf.zk_tx_dir = "TX_DIR/"
        conf.zk_record_dir = "RECORD_DIR/"
        conf.zk_seq_dir = "SEQ_DIR/"
        conf.zk_lock_dir = "LOCK_DIR/"
        conf.zk_node_id = "NODE_ID"
        conf.zk_auth = ("DIGEST", "A", "B")
        conf.zk_acl = (("FOO", "BAR", "CD"), ("XP", "123", "CDRWA"))

        c = k3zkutil.ZKConf()

        self.assertEqual("HOSTS", c.hosts())
        self.assertEqual("TX_DIR/", c.tx_dir())
        self.assertEqual("RECORD_DIR/", c.record_dir())
        self.assertEqual("SEQ_DIR/", c.seq_dir())
        self.assertEqual("LOCK_DIR/", c.lock_dir())
        self.assertEqual("NODE_ID", c.node_id())
        self.assertEqual(("DIGEST", "A", "B"), c.auth())

        self.assertEqual((("FOO", "BAR", "CD"), ("XP", "123", "CDRWA")), c.acl())

        self.assertEqual("LOCK_DIR/", c.lock())
        self.assertEqual("LOCK_DIR/a", c.lock("a"))
        self.assertEqual("RECORD_DIR/", c.record())
        self.assertEqual("RECORD_DIR/a", c.record("a"))
        self.assertEqual("SEQ_DIR/", c.seq())
        self.assertEqual("SEQ_DIR/a", c.seq("a"))
        self.assertEqual("TX_DIR/alive/", c.tx_alive())
        self.assertEqual("TX_DIR/alive/a", c.tx_alive("a"))
        self.assertEqual("TX_DIR/alive/0000000001", c.tx_alive(1))
        self.assertEqual("TX_DIR/state/", c.tx_state())
        self.assertEqual("TX_DIR/state/a", c.tx_state("a"))
        self.assertEqual("TX_DIR/state/0000000001", c.tx_state(1))
        self.assertEqual("TX_DIR/journal/", c.journal())
        self.assertEqual("TX_DIR/journal/a", c.journal("a"))
        self.assertEqual("TX_DIR/journal/journal_id0000000001", c.journal(1))
        self.assertEqual("TX_DIR/journal_id_set", c.journal_id_set())
        self.assertEqual("TX_DIR/txid_maker", c.txid_maker())

        self.assertEqual(
            k3zkutil.make_kazoo_digest_acl((("FOO", "BAR", "CD"), ("XP", "123", "CDRWA"))), c.kazoo_digest_acl()
        )
        self.assertEqual(("DIGEST", "A:B"), c.kazoo_auth())

        (
            conf.zk_hosts,
            conf.zk_tx_dir,
            conf.zk_record_dir,
            conf.zk_lock_dir,
            conf.zk_node_id,
            conf.zk_auth,
            conf.zk_acl,
        ) = old


class TestKazooClientExt(unittest.TestCase):
    def test_create_set_encode(self):
        # The raw client is a mock that records its calls, so no ZooKeeper is needed.
        cases = (
            (True, {"x": 1}, b'{"x": 1}'),
            (False, "x", b"x"),
        )

        for use_json, value, expected in cases:
            dd("json:", use_json, "value:", value)

            raw = mock.create_autospec(KazooClient, instance=True)
            zk = k3zkutil.KazooClientExt(raw, json=use_json)

            zk.create("/a", value)
            zk.set("/a", value)

            want = [
                mock.call.create("/a", value=expected, acl=None, ephemeral=False, sequence=False, makepath=False),
                mock.call.set("/a", expected, version=-1),
            ]
            self.assertEqual(want, raw.mock_calls)

    def test_auth_error_closes_owned_client(self):
        # kazoo_client_ext() creates the client from the hosts, so the KazooClient methods are mocked.
        with mock.patch.multiple(
            KazooClient, start=mock.DEFAULT, add_auth=mock.DEFAULT, stop=mock.DEFAULT, close=mock.DEFAULT
        ) as m:
            m["add_auth"].side_effect = AuthFailedError()
            zk = {"hosts": "127.0.0.1:21811", "auth": ("digest", "a", "b")}
            self.assertRaises(AuthFailedError, k3zkutil.kazoo_client_ext, zk)

        self.assertEqual([mock.call()], m["stop"].mock_calls)
        self.assertEqual([mock.call()], m["close"].mock_calls)
