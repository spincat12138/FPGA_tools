# -*- coding: utf-8 -*-
import copy
import json
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = PACKAGE_DIR / "profiles"
DEFAULT_OUTPUT = "constraints.ucf"
DEFAULT_END_MARKER = "# End of constraints"


class ProfileError(ValueError):
    pass


def builtin_profile_paths():
    return sorted(PROFILE_DIR.glob("*.json"))


def load_builtin_profile(name):
    path = PROFILE_DIR / "{name}.json".format(name=name)
    if not path.is_file():
        raise ProfileError("未找到内置 profile：{name}".format(name=name))
    return load_profile(path)


def load_profile(path):
    profile_path = Path(path)
    try:
        with profile_path.open("r", encoding="utf-8") as handle:
            profile = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ProfileError("JSON 格式错误：{error}".format(error=exc)) from exc

    profile["_profile_path"] = str(profile_path)
    validate_profile(profile)
    return profile


def save_profile(profile, path):
    target = Path(path)
    data = copy.deepcopy(profile)
    data.pop("_profile_path", None)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def profile_to_json(profile):
    data = copy.deepcopy(profile)
    data.pop("_profile_path", None)
    return json.dumps(data, ensure_ascii=False, indent=2)


def profile_from_json(text):
    try:
        profile = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProfileError("JSON 格式错误：{error}".format(error=exc)) from exc
    validate_profile(profile)
    return profile


def validate_profile(profile):
    if not isinstance(profile, dict):
        raise ProfileError("profile 必须是 JSON 对象")

    _require_dict(profile, "output")
    _require_dict(profile, "modules")
    _require_dict(profile, "uxx")
    _require_dict(profile, "uy")
    _require_dict(profile, "placement")
    if not isinstance(profile.get("path_template"), str) or not profile["path_template"]:
        raise ProfileError("path_template 不能为空")

    blocks = profile.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise ProfileError("blocks 必须是非空列表")

    line_mode = profile["output"].get("line_mode")
    if line_mode not in {"single", "paired"}:
        raise ProfileError("output.line_mode 只能是 single 或 paired")
    if line_mode == "paired" and len(blocks) < 2:
        raise ProfileError("paired 模式至少需要两个 blocks")

    modules_kind = profile["modules"].get("kind")
    if modules_kind == "range":
        _require_int(profile["modules"], "start")
        _require_int(profile["modules"], "stop")
        if profile["modules"]["stop"] <= profile["modules"]["start"]:
            raise ProfileError("modules.stop 必须大于 modules.start")
        if not isinstance(profile["modules"].get("template"), str):
            raise ProfileError("modules.template 必须是字符串")
    elif modules_kind == "list":
        values = profile["modules"].get("values")
        if not isinstance(values, list) or not values:
            raise ProfileError("modules.values 必须是非空列表")
    else:
        raise ProfileError("modules.kind 只能是 range 或 list")

    validate_sequence_config(profile["uxx"], "uxx", allow_none=False)

    validate_sequence_config(profile["uy"], "uy", allow_none=True)

    for key in ("x_base", "x_jump", "y_slice", "y_jump"):
        _require_int(profile["placement"], key)
    if profile["placement"]["y_jump"] <= 0:
        raise ProfileError("placement.y_jump 必须大于 0")
    if profile["placement"]["y_slice"] <= 0:
        raise ProfileError("placement.y_slice 必须大于 0")
    if profile["placement"]["y_slice"] % profile["placement"]["y_jump"] != 0:
        raise ProfileError("placement.y_slice 必须能被 y_jump 整除")


def validate_sequence_config(config, name, allow_none):
    kind = config.get("kind")
    if kind is None and name == "uxx" and "count" in config:
        _require_int(config, "count")
        if config["count"] <= 0:
            raise ProfileError("uxx.count 必须大于 0")
        if not isinstance(config.get("format", "u%02d"), str):
            raise ProfileError("uxx.format 必须是字符串")
        return

    if kind == "range":
        _require_int(config, "start")
        _require_int(config, "stop")
        if config["stop"] < config["start"]:
            raise ProfileError("{name}.stop 必须大于或等于 {name}.start".format(name=name))
    elif kind == "list":
        values = config.get("values")
        if not isinstance(values, list) or not values:
            raise ProfileError("{name}.values 必须是非空列表".format(name=name))
    elif kind == "none" and allow_none:
        return
    else:
        allowed = "range、list 或 none" if allow_none else "range 或 list"
        raise ProfileError("{name}.kind 只能是 {allowed}".format(name=name, allowed=allowed))

    if not isinstance(config.get("format", ""), str):
        raise ProfileError("{name}.format 必须是字符串".format(name=name))


