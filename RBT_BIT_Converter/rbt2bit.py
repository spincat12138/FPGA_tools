# -*- coding: UTF-8 -*-
# 参考 ug570 - Chapter 9 Configuration Details

import argparse
import sys
from pathlib import Path


RBT_HEADER_LINES = 7


def _emit(logger, message):
    if logger is not None:
        logger(message)


def rbt2bit(rbt_file_path, bit_file_path=None, header="", logger=print):
    """Convert a Xilinx ASCII .rbt file to a binary .bit payload file."""
    rbt_path = Path(rbt_file_path)
    if not rbt_path.is_file():
        raise FileNotFoundError("找不到指定的RBT文件：{path}".format(path=rbt_path))

    output_path = Path(bit_file_path) if bit_file_path else rbt_path.with_suffix(".bit")

    _emit(logger, "====================RBT文件转BIT文件 begin====================")
    _emit(logger, "读取RBT文件：{path}".format(path=rbt_path))

    rbt_data = rbt_path.read_text(encoding="ascii", errors="ignore").splitlines()
    bit_data = []

    for line_number, line in enumerate(rbt_data[RBT_HEADER_LINES:], start=RBT_HEADER_LINES + 1):
        bit_line = line.strip()
        if not bit_line:
            continue
        if set(bit_line) - {"0", "1"}:
            raise ValueError(
                "RBT数据行包含非二进制字符：第 {line_number} 行".format(
                    line_number=line_number,
                )
            )

        hex_value = "{value:08X}".format(value=int(bit_line, 2))
        bit_data.append(bytes(bytearray.fromhex(hex_value)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w+b") as bit_file:
        if header:
            bit_file.write(bytes(bytearray.fromhex(header)))
        for chunk in bit_data:
            bit_file.write(chunk)

    _emit(logger, "已生成BIT文件：{path}".format(path=output_path))
    _emit(logger, "共写入 {count} 行数据".format(count=len(bit_data)))
    _emit(logger, "====================RBT文件转BIT文件 end====================")
    return output_path


def main(argv=None):
    parser = argparse.ArgumentParser(description="将 RBT 文件转换为 BIT 文件")
    parser.add_argument("rbt_file", help="输入 RBT 文件路径")
    parser.add_argument("-o", "--output", help="输出 BIT 文件路径，默认与输入同名")
    args = parser.parse_args(argv)

    rbt2bit(args.rbt_file, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
