"""Tests for simulator mock HAL implementations."""
import pytest
from edge.simulator.mocks import (
    SimulatorFileSystem,
    SimulatorHttpClient,
    SimulatorNetwork,
    SimulatorSystem,
    SimulatorWatchdog,
)


class TestSimulatorSystem:
    def test_unique_id_returns_string(self):
        system = SimulatorSystem()
        device_id = system.unique_id()
        assert isinstance(device_id, str)
        assert len(device_id) > 0

    def test_unique_id_consistent(self):
        system = SimulatorSystem(device_id="test-device-123")
        assert system.unique_id() == "test-device-123"

    def test_time_ms_returns_positive_int(self):
        system = SimulatorSystem()
        time_ms = system.time_ms()
        assert isinstance(time_ms, int)
        assert time_ms > 0

    def test_time_ms_increases(self):
        system = SimulatorSystem()
        time1 = system.time_ms()
        time2 = system.time_ms()
        assert time2 >= time1

    def test_uptime_ms_starts_low(self):
        system = SimulatorSystem()
        uptime = system.uptime_ms()
        assert isinstance(uptime, int)
        assert uptime >= 0

    def test_free_memory_bytes_returns_positive(self):
        system = SimulatorSystem()
        memory = system.free_memory_bytes()
        assert isinstance(memory, int)
        assert memory > 0

    def test_sleep_ms_completes(self):
        system = SimulatorSystem()
        # Sleep for 10ms, should complete without error
        system.sleep_ms(10)

    def test_sync_time_returns_true(self):
        system = SimulatorSystem()
        result = system.sync_time()
        assert result is True

    def test_reset_raises_error(self):
        system = SimulatorSystem()
        with pytest.raises(RuntimeError):
            system.reset()


class TestSimulatorNetwork:
    def test_connect_succeeds(self):
        network = SimulatorNetwork()
        network.connect("TestSSID", "password")

    def test_is_connected_true_by_default(self):
        network = SimulatorNetwork()
        assert network.is_connected() is True

    def test_get_ip_returns_string(self):
        network = SimulatorNetwork()
        ip = network.get_ip()
        assert isinstance(ip, str)
        assert len(ip) > 0

    def test_set_power_save_noops(self):
        network = SimulatorNetwork()
        # Should not raise
        network.set_power_save("modem")

    def test_interface_active_noops(self):
        network = SimulatorNetwork()
        # Should not raise
        network.interface_active(True)
        network.interface_active(False)


class TestSimulatorWatchdog:
    def test_init_sets_timeout(self):
        watchdog = SimulatorWatchdog()
        watchdog.init(30000)
        assert watchdog._timeout_ms == 30000

    def test_feed_increments_counter(self):
        watchdog = SimulatorWatchdog()
        assert watchdog._feed_count == 0
        watchdog.feed()
        assert watchdog._feed_count == 1
        watchdog.feed()
        assert watchdog._feed_count == 2


class TestSimulatorFileSystem:
    def test_write_and_read_text(self, tmp_path):
        fs = SimulatorFileSystem()
        test_file = tmp_path / "test.txt"
        content = "Hello, simulator!"

        fs.write_text(str(test_file), content)
        assert fs.read_text(str(test_file)) == content

    def test_write_and_read_bytes(self, tmp_path):
        fs = SimulatorFileSystem()
        test_file = tmp_path / "test.bin"
        content = b"Binary content"

        fs.write_bytes(str(test_file), content)
        assert fs.read_bytes(str(test_file)) == content

    def test_exists(self, tmp_path):
        fs = SimulatorFileSystem()
        test_file = tmp_path / "test.txt"

        assert not fs.exists(str(test_file))
        fs.write_text(str(test_file), "content")
        assert fs.exists(str(test_file))

    def test_is_dir(self, tmp_path):
        fs = SimulatorFileSystem()
        test_dir = tmp_path / "testdir"
        test_file = tmp_path / "testfile.txt"

        fs.mkdir(str(test_dir))
        fs.write_text(str(test_file), "content")

        assert fs.is_dir(str(test_dir))
        assert not fs.is_dir(str(test_file))

    def test_mkdir(self, tmp_path):
        fs = SimulatorFileSystem()
        test_dir = tmp_path / "newdir"

        fs.mkdir(str(test_dir))
        assert test_dir.exists()

    def test_makedirs(self, tmp_path):
        fs = SimulatorFileSystem()
        test_dir = tmp_path / "parent" / "child" / "grandchild"

        fs.makedirs(str(test_dir))
        assert test_dir.exists()

    def test_remove(self, tmp_path):
        fs = SimulatorFileSystem()
        test_file = tmp_path / "test.txt"
        fs.write_text(str(test_file), "content")

        assert fs.exists(str(test_file))
        fs.remove(str(test_file))
        assert not fs.exists(str(test_file))

    def test_listdir(self, tmp_path):
        fs = SimulatorFileSystem()
        fs.write_text(str(tmp_path / "file1.txt"), "content1")
        fs.write_text(str(tmp_path / "file2.txt"), "content2")

        files = fs.listdir(str(tmp_path))
        assert "file1.txt" in files
        assert "file2.txt" in files

    def test_rename(self, tmp_path):
        fs = SimulatorFileSystem()
        src = tmp_path / "original.txt"
        dst = tmp_path / "renamed.txt"
        fs.write_text(str(src), "content")

        fs.rename(str(src), str(dst))
        assert not fs.exists(str(src))
        assert fs.exists(str(dst))

    def test_write_chunks(self, tmp_path):
        fs = SimulatorFileSystem()
        test_file = tmp_path / "chunks.bin"
        chunks = [b"Hello, ", b"simulator", b"!"]

        fs.write_chunks(str(test_file), chunks)
        assert fs.read_bytes(str(test_file)) == b"Hello, simulator!"


class TestSimulatorHttpClient:
    def test_http_client_instantiates(self):
        """Test that HTTP client can be instantiated."""
        client = SimulatorHttpClient()
        assert client is not None

    def test_streaming_response_wrapper(self):
        """Test streaming response wrapper."""
        from unittest.mock import MagicMock
        
        # Create a mock response object with an iterator
        mock_response = MagicMock()
        mock_response.iter_content.return_value = iter([b"chunk1", b"chunk2"])
        
        from edge.simulator.mocks.mock_http_client import StreamingResponseWrapper
        wrapper = StreamingResponseWrapper(mock_response)
        
        # Read first chunk
        chunk1 = wrapper.read(1024)
        assert chunk1 == b"chunk1"
        
        # Read second chunk
        chunk2 = wrapper.read(1024)
        assert chunk2 == b"chunk2"
        
        # Close should not raise
        wrapper.close()
