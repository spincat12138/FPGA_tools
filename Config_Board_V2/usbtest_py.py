#!/usr/bin/env python3
"""
Python port of UsbTest.exe.

Requires the FTDI D2XX driver and the Python package:
    pip install ftd2xx

Common commands:
    python usbtest_py.py handshake
    python usbtest_py.py erase 1
    python usbtest_py.py program 1_00.bit
    python usbtest_py.py readback 1 -o readback.bit
    python usbtest_py.py verify 1_00.bit
    python usbtest_py.py verify 1_00.rbt 2_00.txt
    python usbtest_py.py convert fpgatoda.rbt
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


SECTOR_SIZE = 64 * 1024
ADDRESS_MODULO = 16_777_215

HANDSHAKE_CMD = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0, 0, 0, 0])
HANDSHAKE_RESPONSE_TIMEOUT = 30.0
ERASE_HEADER = bytes([0xAA, 0xBB, 0xFF, 0x44])
PROGRAM_HEADER = bytes([0xBB, 0xAA, 0x44, 0xFF])
READBACK_HEADER = bytes([0xFF, 0x44, 0xAA, 0xBB])


@dataclass(frozen=True)
class DeviceProfile:
    name: str
    bit_length: int
    erase_delay_seconds: float


DEVICE_BY_RESPONSE = {
    0xAB: DeviceProfile("BQ2V1000", 655_360, 55.0),
    0xAC: DeviceProfile("BQ2V3000", 1_441_792, 220.0),
    0xAD: DeviceProfile("BQ2V6000", 2_883_584, 385.0),
}

DEVICE_BY_NAME = {profile.name: profile for profile in DEVICE_BY_RESPONSE.values()}


class UsbTestError(Exception):
    pass


def hex_bytes(data: bytes, max_len: int = 32) -> str:
    shown = " ".join(f"{b:02X}" for b in data[:max_len])
    return shown + (" ..." if len(data) > max_len else "")


def import_ftd2xx():
    try:
        import ftd2xx  # type: ignore
    except ImportError as exc:
        raise UsbTestError(
            "Missing Python package 'ftd2xx'. Install it with: pip install ftd2xx"
        ) from exc
    return ftd2xx


class FtdiDevice:
    def __init__(self, index: int = 0):
        self.ftd2xx = import_ftd2xx()
        self.dev = None
        self.index = index

    def __enter__(self) -> "FtdiDevice":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def open(self) -> None:
        count = self.ftd2xx.createDeviceInfoList()
        if count <= 0:
            raise UsbTestError("No FTDI USB device was found.")
        if self.index >= count:
            raise UsbTestError(f"Device index {self.index} is out of range; found {count} device(s).")
        try:
            self.dev = self.ftd2xx.open(self.index)
        except Exception as exc:
            raise UsbTestError(f"Failed to open FTDI device index {self.index}: {exc}") from exc
        self.configure()

    def configure(self) -> None:
        assert self.dev is not None
        self._call("setBitMode", self.dev.setBitMode, 0xFF, 0x40)
        if hasattr(self.dev, "setLatencyTimer"):
            self._call("setLatencyTimer", self.dev.setLatencyTimer, 2)
        elif hasattr(self.dev, "setLatency"):
            self._call("setLatency", self.dev.setLatency, 2)
        if hasattr(self.dev, "setUSBParameters"):
            self._call("setUSBParameters", self.dev.setUSBParameters, SECTOR_SIZE, SECTOR_SIZE)
        elif hasattr(self.dev, "InTransferSize"):
            self._call("InTransferSize", self.dev.InTransferSize, SECTOR_SIZE)

    def close(self) -> None:
        if self.dev is not None:
            try:
                self.dev.close()
            finally:
                self.dev = None

    def _call(self, name: str, fn, *args):
        try:
            return fn(*args)
        except Exception as exc:
            raise UsbTestError(f"FTDI {name} failed with args={args}: {exc}") from exc

    def write(self, data: bytes, label: str = "write") -> int:
        assert self.dev is not None
        try:
            written = self.dev.write(data)
        except Exception as exc:
            raise UsbTestError(f"FTDI {label} failed while writing {len(data)} byte(s): {exc}") from exc
        if written is not None and written != len(data):
            raise UsbTestError(f"FTDI {label} wrote {written} byte(s), expected {len(data)}.")
        return len(data) if written is None else int(written)

    def rx_available(self) -> int:
        assert self.dev is not None
        try:
            return int(self.dev.getQueueStatus())
        except Exception as exc:
            raise UsbTestError(f"FTDI getQueueStatus failed: {exc}") from exc

    def read(self, length: int, label: str = "read") -> bytes:
        assert self.dev is not None
        try:
            data = self.dev.read(length)
        except Exception as exc:
            raise UsbTestError(f"FTDI {label} failed while reading {length} byte(s): {exc}") from exc
        if isinstance(data, str):
            data = data.encode("latin1")
        data = bytes(data)
        if len(data) != length:
            raise UsbTestError(f"FTDI {label} returned {len(data)} byte(s), expected {length}.")
        return data

    def read_at_least(self, min_length: int, timeout: float = 5.0, label: str = "read") -> bytes:
        deadline = time.monotonic() + timeout
        available = 0
        while time.monotonic() <= deadline:
            available = self.rx_available()
            if available >= min_length:
                return self.read(available, label=label)
            time.sleep(0.01)
        raise UsbTestError(
            f"Timeout waiting for {label}: expected at least {min_length} byte(s), "
            f"queue has {available} byte(s)."
        )


def address_to_bytes(value: int | str) -> bytes:
    num = int(value) % ADDRESS_MODULO
    return num.to_bytes(4, "big")


def command_with_address(header: bytes, value: int | str) -> bytes:
    return header + address_to_bytes(value)


def file_number_from_name(path: str | Path) -> int:
    name = Path(path).name
    if "_" not in name:
        raise UsbTestError('File name format must be: number + "_" + description, for example 1_00.bit')
    prefix = name.split("_", 1)[0]
    if not prefix.isdigit():
        raise UsbTestError(f"File name prefix is not a number: {name}")
    return int(prefix)


def pad_to_length(data: bytes, length: int) -> bytes:
    if len(data) > length:
        raise UsbTestError(f"Bitstream is {len(data)} byte(s), larger than selected device length {length}.")
    return data + bytes(length - len(data))


def resolve_output_dir(output_dir: Optional[str | Path] = None) -> Path:
    directory = Path.cwd() if output_dir is None else Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def handshake(ftdi: FtdiDevice) -> DeviceProfile:
    ftdi.write(HANDSHAKE_CMD, label="handshake command AA BB CC DD")
    time.sleep(0.1)
    response = ftdi.read_at_least(1, timeout=HANDSHAKE_RESPONSE_TIMEOUT, label="handshake response")
    first = response[0]
    profile = DEVICE_BY_RESPONSE.get(first)
    if profile is None:
        raise UsbTestError(
            "Handshake returned unknown data: "
            f"{hex_bytes(response)}; expected first byte AB/AC/AD."
        )
    print(f"Handshake OK: {profile.name}, bit_length={profile.bit_length}, response={hex_bytes(response)}")
    return profile


def erase(ftdi: FtdiDevice, address: int | str) -> None:
    cmd = command_with_address(ERASE_HEADER, address)
    print(f"Erase address={address}, cmd={hex_bytes(cmd)}")
    ftdi.write(cmd, label="erase command")


def program_file(
    ftdi: FtdiDevice,
    path: str | Path,
    profile: DeviceProfile,
    auto_erase: bool = True,
    erase_delay: Optional[float] = None,
    output_dir: Optional[str | Path] = None,
) -> None:
    path = Path(path)
    if path.suffix.lower() == ".rbt":
        path = rbt_to_b(path, output_dir=output_dir)
        print(f"Converted RBT to {path}")

    address = file_number_from_name(path)
    if auto_erase:
        erase(ftdi, address)
        delay = profile.erase_delay_seconds if erase_delay is None else erase_delay
        if delay > 0:
            print(f"Waiting {delay:g}s after erase, matching original UsbTest behavior.")
            time.sleep(delay)

    start_cmd = command_with_address(PROGRAM_HEADER, address)
    print(f"Program address={address}, cmd={hex_bytes(start_cmd)}")
    ftdi.write(start_cmd, label="program-start command")
    time.sleep(0.001)

    data = pad_to_length(path.read_bytes(), profile.bit_length)
    for offset in range(0, len(data), SECTOR_SIZE):
        chunk = data[offset : offset + SECTOR_SIZE]
        ftdi.write(chunk, label=f"program data offset={offset}")
        print(f"Wrote {min(offset + len(chunk), len(data))}/{len(data)} bytes", end="\r")
    print()
    time.sleep(3.0 if len(data) % SECTOR_SIZE == 0 else 1.0)
    print(f"Program complete: address={address}, file={path}")


def readback(ftdi: FtdiDevice, address: int | str, profile: DeviceProfile) -> bytes:
    cmd = command_with_address(READBACK_HEADER, address)
    print(f"Readback address={address}, cmd={hex_bytes(cmd)}, length={profile.bit_length}")
    ftdi.write(cmd, label="readback command")

    result = bytearray()
    remaining = profile.bit_length
    while remaining > 0:
        expected = min(SECTOR_SIZE, remaining)
        chunk = ftdi.read_at_least(expected, timeout=5.0, label=f"readback offset={len(result)}")
        result.extend(chunk[:expected])
        extra = chunk[expected:]
        if extra:
            result.extend(extra)
        remaining = profile.bit_length - min(len(result), profile.bit_length)
        print(f"Read {min(len(result), profile.bit_length)}/{profile.bit_length} bytes", end="\r")
    print()
    return bytes(result[: profile.bit_length])


def stream_file_for_compare(path: str | Path, output_dir: Optional[str | Path] = None) -> Path:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".rbt":
        return rbt_to_b(path, output_dir=output_dir)
    if suffix == ".txt":
        return process_txt_file(path, output_dir=output_dir)
    return path


def legacy_datetime_text(value: Optional[datetime] = None) -> str:
    value = datetime.now() if value is None else value
    return f"{value.year}/{value.month}/{value.day} {value.hour}:{value.minute:02d}:{value.second:02d}"


def write_compare_report(output: Path, results: Iterable[tuple[int, bool]], append: bool = True) -> None:
    mode = "a" if append else "w"
    with output.open(mode, encoding="utf-8", newline="") as writer:
        writer.write(legacy_datetime_text() + "\r\n")
        for address, ok in results:
            writer.write(f"码流{address}：验证{'成功' if ok else '失败'}\r\n")


def verify_files(
    ftdi: FtdiDevice,
    files: Iterable[str | Path],
    profile: DeviceProfile,
    output: Path,
    append: bool = True,
    output_dir: Optional[str | Path] = None,
) -> None:
    results: list[tuple[int, bool]] = []
    for file_path in files:
        file_path = Path(file_path)
        address = file_number_from_name(file_path)
        compare_path = stream_file_for_compare(file_path, output_dir=output_dir)
        expected = pad_to_length(compare_path.read_bytes(), profile.bit_length)
        actual = readback(ftdi, address, profile)
        ok = actual == expected
        results.append((address, ok))
        source = f" (compare source: {compare_path})" if compare_path != file_path else ""
        print(f"{file_path}: {'OK' if ok else 'FAILED'}{source}")
    write_compare_report(output, results, append=append)
    print(f"Wrote compare result: {output}")


def create_header(path: Path) -> None:
    lines = ["# TDI\tTMS"]
    lines.extend(["x\t1"] * 5)
    lines.append("x\t0")
    lines.extend(["x\t1"] * 2)
    lines.extend(["x\t0"] * 2)
    lines.extend(["1\t0", "0\t0", "1\t0", "0\t0", "0\t0"])
    lines.append("0\t1")
    lines.extend(["x\t1"] * 2)
    lines.extend(["x\t0"] * 2)
    path.write_text("\r\n".join(lines) + "\r\n", encoding="ascii")


def create_tailer(path: Path) -> None:
    lines = ["# TDI\tTMS", "x\t1"]
    lines.extend(["x\t1"] * 5)
    lines.append("x\t0")
    lines.extend(["x\t1"] * 2)
    lines.extend(["x\t0"] * 2)
    lines.extend(["0\t0", "0\t0", "1\t0", "1\t0", "0\t0"])
    lines.append("0\t1")
    lines.append("x\t1")
    lines.extend(["x\t0"] * 15)
    lines.extend(["x\t1"] * 3)
    path.write_text("\r\n".join(lines) + "\r\n", encoding="ascii")


def txt2bit_once(path: Path, output) -> tuple[str, int]:
    string_to_end = ""
    byte_value = 0
    with path.open("r", encoding="ascii", errors="ignore") as reader:
        for raw_line in reader:
            text = raw_line.strip()
            if not text or text[0] == "#":
                continue
            if text[0] in ("x", "X"):
                text = text.upper().replace("X", "1")
            for token in re.split(r"\s+", text):
                if not token:
                    continue
                string_to_end += token
                while len(string_to_end) >= 8:
                    byte_value = int(string_to_end[:8], 2)
                    output.write(bytes([byte_value]))
                    string_to_end = string_to_end[8:]
    if string_to_end:
        byte_value = int(string_to_end + ("0" * (8 - len(string_to_end))), 2)
        output.write(bytes([byte_value]))
    return string_to_end, byte_value


def process_txt_file(path: str | Path, output_dir: Optional[str | Path] = None) -> Path:
    path = Path(path)
    directory = resolve_output_dir(output_dir)
    output_path = directory / (path.name.split(".", 1)[0] + ".b")
    header = directory / "header.txt"
    tailer = directory / "tailer.txt"
    if not header.exists():
        create_header(header)
    if not tailer.exists():
        create_tailer(tailer)

    string_to_end = ""
    byte_value = 0
    with output_path.open("wb") as output:
        string_to_end, byte_value = txt2bit_once(header, output)
        string_to_end, byte_value = txt2bit_once(path, output)
        string_to_end, byte_value = txt2bit_once(tailer, output)
        # UsbTest.exe writes one extra unpadded remainder byte after the final Txt2Bit call.
        if string_to_end:
            output.write(bytes([int(string_to_end, 2)]))
    return output_path


def process_rbt_file(path: str | Path, output_dir: Optional[str | Path] = None) -> Path:
    path = Path(path)
    output_path = resolve_output_dir(output_dir) / (path.name + ".txt")
    items: list[str] = []
    with path.open("r", encoding="ascii", errors="ignore") as reader:
        for raw_line in reader:
            line = raw_line.rstrip("\r\n")
            if not line:
                continue
            if line[0] in ("0", "1"):
                items.extend(f"{char}\t0" for char in line)
    if items:
        items[-1] = "0\t1"
    output_path.write_text("\r\n".join(items) + ("\r\n" if items else ""), encoding="ascii")
    return output_path


def rbt_to_b(path: str | Path, output_dir: Optional[str | Path] = None) -> Path:
    txt_path = process_rbt_file(path, output_dir=output_dir)
    return process_txt_file(txt_path, output_dir=output_dir)


def convert_files(files: Iterable[str | Path], output_dir: Optional[str | Path] = None) -> None:
    for file_path in files:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix == ".rbt":
            out = rbt_to_b(path, output_dir=output_dir)
        elif suffix == ".txt":
            out = process_txt_file(path, output_dir=output_dir)
        else:
            raise UsbTestError(f"Unsupported conversion input: {path}")
        print(f"Converted {path} -> {out}")


def profile_from_args(args, ftdi: Optional[FtdiDevice] = None) -> DeviceProfile:
    if args.device != "auto":
        return DEVICE_BY_NAME[args.device]
    if ftdi is None:
        raise UsbTestError("--device auto requires an open FTDI device.")
    return handshake(ftdi)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Python implementation of UsbTest.exe")
    parser.add_argument("--index", type=int, default=0, help="FTDI device index, default: 0")
    parser.add_argument(
        "--device",
        choices=["auto", *DEVICE_BY_NAME.keys()],
        default="auto",
        help="Device profile. auto uses the AA BB CC DD handshake.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("handshake", help="Open FTDI device and run handshake")

    p_erase = sub.add_parser("erase", help="Erase one flash address")
    p_erase.add_argument("address")

    p_program = sub.add_parser("program", help="Erase and program one or more .bit/.b/.rbt files")
    p_program.add_argument("files", nargs="+")
    p_program.add_argument("--no-auto-erase", action="store_true")
    p_program.add_argument("--erase-delay", type=float, default=None, help="Override post-erase delay in seconds")

    p_read = sub.add_parser("readback", help="Read back one flash address")
    p_read.add_argument("address")
    p_read.add_argument("-o", "--output", default="readback.bit")

    p_verify = sub.add_parser("verify", help="Read back and compare .bit/.b/.rbt/.txt files by address prefix")
    p_verify.add_argument("files", nargs="+")
    p_verify.add_argument("-o", "--output", default="compare.txt")

    p_convert = sub.add_parser("convert", help="Convert .rbt/.txt to .b using original UsbTest logic")
    p_convert.add_argument("files", nargs="+")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "convert":
            convert_files(args.files)
            return 0

        with FtdiDevice(index=args.index) as ftdi:
            profile = profile_from_args(args, ftdi)
            if args.command == "handshake":
                return 0
            if args.command == "erase":
                erase(ftdi, args.address)
            elif args.command == "program":
                for file_path in args.files:
                    program_file(
                        ftdi,
                        file_path,
                        profile,
                        auto_erase=not args.no_auto_erase,
                        erase_delay=args.erase_delay,
                    )
            elif args.command == "readback":
                data = readback(ftdi, args.address, profile)
                Path(args.output).write_bytes(data)
                print(f"Wrote readback data: {args.output}")
            elif args.command == "verify":
                verify_files(ftdi, args.files, profile, Path(args.output))
            else:
                parser.error(f"Unsupported command: {args.command}")
        return 0
    except UsbTestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
