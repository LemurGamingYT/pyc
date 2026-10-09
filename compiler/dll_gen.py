from pathlib import Path

from llvmlite import ir


def llvm_to_py(ir_type: ir.Type):
    match ir_type:
        case ir.IntType(width=32):
            return int
        case _:
            raise NotImplementedError(ir_type)

def generate_python_interop_file(module: ir.Module, path: Path, dll_path: Path):
    code = f"""from ctypes import CDLL

lib = CDLL('{dll_path.as_posix()}')
"""

    for func in module.globals.values():
        if not isinstance(func, ir.Function):
            continue

        params_str = ', '.join(f'{arg.name.removeprefix("param.")}: {llvm_to_py(arg.type).__name__}' for arg in func.args)
        call_args_str = ', '.join(arg.name.removeprefix('param.') for arg in func.args)
        code += f"""def {func.name}({params_str}) -> {llvm_to_py(func.function_type.return_type).__name__}:
    return lib.{func.name}({call_args_str})

"""

    path.write_text(code)
