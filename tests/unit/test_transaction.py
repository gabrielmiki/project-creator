from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir()
    return d


@pytest.fixture
def txn(output_dir: Path):
    from forge.infrastructure.transaction import GenerationTransaction

    return GenerationTransaction(output_dir)


class TestAC1_Constructor:
    def test_staging_path_and_manifest(self, output_dir: Path) -> None:
        from forge.infrastructure.transaction import GenerationTransaction

        txn = GenerationTransaction(output_dir)
        assert txn.staging == output_dir / ".forge-staging"
        assert txn.manifest == []


class TestAC2_StageFile:
    def test_returns_path_and_writes_content(self, txn) -> None:
        result = txn.stage_file("src/main.py", "print('hello')")
        expected = txn.staging / "src/main.py"
        assert result == expected
        assert expected.read_text() == "print('hello')"

    def test_overwrite_existing_staged_file(self, txn) -> None:
        txn.stage_file("f.txt", "v1")
        txn.stage_file("f.txt", "v2")
        assert (txn.staging / "f.txt").read_text() == "v2"


class TestAC3_StageDirectory:
    def test_creates_directory(self, txn) -> None:
        result = txn.stage_directory("mydir")
        assert result == txn.staging / "mydir"
        assert result.is_dir()

    def test_creates_intermediate_parents(self, txn) -> None:
        result = txn.stage_directory("a/b/c/d")
        assert result == txn.staging / "a/b/c/d"
        assert result.is_dir()
        assert (txn.staging / "a/b/c").is_dir()


class TestAC4_Commit:
    def test_staged_content_moves_to_output_dir(self, output_dir: Path, txn) -> None:
        txn.stage_file("f.txt", "hello")
        txn.stage_directory("sub")
        txn.stage_file("sub/g.txt", "world")
        txn.commit()
        assert (output_dir / "f.txt").read_text() == "hello"
        assert (output_dir / "sub/g.txt").read_text() == "world"
        assert not txn.staging.exists()


class TestAC5_Rollback:
    def test_staging_removed_output_unchanged(self, output_dir: Path, txn) -> None:
        (output_dir / "pre_existing.txt").write_text("keep me")
        txn.stage_file("f.txt", "lost")
        txn.rollback()
        assert not txn.staging.exists()
        assert (output_dir / "pre_existing.txt").read_text() == "keep me"
        assert not (output_dir / "f.txt").exists()


class TestAC6_CheckpointFile:
    def test_checkpoint_path_deleted_on_rollback(self, output_dir: Path, txn) -> None:
        cp = output_dir / "generated.txt"
        cp.write_text("scaffold output")
        txn.add_checkpoint([cp])
        txn.rollback()
        assert not cp.exists()


class TestAC7_CheckpointCumulative:
    def test_checkpoints_accumulate(self, output_dir: Path, txn) -> None:
        p1 = output_dir / "f1.txt"
        p1.write_text("a")
        p2 = output_dir / "f2.txt"
        p2.write_text("b")
        txn.add_checkpoint([p1])
        txn.add_checkpoint([p2])
        txn.rollback()
        assert not p1.exists()
        assert not p2.exists()


class TestAC8_ContextManagerSuccess:
    def test_commit_on_normal_exit(self, output_dir: Path) -> None:
        from forge.infrastructure.transaction import GenerationTransaction

        with GenerationTransaction(output_dir) as txn:
            txn.stage_file("f.txt", "content")
        assert (output_dir / "f.txt").read_text() == "content"
        assert not (output_dir / ".forge-staging").exists()


class TestAC9_ContextManagerException:
    def test_rollback_and_re_raise_on_exception(self, output_dir: Path) -> None:
        from forge.infrastructure.transaction import GenerationTransaction

        (output_dir / "keep.txt").write_text("keep")
        with pytest.raises(RuntimeError, match="fail"):
            with GenerationTransaction(output_dir) as txn:
                txn.stage_file("lost.txt", "gone")
                raise RuntimeError("fail")
        assert not (output_dir / ".forge-staging").exists()
        assert not (output_dir / "lost.txt").exists()
        assert (output_dir / "keep.txt").read_text() == "keep"


class TestAC10_CommitCollision:
    def test_raises_file_exists_error_and_preserves_staging(
        self, output_dir: Path, txn
    ) -> None:
        (output_dir / "collide.txt").write_text("original")
        txn.stage_file("collide.txt", "new")
        with pytest.raises(FileExistsError):
            txn.commit()
        assert txn.staging.exists()
        assert (output_dir / "collide.txt").read_text() == "original"
        txn.rollback()
        assert not txn.staging.exists()


class TestAC4a_NestedDirectoryCommit:
    def test_nested_dir_without_explicit_parent(self, output_dir: Path, txn) -> None:
        txn.stage_directory("a/b")
        txn.stage_file("a/b/c.txt", "nested content")
        txn.commit()
        assert (output_dir / "a/b/c.txt").read_text() == "nested content"
        assert not txn.staging.exists()


class TestAC11_DoubleCommit:
    def test_raises_runtime_error(self, txn) -> None:
        txn.stage_file("f.txt", "ok")
        txn.commit()
        with pytest.raises(RuntimeError, match="already committed|commit"):
            txn.commit()


class TestAC12_RollbackNoOp:
    def test_no_error_when_nothing_exists(self, tmp_path: Path) -> None:
        from forge.infrastructure.transaction import GenerationTransaction

        txn = GenerationTransaction(tmp_path / "nonexistent")
        txn.rollback()
