"""容器运行所需的监听地址和日志行为。"""
import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from easyread.app import cli
from easyread.app import log as app_log


class ServeHostTest(unittest.TestCase):
    def args(self, host=None):
        return SimpleNamespace(host=host, port=None, open=False, exit_on_close=False)

    def test_explicit_host_starts_a_new_server(self):
        with mock.patch.object(cli, "running_server") as running, \
                mock.patch("easyread.server.launch.serve") as serve:
            cli.cmd_serve(self.args("0.0.0.0"))
        running.assert_not_called()
        serve.assert_called_once_with(None, False, exit_on_close=False, host="0.0.0.0")

    def test_host_environment_starts_a_new_server(self):
        with mock.patch.dict(os.environ, {"EASYREAD_HOST": "0.0.0.0"}), \
                mock.patch.object(cli, "running_server") as running, \
                mock.patch("easyread.server.launch.serve") as serve:
            cli.cmd_serve(self.args())
        running.assert_not_called()
        serve.assert_called_once_with(None, False, exit_on_close=False, host=None)


class ContainerLogTest(unittest.TestCase):
    def test_stderr_can_be_enabled_without_a_tty(self):
        old_handlers = list(app_log.log.handlers)
        old_level = app_log.log.level
        for handler in old_handlers:
            app_log.log.removeHandler(handler)
        stream = io.StringIO()
        try:
            with tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.dict(os.environ, {"EASYREAD_LOG_STDERR": "1"}), \
                    mock.patch.object(app_log.sys, "stderr", stream):
                app_log.setup(Path(tmp) / "easyread.log")
                app_log.log.info("container-visible")
                for handler in app_log.log.handlers:
                    handler.flush()
                self.assertIn("container-visible", stream.getvalue())
        finally:
            for handler in list(app_log.log.handlers):
                app_log.log.removeHandler(handler)
                handler.close()
            for handler in old_handlers:
                app_log.log.addHandler(handler)
            app_log.log.setLevel(old_level)


if __name__ == "__main__":
    unittest.main()