def _legacy_count_to_range(config):
    return {
        "kind": "range",
        "start": 0,
        "stop": config["count"] - 1,
        "format": config.get("format", "u%02d"),
    }


def expand_uxx(config):
    if config.get("kind") is None and "count" in config:
        config = _legacy_count_to_range(config)
    return expand_sequence(config)


def expand_sequence(config):
    kind = config["kind"]
    if kind == "none":
        return [None]

    fmt = config.get("format")
    if kind == "range":
        values = range(config["start"], config["stop"] + 1)
    else:
        values = config["values"]

    if not fmt:
        return [str(value) for value in values]
    return [_apply_percent_format(fmt, value) for value in values]


def generate_lines(profile, limit=None):
    validate_profile(profile)
    lines = []
    line_mode = profile["output"]["line_mode"]
    pair_padding = int(profile["output"].get("pair_padding", 64))
    slice_idx = 0

    for module in expand_modules(profile["modules"]):
        for uxx in expand_uxx(profile["uxx"]):
            for uy in expand_uy(profile["uy"]):
                x, y = calc_xy(profile["placement"], slice_idx)
                constraints = [
                    format_constraint(profile, module, uxx, uy, block, x, y)
                    for block in profile["blocks"]
                ]
                if line_mode == "single":
                    lines.extend(constraints)
                else:
                    first = constraints[0].ljust(pair_padding)
                    lines.append("{first}    {second}".format(
                        first=first,
                        second=constraints[1],
                    ))
                    if len(constraints) > 2:
                        lines.extend(constraints[2:])

                slice_idx += 1
                if limit is not None and len(lines) >= limit:
                    return lines[:limit]

    return lines


def generate_text(profile, limit=None, include_end_marker=True):
    lines = generate_lines(profile, limit=limit)
    if include_end_marker and limit is None:
        end_marker = profile.get("output", {}).get("end_marker", DEFAULT_END_MARKER)
        if end_marker:
            lines.append("")
            lines.append(end_marker)
    return "\n".join(lines)


def write_ucf(profile, output_path):
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = generate_text(profile)
    target.write_text(text, encoding="utf-8")
    return target


def expand_modules(config):
    if config["kind"] == "range":
        template = config["template"]
        return [
            template.format(i=index, index=index)
            for index in range(config["start"], config["stop"])
        ]
    return [str(value) for value in config["values"]]


def expand_uy(config):
    return expand_sequence(config)


def calc_xy(placement, slice_idx):
    y_slice = placement["y_slice"]
    y_jump = placement["y_jump"]
    rows_per_x = y_slice // y_jump
    x = (slice_idx // rows_per_x) * placement["x_jump"] + placement["x_base"]
    y = (slice_idx % rows_per_x) * y_jump
    return x, y


def format_constraint(profile, module, uxx, uy, block, x, y):
    block_name = block.get("name")
    test_name = "" if block_name is None else block_name
    inst = profile["path_template"].format(
        module=module,
        block=test_name,
        test_name=test_name,
        TestName=test_name,
        uxx=uxx,
        uy="" if uy is None else uy,
    )
    loc_x = x + int(block.get("x_offset", 0))
    loc_y = y + int(block.get("y_offset", 0))
    return 'INST "{inst}" LOC = SLICE_X{x}Y{y};'.format(
        inst=inst,
        x=loc_x,
        y=loc_y,
    )


def _require_dict(parent, key):
    if not isinstance(parent.get(key), dict):
        raise ProfileError("{key} 必须是对象".format(key=key))


def _require_int(parent, key):
    value = parent.get(key)
    if not isinstance(value, int):
        raise ProfileError("{key} 必须是整数".format(key=key))


def _apply_percent_format(fmt, value):
    try:
        return fmt % value
    except TypeError:
        return fmt % str(value)
