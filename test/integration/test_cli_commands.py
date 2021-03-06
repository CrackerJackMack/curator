import elasticsearch
import curator
import os
import click
from click import testing as clicktest
from mock import patch, Mock

from . import CuratorTestCase

import logging
logger = logging.getLogger(__name__)

host, port = os.environ.get('TEST_ES_SERVER', 'localhost:9200').split(':')
port = int(port) if port else 9200

class TestGetClient(CuratorTestCase):
    def test_get_client_positive(self):
        client_args = {"host":host, "port":port}
        client = curator.get_client(**client_args)
        self.assertTrue(isinstance(client, elasticsearch.client.Elasticsearch))
    def test_get_client_negative_connection_fail(self):
        client_args = {"host":host, "port":54321}
        with self.assertRaises(SystemExit) as cm:
            curator.get_client(**client_args)
        self.assertEqual(cm.exception.code, 1)

class TestCLIIndexSelection(CuratorTestCase):
    def test_index_selection_only_timestamp_filter(self):
        self.create_indices(10)
        indices = curator.get_indices(self.client)
        expected = sorted(indices, reverse=True)[:4]
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                        '--timestring', '%Y.%m.%d',
                    ],
                    obj={"filters":[]})
        output = sorted(result.output.splitlines(), reverse=True)[:4]
        self.assertEqual(expected, output)
    def test_index_selection_no_filters(self):
        self.create_indices(1)
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                    ],
                    obj={"filters":[]})
        self.assertEqual(1, result.exit_code)
    def test_index_selection_manual_selection_single(self):
        self.create_index('my_index')
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                        '--index', 'my_index',
                    ],
                    obj={"filters":[]})
        self.assertEqual(['my_index'], result.output.splitlines()[:1])
    def test_index_selection_no_indices_test(self):
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        self.assertEqual(1, result.exit_code)
    def test_index_selection_all_indices_single(self):
        self.create_index('my_index')
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        self.assertEqual(['my_index'], result.output.splitlines()[:1])
    def test_index_selection_all_indices_exclude(self):
        self.create_index('my_index')
        self.create_index('your_index')
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                        '--all-indices',
                        '--exclude', '^your.*$',
                    ],
                    obj={"filters":[]})
        self.assertEqual(['my_index'], result.output.splitlines()[:1])
    def test_index_selection_regex_match(self):
        self.create_index('my_index')
        self.create_index('your_index')
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                        '--regex', '^my.*$',
                    ],
                    obj={"filters":[]})
        self.assertEqual(['my_index'], result.output.splitlines()[:1])
    def test_index_selection_all_indices_skip_non_exclude_filters(self):
        self.create_index('my_index')
        self.create_index('your_index')
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                        '--all-indices',
                        '--suffix', 'index',
                    ],
                    obj={"filters":[]})
        self.assertEqual(['my_index', 'your_index'], result.output.splitlines()[:2])
    def test_cli_show_indices_if_dry_run(self):
        self.create_indices(10)
        indices = curator.get_indices(self.client)
        expected = sorted(indices, reverse=True)[:4]
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--dry-run',
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'alias', '--name', 'dummy_alias',
                        'indices',
                        '--newer-than', '5',
                        '--timestring', '%Y.%m.%d',
                        '--time-unit', 'days'
                    ],
                    obj={"filters":[]})
        output = sorted(result.output.splitlines(), reverse=True)[:4]
        self.assertEqual(expected, output)
    def test_cli_no_indices_after_filtering(self):
        self.create_indices(10)
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                        '--exclude', 'log',
                    ],
                    obj={"filters":[]})
        self.assertEqual(99, result.exit_code)

class TestCLIAlias(CuratorTestCase):
    def test_alias_no_name_param(self):
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'alias',
                        'indices',
                        '--exclude', 'log',
                    ],
                    obj={"filters":[]})
        self.assertEqual(1, result.exit_code)
    def test_alias_all_indices_single(self):
        self.create_index('my_index')
        alias = 'testalias'
        self.create_index('dummy')
        self.client.indices.put_alias(index='dummy', name=alias)
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'alias', '--name', alias,
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        self.assertEquals(2, len(self.client.indices.get_alias(name=alias)))

