import ast
from importlib.util import spec_from_file_location, module_from_spec
from typing import Iterable, Optional
from dataclasses import dataclass
from enum import Enum, auto
from subprocess import run
from pathlib import Path

from simple_parsing import ArgumentParser, field
from timer_cm import Timer
from llvmlite import ir

from compiler.dll_gen import generate_python_interop_file
from compiler import PycCompiler


def load_py_module(path: Path):
    # Thank you so much https://stackoverflow.com/questions/65123857/import-a-module-from-a-pathlib-source-file-path
    # I have been looking for a way to load a module from a Path object for so long
    spec = spec_from_file_location(path.name, path)
    assert spec is not None
    assert spec.loader is not None
    
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    return module

class EmitType(Enum):
    exe = auto()
    py = auto()
    dll = auto()
    obj = auto()
    ir = auto()

@dataclass(slots=True)
class BuildCommand:
    path: Path = field(positional=True, help='The path to build')
    emit: str = field(default=EmitType.exe.name, choices=[
        etype.name
        for etype in list(EmitType)
    ])

    @property
    def emit_type(self):
        return EmitType[self.emit.upper()]

    def __post_init__(self):
        self.path = self.path.resolve()

    def create_ir_file(self, module: ir.Module):
        ir_file = self.path.with_suffix('.ll')
        ir_file.write_text(str(module))

        return ir_file

    def create_obj_file(self, ir_file: Path):
        obj_file = self.path.with_suffix('.o')
        run(['clang', str(ir_file), '-c', '-o', str(obj_file), '-Wno-override-module'])

        return obj_file

    def create_dll_file(self, *obj_files: Path):
        dll_file = self.path.with_suffix('.dll')
        run(['clang', *[str(obj) for obj in obj_files], '-shared', '-o', str(dll_file)], shell=True, check=True)

        return dll_file

    def create_exe_file(self, *obj_files: Path):
        exe_file = self.path.with_suffix('.exe')
        run(['clang', *[str(obj) for obj in obj_files], '-o', str(exe_file)], shell=True, check=True)

        return exe_file

    def execute(self, parser: ArgumentParser):
        if not self.path.exists():
            parser.error('path does not exist')

        if not self.path.is_file():
            parser.error('expected given path to be a file')

        src = self.path.read_text('utf8')
        program = ast.parse(src, filename=self.path)
        # print(ast.dump(program, indent=2))
        
        compiler = PycCompiler(self.path)
        module = compiler.visit(program)
        match self.emit_type:
            case EmitType.ir:
                output_file = self.create_ir_file(module)
            case EmitType.obj:
                ir_file = self.create_ir_file(module)
                output_file = self.create_obj_file(ir_file)
            case EmitType.exe:
                ir_file = self.create_ir_file(module)
                obj_file = self.create_obj_file(ir_file)
                output_file = self.create_exe_file(obj_file)
            case EmitType.dll:
                ir_file = self.create_ir_file(module)
                obj_file = self.create_obj_file(ir_file)
                output_file = self.create_dll_file(obj_file)
            case EmitType.py:
                ir_file = self.create_ir_file(module)
                obj_file = self.create_obj_file(ir_file)
                dll_file = self.create_dll_file(obj_file)

                output_file = self.path.with_stem(f'{self.path.stem}_gen')
                generate_python_interop_file(module, output_file, dll_file)

        print(f'compiled to {output_file}')
        return output_file

@dataclass(slots=True)
class BenchmarkCommand:
    path: Path = field(positional=True, help='The path to benchmark')
    function_name: str = field(positional=True, help='The function to benchmark in the path')

    def execute(self, parser: ArgumentParser):
        build_cmd = BuildCommand(self.path, 'py')
        py_gen = build_cmd.execute(parser)

        python_module = load_py_module(self.path)
        pyc_module = load_py_module(py_gen)

        python_func = getattr(python_module, self.function_name)
        pyc_func = getattr(pyc_module, self.function_name)
        with Timer('Python') as py_timer:
            python_func()

        with Timer('Pyc') as pyc_timer:
            pyc_func()

        if py_timer.elapsed > pyc_timer.elapsed:
            print(f'Pyc is {py_timer.elapsed / pyc_timer.elapsed:.3f}x faster than Python')
        elif py_timer.elapsed < pyc_timer.elapsed:
            print(f'Pyc is {pyc_timer.elapsed / py_timer.elapsed:.3f}x slower than Python')
        else:
            print('Pyc and Python are exactly the same speed')

class PycArgumentParser(ArgumentParser):
    def __init__(self):
        super().__init__()

        self._commands = {}
        
        self.subparsers = self.add_subparsers(dest='action', required=True, parser_class=ArgumentParser)
        
        self.add_command(name='build', help='Build the given python file', cls=BuildCommand)
        self.add_command(name='benchmark', help='Test the given python file as a benchmark', cls=BenchmarkCommand)

    def add_command(self, name: str, help: str, cls: type):
        parser = self.subparsers.add_parser(name, help=help)
        parser.add_arguments(cls, dest='command')

        self._commands[name] = parser

    def parse(self, args: Optional[Iterable[str]] = None):
        parsed = self.parse_args(args=args)

        parser = self._commands[parsed.action]
        return parsed.command.execute(parser)

def main():
    arg_parser = PycArgumentParser()
    arg_parser.parse()

if __name__ == '__main__':
    main()
