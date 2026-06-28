# -*- coding: utf-8 -*-
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Tuple


@dataclass(frozen=True)
class RbtCopyRecord:
    source: Path
    destination: Path
    overwritten: bool = False


@dataclass(frozen=True)
class RbtOrganizationResult:
    source_root: Path
    target_dir: Path
    copied_files: Tuple[RbtCopyRecord, ...]

    @property
    def copied_count(self):
        return len(self.copied_files)


ProgressCallback = Callable[[int, int, RbtCopyRecord], None]


def copy_and_rename_rbt_files(
    source_root,
    target_subdir="rbt",
    progress_callback=None,
):
    """Copy .rbt files under source_root into source_root/target_subdir."""
    source_path = _validate_source_root(source_root)
    target_name = _validate_target_subdir(target_subdir)
    target_dir = source_path / target_name
    target_dir.mkdir(parents=True, exist_ok=True)

    rbt_files = list(_iter_rbt_files(source_path, target_dir))
    copied_records = []
    total = len(rbt_files)
    for index, src_path in enumerate(rbt_files, start=1):
        dest_path = target_dir / _destination_filename(source_path, src_path)
        overwritten = dest_path.exists()
        shutil.copy2(str(src_path), str(dest_path))
        record = RbtCopyRecord(
            source=src_path,
            destination=dest_path,
            overwritten=overwritten,
        )
        copied_records.append(record)
        if progress_callback is not None:
            progress_callback(index, total, record)

    return RbtOrganizationResult(
        source_root=source_path,
        target_dir=target_dir,
        copied_files=tuple(copied_records),
    )


def _validate_source_root(source_root):
    if not source_root:
        raise ValueError("请先输入要整理的路径")

    source_path = Path(source_root).expanduser()
    if not source_path.exists():
        raise FileNotFoundError("路径不存在：{path}".format(path=source_path))
    if not source_path.is_dir():
        raise NotADirectoryError("请选择文件夹路径：{path}".format(path=source_path))
    return source_path.resolve()


def _validate_target_subdir(target_subdir):
    target_name = str(target_subdir).strip()
    if not target_name:
        raise ValueError("目标子目录名称不能为空")
    if Path(target_name).name != target_name:
        raise ValueError("目标子目录名称不能包含路径分隔符：{name}".format(name=target_name))
    return target_name


def _iter_rbt_files(source_root, target_dir):
    target_resolved = target_dir.resolve()
    for root, dirnames, filenames in os.walk(str(source_root)):
        root_path = Path(root)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if (root_path / dirname).resolve() != target_resolved
        ]

        for filename in filenames:
            if filename.lower().endswith(".rbt"):
                yield (root_path / filename).resolve()


def _destination_filename(source_root, src_path):
    relative_parts = src_path.relative_to(source_root).parts
    if len(relative_parts) == 1:
        base_name = src_path.stem
    else:
        base_name = relative_parts[0]
    return "{base_name}.rbt".format(base_name=base_name)
