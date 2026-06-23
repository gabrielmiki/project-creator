from __future__ import annotations

from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from forge.domain import DurationEstimate
from forge.domain.project_spec import ProjectSpec
from forge.generation.orchestrator import GenerationResult, Orchestrator
from forge.infrastructure.transaction import GenerationTransaction


class QtProgressReporter(QObject):
    stage_started = Signal(str, int)
    step_completed = Signal(str)
    stage_completed = Signal(str)
    log_message = Signal(str, str)
    error_occurred = Signal(str, bool)
    duration_estimated = Signal(DurationEstimate)

    def __init__(self) -> None:
        super().__init__()
        self._cancelled = Event()

    def on_stage_start(self, stage_name: str, total_steps: int) -> None:
        self.stage_started.emit(stage_name, total_steps)

    def on_step_complete(self, step_name: str) -> None:
        self.step_completed.emit(step_name)

    def on_stage_complete(self, stage_name: str) -> None:
        self.stage_completed.emit(stage_name)

    def on_log(self, message: str, level: str = "info") -> None:
        self.log_message.emit(message, level)

    def on_error(self, error: Exception, recoverable: bool) -> None:
        self.error_occurred.emit(str(error), recoverable)

    def on_duration_estimate(self, estimate: DurationEstimate) -> None:
        self.duration_estimated.emit(estimate)

    def should_cancel(self) -> bool:
        return self._cancelled.is_set()

    def set_cancelled(self) -> None:
        self._cancelled.set()


class GenerationWorker(QObject):
    finished = Signal(GenerationResult)
    progress = Signal(str, int)
    log = Signal(str, str)
    error = Signal(str)

    def __init__(
        self,
        orchestrator: Orchestrator,
        spec: ProjectSpec,
        output_dir: Path,
        txn: GenerationTransaction | None = None,
        progress: QtProgressReporter | None = None,
    ) -> None:
        super().__init__()
        self._orchestrator = orchestrator
        self._spec = spec
        self._output_dir = output_dir
        self._txn = txn
        self._reporter = progress if progress is not None else self._create_progress()
        self._finished = False

    @Slot()
    def run(self) -> None:
        if self._reporter.should_cancel():
            return

        try:
            txn = self._txn if self._txn is not None else GenerationTransaction(self._output_dir)
            result = self._orchestrator.generate(
                self._spec,
                self._output_dir,
                txn,
                self._reporter,
            )
        except Exception as e:
            txn.rollback()
            result = GenerationResult(False, str(e), None)

        self._finished = True
        self.finished.emit(result)

    def cancel(self) -> None:
        if self._finished:
            return
        self._reporter.set_cancelled()

    def _create_progress(self) -> QtProgressReporter:
        return QtProgressReporter()
