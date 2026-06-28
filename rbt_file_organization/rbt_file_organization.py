# -*- coding: utf-8 -*-
import argparse
import sys

try:
    from .core import copy_and_rename_rbt_files
except ImportError:
    from core import copy_and_rename_rbt_files


def main(argv=None):
    parser = argparse.ArgumentParser(description="整理指定目录下的 rbt 文件")
    parser.add_argument("source_directory", help="要整理的目录")
    parser.add_argument(
        "--target-subdir",
        default="rbt",
        help="输出到源目录下的子目录名，默认 rbt",
    )
    args = parser.parse_args(argv)

    result = copy_and_rename_rbt_files(args.source_directory, args.target_subdir)
    for record in result.copied_files:
        action = "已覆盖" if record.overwritten else "已复制"
        print("{action}: {source} -> {destination}".format(
            action=action,
            source=record.source,
            destination=record.destination,
        ))
    print("整理完成，共复制 {count} 个 rbt 文件。输出目录：{target}".format(
        count=result.copied_count,
        target=result.target_dir,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
