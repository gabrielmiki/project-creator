from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir()
    return d


class TestIntegration_Commit:
    def test_staged_content_appears_in_output_dir(self, output_dir: Path, txn) -> None:
        txn.stage_file("f.txt", "hello")
        txn.stage_directory("sub")
        txn.stage_file("sub/g.txt", "nested")
        txn.commit()
        assert (output_dir / "f.txt").read_text() == "hello"
        assert (output_dir / "sub/g.txt").read_text() == "nested"
        assert not txn.staging.exists()


class TestIntegration_Rollback:
    def test_staging_removed_output_unchanged(self, output_dir: Path, txn) -> None:
        (output_dir / "pre_existing.txt").write_text("keep me")
        txn.stage_file("f.txt", "lost")
        txn.rollback()
        assert not txn.staging.exists()
        assert (output_dir / "pre_existing.txt").read_text() == "keep me"
        assert not (output_dir / "f.txt").exists()


class TestIntegration_Checkpoint:
    def test_file_checkpoint_deleted_on_rollback(self, output_dir: Path, txn) -> None:
        cp = output_dir / "generated.txt"
        cp.write_text("scaffold output")
        txn.add_checkpoint([cp])
        txn.rollback()
        assert not cp.exists()

    def test_directory_checkpoint_deleted_recursively_on_rollback(
        self, output_dir: Path, txn
    ) -> None:
        cp_dir = output_dir / "scaffold_output"
        cp_dir.mkdir()
        (cp_dir / "inner.txt").write_text("nested")
        (cp_dir / "sub").mkdir()
        (cp_dir / "sub" / "deep.txt").write_text("deep")
        txn.add_checkpoint([cp_dir])
        txn.rollback()
        assert not cp_dir.exists()

    def test_external_file_checkpoint_deleted_on_rollback(
        self, output_dir: Path, txn
    ) -> None:
        external = output_dir.parent / "external_generated.txt"
        external.write_text("scaffold output outside staging")
        txn.add_checkpoint([external])
        txn.rollback()
        assert not external.exists()


class TestIntegration_NoopCommit:
    def test_commit_with_zero_staged_files_succeeds(
        self, output_dir: Path
    ) -> None:
        from forge.infrastructure.transaction import GenerationTransaction

        txn = GenerationTransaction(output_dir)
        txn.commit()
        assert not (output_dir / ".forge-staging").exists()


class TestIntegration_ContextManager:
    def test_context_manager_commits_on_normal_exit(
        self, output_dir: Path
    ) -> None:
        from forge.infrastructure.transaction import GenerationTransaction

        with GenerationTransaction(output_dir) as cm:
            cm.stage_file("f.txt", "content")
        assert (output_dir / "f.txt").read_text() == "content"
        assert not (output_dir / ".forge-staging").exists()

    def test_context_manager_rolls_back_on_exception(
        self, output_dir: Path
    ) -> None:
        from forge.infrastructure.transaction import GenerationTransaction

        (output_dir / "keep.txt").write_text("keep")
        with pytest.raises(RuntimeError, match="fail"):
            with GenerationTransaction(output_dir) as cm:
                cm.stage_file("lost.txt", "gone")
                raise RuntimeError("fail")
        assert not (output_dir / ".forge-staging").exists()
        assert not (output_dir / "lost.txt").exists()
        assert (output_dir / "keep.txt").read_text() == "keep"
