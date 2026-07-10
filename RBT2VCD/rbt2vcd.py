#!/usr/bin/env python3
"""Convert a Xilinx ASCII RBT file to a SelectMAP-style VCD file.

This script replaces the original UltraEdit macro + ModelSim dump flow used by
this project.  It follows the Virtex-7 43-bit ordering documented in
``使用说明.docx`` and in ``RBT2VCD_DataLoad_tb.v``.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
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

CTRL_DATA = "00000110110"
CTRL_SETUP = "00000110010"
CTRL_PROG_LOW = "00000110000"
CTRL_TAIL = "00000110111"


@dataclass(frozen=True)
class Rbt2VcdProfile:
    signals: tuple[str, ...]
    ctrl_data: str
    ctrl_setup: str
    ctrl_prog_low: str
    ctrl_tail: str
    word_size: int = 32

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def zero_data(self) -> str:
        return "0" * self.word_size

    @property
    def header_vectors(self) -> tuple[str, ...]:
        return tuple(
            [self.ctrl_data + self.zero_data] * 12
            + [self.ctrl_setup + self.zero_data] * 4
            + [self.ctrl_prog_low + self.zero_data] * 8
            + [self.ctrl_data + self.zero_data] * 16
        )

    @property
    def tail_vectors(self) -> tuple[str, ...]:
        return tuple([self.ctrl_tail + self.zero_data] * 14)


DEFAULT_PROFILE = Rbt2VcdProfile(
    signals=tuple(SIGNALS),
    ctrl_data=CTRL_DATA,
    ctrl_setup=CTRL_SETUP,
    ctrl_prog_low=CTRL_PROG_LOW,
    ctrl_tail=CTRL_TAIL,
    word_size=32,
)


def format_elapsed_seconds(elapsed_seconds: float) -> str:
    return f"{elapsed_seconds:.1f} s"


def _read_config_value(config: dict[str, object], *names: str, default: object) -> object:
    for name in names:
        if name in config:
            return config[name]
    return default


def _validate_binary(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a binary string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    if set(value) - {"0", "1"}:
        raise ValueError(f"{field_name} contains non-binary characters")
    return value


def _coerce_signals(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")

    signals: list[str] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name}[{index}] must be a non-empty string")
        signal = item.strip()
        if any(character.isspace() for character in signal):
            raise ValueError(f"{field_name}[{index}] must not contain whitespace")
        signals.append(signal)

    if not signals:
        raise ValueError(f"{field_name} must not be empty")
    if len(set(signals)) != len(signals):
        raise ValueError(f"{field_name} contains duplicate signal names")
    return tuple(signals)


def _coerce_word_size(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _validate_profile(profile: Rbt2VcdProfile, source: str) -> Rbt2VcdProfile:
    signals = _coerce_signals(list(profile.signals), "SIGNALS")
    word_size = _coerce_word_size(profile.word_size, "WORD_SIZE")
    control_width = len(signals) - word_size
    if control_width < 1:
        raise ValueError(
            f"{source}: signals count {len(signals)} must be greater than "
            f"word_size {word_size}"
        )

    for field_name, value in (
        ("CTRL_DATA", profile.ctrl_data),
        ("CTRL_SETUP", profile.ctrl_setup),
        ("CTRL_PROG_LOW", profile.ctrl_prog_low),
        ("CTRL_TAIL", profile.ctrl_tail),
    ):
        control_value = _validate_binary(value, field_name)
        if len(control_value) != control_width:
            raise ValueError(
                f"{source}: {field_name} width is {len(control_value)}, "
                f"expected {control_width} from signals count minus word_size"
            )

    return profile


def load_rbt2vcd_profile(profile_path: Path | None = None) -> Rbt2VcdProfile:
    if profile_path is None:
        return _validate_profile(DEFAULT_PROFILE, "default profile")

    try:
        config = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{profile_path}: invalid JSON: {exc}") from exc

    if not isinstance(config, dict):
        raise ValueError(f"{profile_path}: profile JSON must be an object")

    unsupported_fields = [
        field_name
        for field_name in (
            "header_vectors",
            "HEADER_VECTORS",
            "tail_vectors",
            "TAIL_VECTORS",
            "data_prefix",
        )
        if field_name in config
    ]
    if unsupported_fields:
        raise ValueError(
            f"{profile_path}: {', '.join(unsupported_fields)} are not configurable; "
            "set CTRL_DATA/CTRL_SETUP/CTRL_PROG_LOW/CTRL_TAIL instead"
        )

    signals = _coerce_signals(
        _read_config_value(config, "signals", "SIGNALS", default=list(DEFAULT_PROFILE.signals)),
        "signals",
    )
    ctrl_data = _validate_binary(
        _read_config_value(
            config,
            "ctrl_data",
            "CTRL_DATA",
            default=DEFAULT_PROFILE.ctrl_data,
        ),
        "CTRL_DATA",
    )
    ctrl_setup = _validate_binary(
        _read_config_value(
            config,
            "ctrl_setup",
            "CTRL_SETUP",
            default=DEFAULT_PROFILE.ctrl_setup,
        ),
        "CTRL_SETUP",
    )
    ctrl_prog_low = _validate_binary(
        _read_config_value(
            config,
            "ctrl_prog_low",
            "CTRL_PROG_LOW",
            default=DEFAULT_PROFILE.ctrl_prog_low,
        ),
        "CTRL_PROG_LOW",
    )
    ctrl_tail = _validate_binary(
        _read_config_value(
            config,
            "ctrl_tail",
            "CTRL_TAIL",
            default=DEFAULT_PROFILE.ctrl_tail,
        ),
        "CTRL_TAIL",
    )
    word_size = _coerce_word_size(
        _read_config_value(config, "word_size", "WORD_SIZE", default=DEFAULT_PROFILE.word_size),
        "word_size",
    )

    return _validate_profile(
        Rbt2VcdProfile(
            signals=signals,
            ctrl_data=ctrl_data,
            ctrl_setup=ctrl_setup,
            ctrl_prog_low=ctrl_prog_low,
            ctrl_tail=ctrl_tail,
            word_size=word_size,
        ),
        str(profile_path),
    )


def read_rbt_words(path: Path, word_size: int = 32) -> list[str]:
    words: list[str] = []

    for line_number, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        if len(text) == word_size and set(text) <= {"0", "1"}:
            words.append(text)
            continue
        if words:
            raise ValueError(f"{path}:{line_number}: found non-bitstream text after data starts")

    if not words:
        raise ValueError(f"{path}: no {word_size}-bit RBT data lines found")

    return words


def build_selectmap_vectors(
    words: list[str],
    profile: Rbt2VcdProfile = DEFAULT_PROFILE,
) -> list[str]:
    return (
        list(profile.header_vectors)
        + [profile.ctrl_data + word for word in words]
        + list(profile.tail_vectors)
    )


def write_converted_rbt(vectors: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(vectors) + "\n", encoding="ascii")


def vcd_ids(count: int) -> list[str]:
    # VCD identifiers are printable non-whitespace ASCII. Use short base-94 ids.
    characters = [chr(code) for code in range(ord("!"), ord("~") + 1)]

    def encode(index: int) -> str:
        encoded = ""
        base = len(characters)
        while True:
            encoded = characters[index % base] + encoded
            index = index // base - 1
            if index < 0:
                return encoded

    return [encode(index) for index in range(count)]


def write_vcd(
    vectors: list[str],
    path: Path,
    period_ps: int,
    profile: Rbt2VcdProfile = DEFAULT_PROFILE,
) -> None:
    ids = vcd_ids(profile.signal_count)
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

        for signal_id, signal_name in zip(ids, profile.signals):
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
    profile: Rbt2VcdProfile | None = None,
    profile_path: Path | None = None,
) -> dict[str, object]:
    start_time = time.time()
    if profile is not None and profile_path is not None:
        raise ValueError("profile and profile_path cannot be used together")

    active_profile = (
        _validate_profile(profile, "profile")
        if profile
        else load_rbt2vcd_profile(profile_path)
    )
    words = read_rbt_words(input_rbt, active_profile.word_size)
    vectors = build_selectmap_vectors(words, active_profile)

    if converted_rbt:
        write_converted_rbt(vectors, converted_rbt)

    write_vcd(vectors, output_vcd, period_ps, active_profile)
    elapsed_seconds = time.time() - start_time

    return {
        "word_count": len(words),
        "vector_count": len(vectors),
        "signal_count": active_profile.signal_count,
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
    parser.add_argument(
        "--profile",
        type=Path,
        help="Optional JSON profile for custom signals and CTRL_* control values.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = convert_rbt_to_vcd(
        args.input_rbt,
        args.output_vcd,
        period_ps=args.period_ps,
        converted_rbt=args.converted_rbt,
        profile_path=args.profile,
    )
    print(f"Read {result['word_count']} RBT data words")
    print(f"Wrote {result['vector_count']} SelectMAP vectors")
    print(f"Signals: {result['signal_count']}")
    print(f"VCD: {args.output_vcd}")
    if args.converted_rbt:
        print(f"Converted RBT: {args.converted_rbt}")
    print(f"用时{result['elapsed_text']}")


if __name__ == "__main__":
    main()
