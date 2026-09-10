from pathlib import Path
import tempfile

import pytest

from tools.code_kernel import SessionKernel, _bind_rpc_socket


@pytest.mark.macos_only
def test_session_kernel_binds_to_configured_short_directory(monkeypatch):
    with tempfile.TemporaryDirectory(prefix='hm-', dir='/tmp') as directory:
        monkeypatch.setenv('HERMES_SHORT_TMPDIR', directory)
        kernel = SessionKernel(('migration-test',))
        try:
            endpoint = _bind_rpc_socket(kernel)
            assert Path(endpoint).parent == Path(directory)
            assert Path(endpoint).is_socket()
        finally:
            if kernel.server_sock:
                kernel.server_sock.close()
            if kernel.sock_path:
                Path(kernel.sock_path).unlink(missing_ok=True)
