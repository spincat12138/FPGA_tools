# -*- coding: utf-8 -*-
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple


@dataclass(frozen=True)
class RbtCopyRecord:
    source: Path
    destination: Path
    file_type: str = "rbt"


@dataclass(frozen=True)
class RbtOrganizationResult:
    source_root: Path
    target_dir: Path
    bit_target_dir: Optional[Path]
    copied_files: Tuple[RbtCopyRecord, ...]

    @property
    def copied_count(self):
        return len(self.copied_files)

    @property
    def rbt_copied_count(self):
        return sum(1 for record in self.copied_files if record.file_type == "rbt")

    @property
    def bit_copied_count(self):
        return sum(1 for record in self.copied_files if record.file_type == "bit")


ProgressCallback = Callable[[int, int, RbtCopyRecord], None]


def copy_and_rename_rbt_files(
    source_root,
    target_subdir="rbt",
    export_bit=False,
    bit_target_subdir="bit",
    progress_callback=None,
):
    """Copy .rbt files and optional .bit files under source_root into output subdirs."""
    source_path = _validate_source_root(source_root)
    target_name = _validate_target_subdir(target_subdir)
    target_dir = source_path / target_name
    target_dir.mkdir(parents=True, exist_ok=True)
    bit_target_dir = None
    if export_bit:
        bit_target_name = _validate_target_subdir(bit_target_subdir)
        bit_target_dir = source_path / bit_target_name
        bit_target_dir.mkdir(parents=True, exist_ok=True)

    skipped_dirs = (target_dir, bit_target_dir)
    copy_tasks = [
        (src_path, target_dir, "rbt")
        for src_path in _iter_files(source_path, skipped_dirs, ".rbt")
    ]
    if bit_target_dir is not None:
        copy_tasks.extend(
            (src_path, bit_target_dir, "bit")
            for src_path in _iter_files(source_path, skipped_dirs, ".bit")
        )

    _validate_copy_destinations(source_path, copy_tasks)

    copied_records = []
    total = len(copy_tasks)
    for index, (src_path, output_dir, file_type) in enumerate(copy_tasks, start=1):
        dest_path = output_dir / _destination_filename(source_path, src_path, file_type)
        shutil.copy2(str(src_path), str(dest_path))
        record = RbtCopyRecord(
            source=src_path,
            destination=dest_path,
            file_type=file_type,
        )
        copied_records.append(record)
        if progress_callback is not None:
            progress_callback(index, total, record)

    return RbtOrganizationResult(
        source_root=source_path,
        target_dir=target_dir,
        bit_target_dir=bit_target_dir,
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


def _iter_files(source_root, skipped_dirs, suffix):
    skipped_resolved = {
        target_dir.resolve()
        for target_dir in skipped_dirs
        if target_dir is not None
    }
    for root, dirnames, filenames in os.walk(str(source_root)):
        root_path = Path(root)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if (root_path / dirname).resolve() not in skipped_resolved
        ]

        for filename in filenames:
            if filename.lower().endswith(suffix):
                yield (root_path / filename).resolve()


def _validate_copy_destinations(source_root, copy_tasks):
    destinations = {}
    for src_path, output_dir, file_type in copy_tasks:
        dest_path = output_dir / _destination_filename(source_root, src_path, file_type)
        key = os.path.normcase(str(dest_path.resolve()))
        destinations.setdefault(key, []).append((src_path, dest_path))

    conflicts = []
    for records in destinations.values():
        dest_path = records[0][1]
        if len(records) > 1:
            sources = "；".join(str(src_path) for src_path, _ in records)
            conflicts.append(
                "目标 {destination} 对应多个源文件：{sources}".format(
                    destination=dest_path,
                    sources=sources,
                )
            )
        elif dest_path.exists():
            conflicts.append(
                "目标文件已存在：{destination}，源文件：{source}".format(
                    destination=dest_path,
                    source=records[0][0],
                )
            )

    if conflicts:
        raise FileExistsError(
            "检测到输出文件名冲突，已停止整理以避免覆盖。\n{details}".format(
                details="\n".join(conflicts)
            )
        )


def _destination_filename(source_root, src_path, file_type):
    relative_parts = src_path.relative_to(source_root).parts
    if len(relative_parts) == 1:
        base_name = src_path.stem
    else:
        base_name = relative_parts[0]
    return "{base_name}.{file_type}".format(base_name=base_name, file_type=file_type)
