# -*- coding: utf-8 -*-
import argparse
import sys
from pathlib import Path

try:
    from .core import (
        DEFAULT_OUTPUT,
        builtin_profile_paths,
        generate_text,
        load_builtin_profile,
        load_profile,
        profile_to_json,
        write_ucf,
    )
except ImportError:
    from core import (  # type: ignore
        DEFAULT_OUTPUT,
        builtin_profile_paths,
        generate_text,
        load_builtin_profile,
        load_profile,
        profile_to_json,
        write_ucf,
    )


def generate_ucf(profile="type1", output=DEFAULT_OUTPUT):
    data = _load_profile_arg(profile)
    return write_ucf(data, output)


def main(argv=None):
    parser = argparse.ArgumentParser(description="生成 UCF 约束文件")
    parser.add_argument(
        "--profile",
        default="type1",
        help="内置 profile 名称或 JSON profile 路径，默认 type1",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="输出 UCF 文件路径，默认 constraints.ucf",
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=0,
        help="只预览前 N 行，不写文件",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="列出内置 profile",
    )
    parser.add_argument(
        "--export-profile",
        metavar="PATH",
        help="把当前 profile 导出为 JSON",
    )
    args = parser.parse_args(argv)

    if args.list_profiles:
        for path in builtin_profile_paths():
            print(path.stem)
        return 0

    profile = _load_profile_arg(args.profile)

    if args.export_profile:
        target = Path(args.export_profile)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(profile_to_json(profile) + "\n", encoding="utf-8")
        print("已导出 profile：{path}".format(path=target))
        return 0

    if args.preview:
        print(generate_text(profile, limit=args.preview, include_end_marker=False))
        return 0

    output_path = write_ucf(profile, args.output)
    print("已生成：{path}".format(path=output_path))
    return 0


def _load_profile_arg(value):
    path = Path(value)
    if path.is_file():
        return load_profile(path)
    return load_builtin_profile(value)


if __name__ == "__main__":
    sys.exit(main())
