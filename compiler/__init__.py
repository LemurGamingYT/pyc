import ast
from contextlib import contextmanager
from typing import Any, cast
from pathlib import Path

from llvmlite import ir, binding as llvm

from compiler.context import Scope, Symbol, Object, SymbolKind


class PycCompiler(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.module = ir.Module(str(path), context=ir.Context())
        self.module.triple = llvm.get_default_triple()
        
        self.builder = ir.IRBuilder()
        
        self.path = path

        self.scope = Scope()

    @contextmanager
    def child_scope(self):
        outer_scope = self.scope
        self.scope = outer_scope.clone()
        yield
        self.scope = outer_scope
    
    def visit_Module(self, node: ast.Module):
        for stmt in node.body:
            self.visit(stmt)

        return self.module

    def visit_Name(self, node: ast.Name):
        match node.id:
            case 'int':
                return ir.IntType(32)
            case 'float':
                return ir.FloatType()
            case 'bool':
                return ir.IntType(1)
            case _:
                raise NotImplementedError(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        assert node.returns is not None, 'expected function return type'

        ret_type = self.visit(node.returns)
        func = ir.Function(self.module, ir.FunctionType(ret_type, []), node.name) # TODO: args

        self.scope.symbols[node.name] = Symbol(Any, SymbolKind.FUNCTION, func)
        
        entry_block = func.append_basic_block('entry')
        previous_block = self.builder.block
        self.builder.position_at_end(entry_block)

        with self.child_scope():
            for stmt in node.body:
                self.visit(stmt)

        if previous_block is not None:
            self.builder.position_at_end(previous_block)
        
        return func

    def visit_Assign(self, node: ast.Assign):
        name = cast(ast.Name, node.targets[0]).id
        value = self.visit(node.value)
        ptr = self.builder.alloca(value.value.type, name=f'{name}.addr')
        self.builder.store(value.value, ptr)
        
        self.scope.symbols[name] = Symbol(value.type, SymbolKind.VARIABLE, ptr)

    def visit_Return(self, node: ast.Return):
        if node.value is None:
            return self.builder.ret_void()
        
        value = self.visit(node.value)
        return self.builder.ret(value.value)

    def visit_Constant(self, node: ast.Constant):
        match node.value:
            case int() as i:
                return Object(ir.Constant(ir.IntType(32), i), int)
            case _:
                raise NotImplementedError(node.value)
