#!/usr/bin/env python3
"""Convert a Xilinx ASCII RBT file to a SelectMAP-style VCD file.

This script replaces the original UltraEdit macro + ModelSim dump flow used by
this project.  It follows the Virtex-7 43-bit ordering documented in
``使用说明.docx`` and in ``RBT2VCD_DataLoad_tb.v``.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import time


SIGNALS = [
    "CFG_CCLK",
    "CFG_PUDC",
    "CFG_BVS",
    "CFG_RDWR",
    "CFG_CSI",
    "CFG_M2",
    "CFG_M1",
    "CFG_M0",
    "CFG_PROG",
    "CFG_INIT",
    "CFG_DONE",
    "CFG_D24",
    "CFG_D25",
    "CFG_D26",
    "CFG_D27",
    "CFG_D28",
    "CFG_D29",
    "CFG_D30",
    "CFG_D31",
    "CFG_D16",
    "CFG_D17",
    "CFG_D18",
    "CFG_D19",
    "CFG_D20",
    "CFG_D21",
    "CFG_D22",
    "CFG_D23",
    "CFG_D08",
    "CFG_D09",
    "CFG_D10",
    "CFG_D11",
    "CFG_D12",
    "CFG_D13",
    "CFG_D14",
    "CFG_D15",
    "CFG_D00",
    "CFG_D01",
    "CFG_D02",
    "CFG_D03",
    "CFG_D04",
    "CFG_D05",
    "CFG_D06",
    "CFG_D07",
]

ZERO_DATA = "0" * 32
CTRL_DATA = "00000110110"
CTRL_SETUP = "00000110010"
CTRL_PROG_LOW = "00000110000"
CTRL_TAIL = "00000110111"

HEADER_VECTORS = (
    [CTRL_DATA + ZERO_DATA] * 12
    + [CTRL_SETUP + ZERO_DATA] * 4
    + [CTRL_PROG_LOW + ZERO_DATA] * 8
    + [CTRL_DATA + ZERO_DATA] * 16
)
TAIL_VECTORS = [CTRL_TAIL + ZERO_DATA] * 14


def format_elapsed_seconds(elapsed_seconds: float) -> str:
    return f"{elapsed_seconds:.1f} s"


def read_rbt_words(path: Path) -> list[str]:
    words: list[str] = []

    for line_number, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        if len(text) == 32 and set(text) <= {"0", "1"}:
            words.append(text)
            continue
        if words:
            raise ValueError(f"{path}:{line_number}: found non-bitstream text after data starts")

    if not words:
        raise ValueError(f"{path}: no 32-bit RBT data lines found")

    return words


def build_selectmap_vectors(words: list[str]) -> list[str]:
    return HEADER_VECTORS + [CTRL_DATA + word for word in words] + TAIL_VECTORS


def write_converted_rbt(vectors: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(vectors) + "\n", encoding="ascii")


def vcd_ids(count: int) -> list[str]:
    # Printable one-character identifiers are enough for this 43-signal file.
    start = ord("!")
    return [chr(start + index) for index in range(count)]


def write_vcd(vectors: list[str], path: Path, period_ps: int) -> None:
    ids = vcd_ids(len(SIGNALS))
    previous: str | None = None

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as file:
        file.write("$date\n")
        file.write(f"\t{datetime.now():%a %b %d %H:%M:%S %Y}\n")
        file.write("$end\n")
        file.write("$version\n")
        file.write("\tPython RBT2VCD\n")
        file.write("$end\n")
        file.write("$timescale\n")
        file.write("\t1ps\n")
        file.write("$end\n\n")
        file.write("$scope module RBT2VCD_DataLoad_tb $end\n")

        for signal_id, signal_name in zip(ids, SIGNALS):
            file.write(f"$var wire 1 {signal_id} {signal_name} $end\n")

        file.write("$upscope $end\n")
        file.write("$enddefinitions $end\n")

        for index, vector in enumerate(vectors):
            if previous is None:
                file.write(f"#{index * period_ps}\n")
                file.write("$dumpvars\n")
                for bit, signal_id in reversed(list(zip(vector, ids))):
                    file.write(f"{bit}{signal_id}\n")
                file.write("$end\n")
            else:
                changes = [
                    (bit, signal_id)
                    for bit, old_bit, signal_id in zip(vector, previous, ids)
                    if bit != old_bit
                ]
                if not changes:
                    previous = vector
                    continue

                file.write(f"#{index * period_ps}\n")
                for bit, signal_id in reversed(changes):
                    file.write(f"{bit}{signal_id}\n")
            previous = vector


def convert_rbt_to_vcd(
    input_rbt: Path,
    output_vcd: Path,
    period_ps: int = 20_000,
    converted_rbt: Path | None = None,
) -> dict[str, object]:
    start_time = time.time()
    words = read_rbt_words(input_rbt)
    vectors = build_selectmap_vectors(words)

    if converted_rbt:
        write_converted_rbt(vectors, converted_rbt)

    write_vcd(vectors, output_vcd, period_ps)
    elapsed_seconds = time.time() - start_time

    return {
        "word_count": len(words),
        "vector_count": len(vectors),
        "elapsed_seconds": elapsed_seconds,
        "elapsed_text": format_elapsed_seconds(elapsed_seconds),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Xilinx ASCII RBT file to a Virtex-7 SelectMAP VCD file."
    )
    parser.add_argument("input_rbt", type=Path, help="Original Vivado/ISE ASCII .rbt file")
    parser.add_argument("output_vcd", type=Path, help="Output .vcd file")
    parser.add_argument(
        "--converted-rbt",
        type=Path,
        help="Optional 43-bit intermediate file compatible with RBT2VCD_DataLoad_tb.v",
    )
    parser.add_argument(
        "--period-ps",
        type=int,
        default=20_000,
        help="Time step per RBT word in ps. Default: 20000 ps, matching Period=20 ns.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = convert_rbt_to_vcd(
        args.input_rbt,
        args.output_vcd,
        period_ps=args.period_ps,
        converted_rbt=args.converted_rbt,
    )
    print(f"Read {result['word_count']} RBT data words")
    print(f"Wrote {result['vector_count']} SelectMAP vectors")
    print(f"VCD: {args.output_vcd}")
    if args.converted_rbt:
        print(f"Converted RBT: {args.converted_rbt}")
    print(f"用时{result['elapsed_text']}")


if __name__ == "__main__":
    main()
