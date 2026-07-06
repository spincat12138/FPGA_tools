import argparse
import os
import struct
import sys


BIT_PREAMBLE = b'\x0f\xf0\x0f\xf0\x0f\xf0\x0f\xf0\x00'
BIT_SYNC_WORD = b'\xaa\x99\x55\x66'
BIT_METADATA_KEYS = {
    b'a': 'design',
    b'b': 'part',
    b'c': 'date',
    b'd': 'time',
}

def _emit(logger, message):
    if logger is not None:
        logger(message)


def extract_bit_file_info(data, logger=print):
    """
    从标准 Xilinx BIT 文件中提取设计信息和配置 payload。
    """
    metadata = {
        'design': 'unknown',
        'part': 'unknown',
        'date': 'unknown',
        'time': 'unknown',
        'bit_len': 0,
        'data_start': 0,
        'payload': b'',
    }

    if len(data) < 13:
        raise ValueError("BIT文件过短，无法解析文件头")

    preamble_length = struct.unpack('>H', data[:2])[0]
    preamble_start = 2
    preamble_end = preamble_start + preamble_length
    if data[preamble_start:preamble_end] != BIT_PREAMBLE:
        raise ValueError("未找到标准Xilinx BIT文件固定头")

    if data[preamble_end:preamble_end + 2] != b'\x00\x01':
        raise ValueError("BIT文件固定头后的字段标记不完整")

    index = preamble_end + 2
    if index > len(data):
        raise ValueError("BIT文件头不完整")

    while index < len(data):
        key = data[index:index + 1]
        index += 1

        if key in BIT_METADATA_KEYS:
            if index + 2 > len(data):
                raise ValueError("BIT文件元数据字段长度不完整")
            length = struct.unpack('>H', data[index:index + 2])[0]
            index += 2
            value_end = index + length
            if value_end > len(data):
                raise ValueError("BIT文件元数据字段内容不完整")
            value = data[index:value_end].decode('ascii', errors='replace').strip('\x00')
            metadata[BIT_METADATA_KEYS[key]] = value
            index = value_end
            continue

        if key == b'e':
            if index + 4 > len(data):
                raise ValueError("BIT文件payload长度字段不完整")
            bit_len = struct.unpack('>I', data[index:index + 4])[0]
            data_start = index + 4
            data_end = data_start + bit_len
            if data_end > len(data):
                raise ValueError("BIT文件payload长度超过文件大小")
            payload = data[data_start:data_end]
            if BIT_SYNC_WORD not in payload:
                raise ValueError("BIT文件payload中未找到同步字AA995566")
            metadata['bit_len'] = bit_len
            metadata['data_start'] = data_start
            metadata['payload'] = payload
            return metadata

        raise ValueError("遇到未知BIT文件字段：0x{value:02X}".format(value=key[0]))

    raise ValueError("BIT文件中未找到payload字段")


def bit2rbt(bit_file_path, rbt_file_path=None, rename=False, logger=print):
    """
    BIT文件转RBT文件，并从标准Xilinx BIT容器中恢复设计信息。
    """
    if rbt_file_path is not None:
        rbt_file_path = os.fspath(rbt_file_path)
    elif rename:
        rbt_file_path = os.path.join(os.path.split(bit_file_path)[0], "No" + os.path.splitext(os.path.basename(bit_file_path))[0]+ ".rbt")
    else:
        rbt_file_path = os.path.splitext(bit_file_path)[0] + ".rbt"
    
    _emit(logger, "=====================BIT文件转RBT文件 开始=====================")
    
    if not os.path.exists(bit_file_path):
        raise FileNotFoundError("找不到指定的BIT文件：{path}".format(path=bit_file_path))
        
    with open(bit_file_path, 'rb') as f_bit:
        bit_data = f_bit.read()
        
    _emit(logger, "已读取BIT文件，大小：{bit_data_length} 字节".format(bit_data_length=len(bit_data)))

    info = extract_bit_file_info(bit_data, logger=logger)
    bit_payload = info['payload']
    sync_index = bit_payload.find(BIT_SYNC_WORD)
    _emit(logger, "找到同步字，payload内偏移量:{sync_index}".format(sync_index=sync_index))
    _emit(logger, "配置payload大小：{payload_length} 字节".format(payload_length=len(bit_payload)))

    rbt_header = [
        "Xilinx ASCII Bitstream\n",
        "Created by BIT2RBT.py\n",
        "Design: {design}\n".format(design=info['design']),
        "Part: {part}\n".format(part=info['part']),
        "Date: {date}\n".format(date=info['date']),
        "Time: {time}\n".format(time=info['time']),
        "Bits: {bit_data_length}\n".format(bit_data_length=len(bit_payload)*8)
    ]

    output_dir = os.path.dirname(os.path.abspath(rbt_file_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(rbt_file_path, 'w') as f_rbt:
        f_rbt.writelines(rbt_header)

        # 将二进制数据每4个字节转为一行32位的'0/1'字符串
        count = 0
        for i in range(0, len(bit_payload), 4):
            chunk = bit_payload[i:i+4]
            if len(chunk) < 4:
                chunk = chunk.ljust(4, b'\x00')

            val = int.from_bytes(chunk, byteorder='big')
            bin_str = format(val, '032b')

            f_rbt.write(bin_str + "\n")
            count += 1

    _emit(logger, "转换完成！已生成RBT文件：{rbt_file_path}".format(rbt_file_path=rbt_file_path))
    _emit(logger, "共写入 {count} 行数据".format(count=count))
    _emit(logger, "=====================BIT文件转RBT文件 结束=====================")
    return rbt_file_path

def main(argv=None):
    parser = argparse.ArgumentParser(description="将 BIT 文件转换为 RBT 文件")
    parser.add_argument("bit_file", nargs="+", help="输入 BIT 文件路径，可传多个")
    parser.add_argument(
        "-o",
        "--output",
        help="输出 RBT 文件路径。仅转换单个文件时可用，默认生成 <原文件名>.rbt",
    )
    parser.add_argument(
        "--rename",
        action="store_true",
        help="未指定输出路径时，生成 No<原文件名>.rbt",
    )
    args = parser.parse_args(argv)

    if args.output and len(args.bit_file) != 1:
        parser.error("--output 只能在转换单个文件时使用")

    for bit_file in args.bit_file:
        bit2rbt(bit_file, rbt_file_path=args.output, rename=args.rename)
    return 0


if __name__ == "__main__":
    sys.exit(main())