class TestCLIAllocation(CuratorTestCase):
    def test_allocation_no_rule_param(self):
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'allocation',
                        'indices',
                        '--exclude', 'log',
                    ],
                    obj={"filters":[]})
        self.assertEqual(1, result.exit_code)
    def test_allocation_all_indices_single(self):
        self.create_index('my_index')
        key = 'foo'
        value = 'bar'
        rule = key + '=' + value
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'allocation', '--rule', rule,
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        self.assertEquals(
            value,
            self.client.indices.get_settings(index='my_index')['my_index']['settings']['index']['routing']['allocation']['require'][key]
        )

class TestCLIBloom(CuratorTestCase):
    def test_bloom_cli(self):
        self.create_indices(5)
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'bloom',
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        self.assertEqual(0, result.exit_code)

class TestCLIClose(CuratorTestCase):
    def test_close_cli(self):
        self.create_indices(5)
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'close',
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        self.assertEqual(0, result.exit_code)

class TestCLIDelete(CuratorTestCase):
    def test_delete_indices_skip_kibana(self):
        self.create_index('my_index')
        self.create_index('.kibana')
        self.create_index('kibana-int')
        self.create_index('.marvel-kibana')
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'delete',
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        l = curator.get_indices(self.client)
        self.assertEqual(sorted(['.kibana', '.marvel-kibana', 'kibana-int']), sorted(l))
    def test_delete_indices_dry_run(self):
        self.create_indices(9)
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--dry-run',
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'delete',
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        l = curator.get_indices(self.client)
        self.assertEquals(9, len(l))
        output = sorted(result.output.splitlines(), reverse=True)[:9]
        self.assertEqual(sorted(l, reverse=True), output)
    def test_delete_indices_by_space_dry_run(self):
        for i in range(1,10):
            self.client.create(
                index="index" + str(i), doc_type='log',
                body={'message':'TEST DOCUMENT'},
            )
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--dry-run',
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'delete',
                        '--disk-space', '0.0000001',
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        l = curator.get_indices(self.client)
        self.assertEquals(9, len(l))
        output = sorted(result.output.splitlines(), reverse=True)[:9]
        self.assertEqual(sorted(l, reverse=True), output)
    def test_delete_indices_huge_list(self):
        self.create_indices(365)
        pre = curator.get_indices(self.client)
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'delete',
                        'indices',
                        '--all-indices',
                        '--exclude', pre[0],
                    ],
                    obj={"filters":[]})
        post = curator.get_indices(self.client)
        self.assertEquals(1, len(post))

class TestCLIOpen(CuratorTestCase):
    def test_open_cli(self):
        self.create_indices(5)
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'open',
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        self.assertEqual(0, result.exit_code)

class TestCLIOptimize(CuratorTestCase):
    def test_optimize_cli(self):
        self.create_indices(5)
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'optimize',
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        self.assertEqual(0, result.exit_code)

class TestCLIReplicas(CuratorTestCase):
    def test_replicas_no_count_param(self):
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'replicas',
                        'indices',
                        '--exclude', 'log',
                    ],
                    obj={"filters":[]})
        self.assertEqual(1, result.exit_code)
    def test_replicas_cli(self):
        self.create_indices(5)
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'replicas', '--count', '2',
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        self.assertEqual(0, result.exit_code)

class TestCLIShow(CuratorTestCase):
    def test_cli_show_indices(self):
        self.create_indices(10)
        indices = curator.get_indices(self.client)
        expected = sorted(indices, reverse=True)[:4]
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                        '--newer-than', '5',
                        '--timestring', '%Y.%m.%d',
                        '--time-unit', 'days'
                    ],
                    obj={"filters":[]})
        output = sorted(result.output.splitlines(), reverse=True)[:4]
        self.assertEqual(expected, output)

