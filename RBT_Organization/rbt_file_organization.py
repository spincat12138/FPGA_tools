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
    parser.add_argument(
        "--export-bit",
        action="store_true",
        help="同时整理 .bit 文件到源目录下的 bit 子目录",
    )
    args = parser.parse_args(argv)

    result = copy_and_rename_rbt_files(
        args.source_directory,
        args.target_subdir,
        export_bit=args.export_bit,
    )
    for record in result.copied_files:
        print("已复制: {source} -> {destination}".format(
            source=record.source,
            destination=record.destination,
        ))
    message = "整理完成，共复制 {count} 个 rbt 文件。输出目录：{target}".format(
        count=result.rbt_copied_count,
        target=result.target_dir,
    )
    if result.bit_target_dir is not None:
        message = "{message}；同时复制 {count} 个 bit 文件。输出目录：{target}".format(
            message=message,
            count=result.bit_copied_count,
            target=result.bit_target_dir,
        )
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
