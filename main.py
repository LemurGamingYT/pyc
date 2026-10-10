import ast
from typing import Iterable, Optional
from dataclasses import dataclass
from subprocess import run
from pathlib import Path

from simple_parsing import ArgumentParser, field
from llvmlite import ir

from compiler.dll_gen import generate_python_interop_file
from compiler import PycCompiler


@dataclass(slots=True)
class BuildCommand:
    path: Path = field(positional=True, help='The path to build')
    emit: str = field(default='exe')

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
        
        compiler = PycCompiler(self.path)
        module = compiler.visit(ast.parse(src, filename=self.path))
        match self.emit:
            case 'ir':
                output_file = self.create_ir_file(module)
            case 'exe':
                ir_file = self.create_ir_file(module)
                obj_file = self.create_obj_file(ir_file)
                output_file = self.create_exe_file(obj_file)
            case 'obj':
                ir_file = self.create_ir_file(module)
                output_file = self.create_obj_file(ir_file)
            case 'dll':
                ir_file = self.create_ir_file(module)
                obj_file = self.create_obj_file(ir_file)
                output_file = self.create_dll_file(obj_file)
            case 'py':
                ir_file = self.create_ir_file(module)
                obj_file = self.create_obj_file(ir_file)
                dll_file = self.create_dll_file(obj_file)

                output_file = self.path.with_stem(f'{self.path.stem}_gen')
                generate_python_interop_file(module, output_file, dll_file)
            case _:
                parser.error(f'unknown emission file type {self.emit}')

        print(f'compiled to {output_file}')

class PycArgumentParser(ArgumentParser):
    def __init__(self):
        super().__init__()

        self._commands = {}
        
        self.subparsers = self.add_subparsers(dest='action', parser_class=ArgumentParser)
        
        self.add_command(name='build', help='Build the given python file', cls=BuildCommand)

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