class TestCLISnapshot(CuratorTestCase):
    def test_snapshot_no_repository_param(self):
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'snapshot',
                        'indices',
                        '--exclude', 'log',
                    ],
                    obj={"filters":[]})
        self.assertEqual(1, result.exit_code)
    def test_cli_snapshot_indices(self):
        self.create_indices(5)
        self.create_repository()
        snap_name = 'snapshot1'
        indices = curator.get_indices(self.client)
        expected = sorted(indices, reverse=True)[:4]
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'snapshot',
                        '--repository', self.args['repository'],
                        '--name', snap_name,
                        'indices',
                        '--all-indices',
                    ],
                    obj={"filters":[]})
        snapshot = curator.get_snapshot(
                    self.client, self.args['repository'], '_all'
                   )
        self.assertEqual(1, len(snapshot['snapshots']))
        self.assertEqual(snap_name, snapshot['snapshots'][0]['snapshot'])


class TestCLISnapshotSelection(CuratorTestCase):
    def test_show_no_repository_param(self):
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'snapshots',
                        '--exclude', 'log',
                    ],
                    obj={"filters":[]})
        self.assertEqual(1, result.exit_code)
    def test_snapshot_selection_show_all_snapshots(self):
        index_name = 'index1'
        snap_name = 'snapshot1'
        self.create_index(index_name)
        self.create_repository()
        self.client.create(
            index=index_name, doc_type='log', body={'message':'TEST DOCUMENT'}
            )
        curator.create_snapshot(
            self.client, name=snap_name, indices=index_name,
            repository=self.args['repository']
            )
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'snapshots',
                        '--repository', self.args['repository'],
                        '--all-snapshots',
                    ],
                    obj={"filters":[]})
        self.assertEqual([snap_name], result.output.splitlines()[:1])
    def test_snapshot_selection_show_all_snapshots_with_exclude(self):
        self.create_repository()
        for i in ["1", "2"]:
            self.create_index("index" + i)
            self.client.create(
                index="index" + i, doc_type='log',
                body={'message':'TEST DOCUMENT'},
            )
            curator.create_snapshot(
                self.client, name="snapshot" + i, indices="index" + i,
                repository=self.args['repository']
            )
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'snapshots',
                        '--repository', self.args['repository'],
                        '--all-snapshots',
                        '--exclude', '2',
                    ],
                    obj={"filters":[]})
        self.assertEqual(['snapshot1'], result.output.splitlines()[:1])
    def test_snapshot_selection_no_snapshots_found(self):
        self.create_repository()
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'snapshots',
                        '--repository', self.args['repository'],
                        '--all-snapshots',
                    ],
                    obj={"filters":[]})
        self.assertEqual(1, result.exit_code)
    def test_snapshot_selection_show_filtered(self):
        self.create_repository()
        for i in ["1", "2", "3"]:
            self.create_index("index" + i)
            self.client.create(
                index="index" + i, doc_type='log',
                body={'message':'TEST DOCUMENT'},
            )
            curator.create_snapshot(
                self.client, name="snapshot" + i, indices="index" + i,
                repository=self.args['repository']
            )
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'snapshots',
                        '--repository', self.args['repository'],
                        '--prefix', 'snap',
                        '--suffix', '1',
                    ],
                    obj={"filters":[]})
        self.assertEqual(['snapshot1'], result.output.splitlines()[:1])
    def test_snapshot_selection_show_all_snapshots_with_exclude_and_other(self):
        self.create_repository()
        for i in ["1", "2"]:
            self.create_index("index" + i)
            self.client.create(
                index="index" + i, doc_type='log',
                body={'message':'TEST DOCUMENT'},
            )
            curator.create_snapshot(
                self.client, name="snapshot" + i, indices="index" + i,
                repository=self.args['repository']
            )
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'snapshots',
                        '--repository', self.args['repository'],
                        '--all-snapshots',
                        '--exclude', '2',
                        '--prefix', 'missing',
                        '--suffix', 'also_missing',
                    ],
                    obj={"filters":[]})
        self.assertEqual(['snapshot1'], result.output.splitlines()[:1])
    def test_snapshot_selection_delete_all_snapshots_with_dry_run(self):
        self.create_repository()
        for i in ["1", "2"]:
            self.create_index("index" + i)
            self.client.create(
                index="index" + i, doc_type='log',
                body={'message':'TEST DOCUMENT'},
            )
            curator.create_snapshot(
                self.client, name="snapshot" + i, indices="index" + i,
                repository=self.args['repository']
            )
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--dry-run',
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'delete',
                        'snapshots',
                        '--repository', self.args['repository'],
                        '--all-snapshots',
                        '--exclude', '2',
                    ],
                    obj={"filters":[]})
        self.assertEqual(['snapshot1'], result.output.splitlines()[:1])
    def test_snapshot_selection_delete_snapshot(self):
        self.create_repository()
        for i in ["1", "2"]:
            self.create_index("index" + i)
            self.client.create(
                index="index" + i, doc_type='log',
                body={'message':'TEST DOCUMENT'},
            )
            curator.create_snapshot(
                self.client, name="snapshot" + i, indices="index" + i,
                repository=self.args['repository']
            )
        result = curator.get_snapshot(self.client, self.args['repository'], '_all')
        self.assertEqual(2, len(result['snapshots']))
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'delete',
                        'snapshots',
                        '--repository', self.args['repository'],
                        '--exclude', '2',
                    ],
                    obj={"filters":[]})
        result = curator.get_snapshot(self.client, self.args['repository'], '_all')
        self.assertEqual(1, len(result['snapshots']))
        self.assertEqual('snapshot2', result['snapshots'][0]['snapshot'])
    def test_snapshot_selection_all_filtered_fail(self):
        self.create_repository()
        for i in ["1", "2", "3"]:
            self.create_index("index" + i)
            self.client.create(
                index="index" + i, doc_type='log',
                body={'message':'TEST DOCUMENT'},
            )
            curator.create_snapshot(
                self.client, name="snapshot" + i, indices="index" + i,
                repository=self.args['repository']
            )
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'snapshots',
                        '--repository', self.args['repository'],
                        '--prefix', 'no_match',
                    ],
                    obj={"filters":[]})
        self.assertEqual(99, result.exit_code)

