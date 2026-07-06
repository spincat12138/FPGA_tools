# -*- coding: utf-8 -*-
import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_DEVICE = "xcvu9p-flgb2104-2L-e"
DEFAULT_VIVADO_PATH = "C:/Xilinx/Vivado/2019.1/bin/vivado.bat"
SOURCE_DIR_NAME = "source"
SOURCE_SUBDIRS = ("hdl", "sim", "xdc")
NO_SIM_VERILOG_WARNING = "[Warning] source/sim 文件夹下未找到 .v 文件，TCL 中已跳过 sim_1 文件添加项"


def validate_project_name(project_name):
    """Validate the project name before it is used as a directory and Tcl token."""
    name = project_name.strip()
    if not name:
        raise ValueError("project_name 不能为空")
    if Path(name).name != name or any(separator in name for separator in ("/", "\\")):
        raise ValueError("project_name 只能是单级目录名，不能包含路径分隔符")
    if any(char in name for char in "{}"):
        raise ValueError("project_name 不能包含 Tcl 花括号")
    return name


def resolve_project_dir(root_dir, project_name):
    if not str(root_dir).strip():
        raise ValueError("根目录不能为空")
    root = Path(root_dir).expanduser()
    return root / validate_project_name(project_name)


def create_project_dir(project_dir, target_name=SOURCE_DIR_NAME):
    """Create the Vivado project source directory structure."""
    project_path = Path(project_dir)
    created_dirs = []

    for subdir in SOURCE_SUBDIRS:
        path = project_path / target_name / subdir
        path.mkdir(parents=True, exist_ok=True)
        created_dirs.append(path)

    return created_dirs


def tcl_braced(value):
    text = str(value).replace("\\", "/")
    if any(char in text for char in "{}"):
        raise ValueError("Tcl 参数不能包含花括号: {value}".format(value=value))
    return "{{{value}}}".format(value=text)


def has_sim_verilog_files(project_dir):
    return any((Path(project_dir) / SOURCE_DIR_NAME / "sim").glob("*.v"))


def has_hdl_xci_files(project_dir):
    return any((Path(project_dir) / SOURCE_DIR_NAME / "hdl").glob("*.xci"))


def create_project_tcl(project_name, device=DEFAULT_DEVICE, project_dir=None):
    """Generate a Tcl script for creating the Vivado project."""
    name = validate_project_name(project_name)
    part = device.strip()
    if not part:
        raise ValueError("device 不能为空")

    project_path = Path(project_dir or Path.cwd()).resolve()
    project_path.mkdir(parents=True, exist_ok=True)
    tcl_path = project_path / "{name}_create_project.tcl".format(name=name)

    create_project_option = "create_project {name} {project_dir} -part {device}".format(
        name=tcl_braced(name),
        project_dir=tcl_braced(project_path),
        device=tcl_braced(part),
    )
    add_file_options = []
    if has_sim_verilog_files(project_path):
        add_file_options.append("add_files -fileset sim_1 -norecurse [glob source/sim/*.v]")
    add_file_options.extend(
        (
            "add_files -fileset constrs_1 -norecurse [glob source/xdc/*.xdc]",
            "add_files -fileset sources_1 -norecurse [glob source/hdl/*.v]",
        )
    )
    if has_hdl_xci_files(project_path):
        add_file_options.append("add_files -fileset sources_1 -norecurse [glob source/hdl/*.xci]")
    synth_strategy = "set_property strategy Flow_RuntimeOptimized [get_runs synth_1]"
    impl_strategy = "set_property strategy Flow_RuntimeOptimized [get_runs impl_1]"
    bit_compress_option = "set_property STEPS.WRITE_BITSTREAM.ARGS.RAW_BITFILE true [get_runs impl_1]"

    tcl_content = "\n".join(
        (
            create_project_option,
            "\n".join(add_file_options),
            synth_strategy,
            impl_strategy,
            bit_compress_option,
        )
    )
    tcl_path.write_text(tcl_content, encoding="utf-8")
    return tcl_path


def create_vivado_project(tcl_file, vivado_path=DEFAULT_VIVADO_PATH, cwd=None):
    """Run Vivado in batch mode with the generated Tcl script."""
    executable = Path(vivado_path)
    if not executable.exists():
        raise FileNotFoundError("Vivado 路径不存在: {path}".format(path=vivado_path))

    result = subprocess.run(
        [
            str(executable),
            "-mode",
            "batch",
            "-nolog",
            "-nojournal",
            "-source",
            str(tcl_file),
        ],
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout or "Vivado 执行失败，退出码: {code}".format(code=result.returncode))
    return result.stdout


def create_project_structure(root_dir, project_name):
    project_dir = resolve_project_dir(root_dir, project_name)
    return project_dir, create_project_dir(project_dir)


def build_vivado_project(root_dir, project_name, device=DEFAULT_DEVICE, vivado_path=DEFAULT_VIVADO_PATH):
    project_dir = resolve_project_dir(root_dir, project_name)
    if not project_dir.exists():
        raise FileNotFoundError("工程目录不存在: {path}".format(path=project_dir))

    warnings = []
    if not has_sim_verilog_files(project_dir):
        warnings.append(NO_SIM_VERILOG_WARNING)
    tcl_file = create_project_tcl(project_name, device=device, project_dir=project_dir)
    vivado_output = create_vivado_project(tcl_file, vivado_path=vivado_path, cwd=project_dir)
    return project_dir, tcl_file, vivado_output, warnings


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Create Vivado project directories or build a project.")
    parser.add_argument("project_name", help="Vivado project name")
    parser.add_argument("mode", choices=("mkdir", "project"), help="Execution mode")
    parser.add_argument("--root-dir", default=".", help="Root directory for the project")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="Vivado device part")
    parser.add_argument("--vivado-path", default=DEFAULT_VIVADO_PATH, help="Path to vivado.bat")
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)

    try:
        if args.mode == "mkdir":
            project_dir, created_dirs = create_project_structure(args.root_dir, args.project_name)
            print("工程目录: {path}".format(path=project_dir))
            for path in created_dirs:
                print("创建 {path} 成功".format(path=path))
        else:
            project_dir, tcl_file, output, warnings = build_vivado_project(
                args.root_dir,
                args.project_name,
                device=args.device,
                vivado_path=args.vivado_path,
            )
            print("工程目录: {path}".format(path=project_dir))
            print("TCL脚本: {path}".format(path=tcl_file))
            for warning in warnings:
                print(warning)
            print(output)
    except Exception as exc:
        print("错误: {message}".format(message=exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
