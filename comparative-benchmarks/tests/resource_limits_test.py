from src.subprocess_runner import ResourceLimits, SubprocessRunner


def test_resource_limits_structure() -> None:
    limits = ResourceLimits()
    assert limits.max_memory_mb is None
    assert limits.max_cpu_percent is None
    assert limits.max_open_files is None
    assert limits.max_execution_time is None

    limits = ResourceLimits(max_memory_mb=512, max_cpu_percent=80.0, max_open_files=100, max_execution_time=60.0)
    assert limits.max_memory_mb == 512
    assert limits.max_cpu_percent == 80.0
    assert limits.max_open_files == 100
    assert limits.max_execution_time == 60.0


def test_subprocess_runner_with_resource_limits() -> None:
    limits = ResourceLimits(max_memory_mb=256, max_open_files=50)
    runner = SubprocessRunner(timeout=60.0, resource_limits=limits)

    assert runner.resource_limits.max_memory_mb == 256
    assert runner.resource_limits.max_open_files == 50
    assert runner.resource_limits.max_cpu_percent is None


def test_subprocess_runner_default_resource_limits() -> None:
    runner = SubprocessRunner(timeout=60.0)

    assert runner.resource_limits.max_memory_mb is None
    assert runner.resource_limits.max_cpu_percent is None
    assert runner.resource_limits.max_open_files is None


def test_resource_limits_serialization() -> None:
    import msgspec

    limits = ResourceLimits(max_memory_mb=512, max_open_files=100)

    encoded = msgspec.json.encode(limits)
    assert isinstance(encoded, bytes)

    decoded = msgspec.json.decode(encoded, type=ResourceLimits)
    assert decoded.max_memory_mb == 512
    assert decoded.max_open_files == 100
    assert decoded.max_cpu_percent is None