class TestCLILogging(CuratorTestCase):
    def test_logging_with_debug_flag(self):
        self.create_indices(10)
        indices = curator.get_indices(self.client)
        expected = sorted(indices, reverse=True)[:4]
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--debug',
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                        '--newer-than', '5',
                        '--timestring', '%Y.%m.%d',
                        '--time-unit', 'days'
                    ],
                    obj={"filters":[]})
        output = sorted(result.output.splitlines(), reverse=True)[:4]
        self.assertEqual(expected, output)

    def test_logging_with_bad_loglevel_flag(self):
        self.create_indices(1)
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--loglevel', 'FOO',
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                        '--newer-than', '5',
                        '--timestring', '%Y.%m.%d',
                        '--time-unit', 'days'
                    ],
                    obj={"filters":[]})
        self.assertEqual('Invalid log level: FOO', str(result.exception))

    def test_logging_with_logformat_logstash_flag(self):
        self.create_indices(10)
        indices = curator.get_indices(self.client)
        expected = sorted(indices, reverse=True)[:4]
        test = clicktest.CliRunner()
        result = test.invoke(
                    curator.cli,
                    [
                        '--logformat', 'logstash',
                        '--logfile', os.devnull,
                        '--host', host,
                        '--port', str(port),
                        'show',
                        'indices',
                        '--newer-than', '5',
                        '--timestring', '%Y.%m.%d',
                        '--time-unit', 'days'
                    ],
                    obj={"filters":[]})
        output = sorted(result.output.splitlines(), reverse=True)[:4]
        self.assertEqual(expected, output)
