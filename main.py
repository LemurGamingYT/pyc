import ast
from typing import Iterable, Optional
from dataclasses import dataclass
from subprocess import run
from pathlib import Path

from simple_parsing import ArgumentParser, field

from compiler.dll_gen import generate_python_interop_file
from compiler import PycCompiler


@dataclass(slots=True)
class BuildCommand:
    path: Path = field(positional=True, help='The path to build')

    def __post_init__(self):
        self.path = self.path.resolve()

    def execute(self, parser: ArgumentParser):
        if not self.path.exists():
            parser.error('path does not exist')

        if not self.path.is_file():
            parser.error('expected given path to be a file')

        src = self.path.read_text('utf8')
        
        compiler = PycCompiler(self.path)
        module = compiler.visit(ast.parse(src, filename=self.path))
        ir_file = self.path.with_suffix('.ll')
        ir_file.write_text(str(module))

        dll_file = self.path.with_suffix('.dll')
        run(['clang', str(ir_file), '-shared', '-o', str(dll_file), '-Wno-override-module'], shell=True, check=True)

        gen_file = self.path.with_stem(f'{self.path.stem}_gen')
        generate_python_interop_file(module, gen_file, dll_file)

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
