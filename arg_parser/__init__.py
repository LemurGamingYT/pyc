from typing import Optional, Iterable

from simple_parsing import ArgumentParser

from arg_parser.commands import BuildCommand, BenchmarkCommand


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
