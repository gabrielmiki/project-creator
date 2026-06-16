from typing import Protocol, runtime_checkable

from forge.domain import DurationEstimate
from forge.infrastructure import GenerationTransaction as _  # noqa: F401


@runtime_checkable
class ProgressReporter(Protocol):
    def on_stage_start(self, stage_name: str, total_steps: int) -> None: ...
    def on_step_complete(self, step_name: str) -> None: ...
    def on_stage_complete(self, stage_name: str) -> None: ...
    def on_log(self, message: str, level: str = "info") -> None: ...
    def on_error(self, error: Exception, recoverable: bool) -> None: ...
    def on_duration_estimate(self, estimate: DurationEstimate) -> None: ...
    def should_cancel(self) -> bool: ...


class StdoutProgressReporter:
    def on_stage_start(self, stage_name: str, total_steps: int) -> None:
        print(f"[{stage_name}] Starting: {total_steps} step{'s' if total_steps != 1 else ''}")

    def on_step_complete(self, step_name: str) -> None:
        print(f"  \u2713 {step_name}")

    def on_stage_complete(self, stage_name: str) -> None:
        print(f"[{stage_name}] Complete")

    def on_log(self, message: str, level: str = "info") -> None:
        print(f"[{level}]: {message}")

    def on_error(self, error: Exception, recoverable: bool) -> None:
        label = "recoverable" if recoverable else "fatal"
        print(f"[ERROR] {error} ({label})")

    def on_duration_estimate(self, estimate: DurationEstimate) -> None:
        print(f"Estimated duration: {estimate.estimated_seconds}s")

    def should_cancel(self) -> bool:
        return False


class MockProgressReporter:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def on_stage_start(self, stage_name: str, total_steps: int) -> None:
        self.calls.append(("on_stage_start", stage_name, total_steps))

    def on_step_complete(self, step_name: str) -> None:
        self.calls.append(("on_step_complete", step_name))

    def on_stage_complete(self, stage_name: str) -> None:
        self.calls.append(("on_stage_complete", stage_name))

    def on_log(self, message: str, level: str = "info") -> None:
        self.calls.append(("on_log", message, level))

    def on_error(self, error: Exception, recoverable: bool) -> None:
        self.calls.append(("on_error", error, recoverable))

    def on_duration_estimate(self, estimate: DurationEstimate) -> None:
        self.calls.append(("on_duration_estimate", estimate))

    def should_cancel(self) -> bool:
        self.calls.append(("should_cancel",))
        return False
