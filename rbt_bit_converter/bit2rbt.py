import argparse
import os
import struct
import sys

def _emit(logger, message):
    if logger is not None:
        logger(message)


def extract_metadata(data, logger=print):
    """
    从BIT二进制中数据中提取设计信息
    """
    metadata = {
        'design': 'unknown',
        'part': 'unknown',
        'date': 'unknown',
        'time': 'unknown',
        'bit_len': 0,
        'data_start': 0
    }

    try:
        # 跳过开头的固定字节
        fix_header = b'\x00\x09\x0f\xf0\x0f\xf0\x0f\xf0\x0f\xf0\x00\x00\x01'
        idx = data.find(fix_header[:200])
        if idx == -1:
            _emit(logger, "未找到标准的BIT文件固定头！")
            return metadata

        # 寻找标记 'a'(0x61)
        idx = data.find(b'a')
        if idx == -1: return metadata

        # 提取字段 'a' (Design Name)
        # 格式：'a' + 2字节长度 + 字符串
        length = struct.unpack('>H', data[idx+1:idx+3])[0]
        metadata['design'] = data[idx+3:idx+3+length].decode('ascii').strip('\x00')
        idx += 3 + length

        if data[idx:idx+1] == b'b':
            length = struct.unpack('>H', data[idx + 1:idx + 3])[0]
            metadata['part'] = data[idx + 3:idx + 3 + length].decode('ascii').strip('\x00')
            idx += 3 + length

        if data[idx:idx+1] == b'c':
            length = struct.unpack('>H', data[idx + 1:idx + 3])[0]
            metadata['date'] = data[idx + 3:idx + 3 + length].decode('ascii').strip('\x00')
            idx += 3 + length

        if data[idx:idx+1] == b'd':
            length = struct.unpack('>H', data[idx + 1:idx + 3])[0]
            metadata['time'] = data[idx + 3:idx + 3 + length].decode('ascii').strip('\x00')
            idx += 3 + length

        if data[idx:idx+1] == b'e':
            metadata['bit_len'] = struct.unpack('>I', data[idx + 1:idx + 5])[0]
            metadata['data_start'] = idx + 5


    except Exception as e:
        _emit(logger, "解析头部信息时出错:{error}".format(error=e))

    return metadata


def bit2rbt(bit_file_path, rbt_file_path=None, rename=False, logger=print):
    """
    BIT文件转RBT文件，并且恢复文件头信息
    目前只测试了V2系列，其他系列已知的需要改动同步标志FF的数量
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

    info = extract_metadata(bit_data, logger=logger)

    sync_pattern = b'\xff\xff\xff\xff\xaa\x99\x55\x66'
    start_index = bit_data.find(sync_pattern)

    if start_index == -1:
        _emit(logger, "未找到同步字，使用Header后默认位置")
        bit_payload = bit_data[info["data_start"]:]
    else:
        _emit(logger, "找到同步字，偏移量:{start_index}".format(start_index=start_index))
        bit_payload = bit_data[start_index:]

    rbt_header = [
        "Xilinx ASCII Bitstream\n",
        "Created by BIT2RBT.py\n",
        "Design: {design}\n".format(design=info['design']),
        "Part: {part}\n".format(part=info['part']),
        "Date: {date}\n".format(date=info['date']),
        "Time: {time}\n".format(time=info['time']),
        "Bits: {bit_data_length}\n".format(bit_data_length=len(bit_data)*8)
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

def find_bit_files(folder_path):
    """
    查找指定文件夹中所有的.bit文件
    :param folder_path: 要搜索的文件夹路径
    :return: 包含所有.bit文件路径的列表
    """
    bit_files = []
    
    # 遍历文件夹、子文件夹及文件
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            # 检查文件扩展名是否为.bit
            if file.endswith('.bit'):
                # 拼接完整文件路径
                file_path = os.path.join(root, file)
                bit_files.append(file_path)
    
    return bit_files

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
