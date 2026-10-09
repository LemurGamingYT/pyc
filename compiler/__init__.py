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
                return Object(ir.IntType(32), int)
            case 'float':
                return Object(ir.FloatType(), float)
            case 'bool':
                return Object(ir.IntType(1), bool)
            case _:
                if node.id in self.scope.symbols:
                    symbol = self.scope.symbols[node.id]
                    ptr = symbol.value
                    return Object(self.builder.load(ptr, name=node.id), symbol.type)
                
                raise NotImplementedError(node.id)

    def visit_arguments(self, node: ast.arguments):
        return [self.visit(arg) for arg in node.args]

    def visit_arg(self, node: ast.arg):
        assert node.annotation is not None, 'expected parameter type'
        return (self.visit(node.annotation), node.arg)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        assert node.returns is not None, 'expected function return type'

        ret_type_object = self.visit(node.returns)
        ret_type = ret_type_object.value
        params = self.visit(node.args)
        func = ir.Function(self.module, ir.FunctionType(ret_type, [param[0].value for param in params]), node.name) # TODO: args
        for arg, (_, name) in zip(func.args, params):
            arg.name = f'param.{name}'

        self.scope.symbols[node.name] = Symbol(Any, SymbolKind.FUNCTION, Object(func, ret_type_object.type))
        
        entry_block = func.append_basic_block('entry')
        previous_block = self.builder.block
        self.builder.position_at_end(entry_block)

        with self.child_scope():
            for i, (type, name) in enumerate(params):
                ptr = self.builder.alloca(type.value, name=f'{name}.addr')
                self.builder.store(func.args[i], ptr)
                
                self.scope.symbols[name] = Symbol(type.type, SymbolKind.VARIABLE, ptr)
            
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

    def visit_Call(self, node: ast.Call):
        name = cast(ast.Name, node.func).id
        symbol = self.scope.symbols[name]
        assert symbol.kind == SymbolKind.FUNCTION

        func = symbol.value
        args = [self.visit(arg).value for arg in node.args]
        return Object(self.builder.call(func.value, args, name), func.type)

    def add_ints(self, a: Object, b: Object):
        return Object(self.builder.add(a.value, b.value, 'int + int'), int)

    def sub_ints(self, a: Object, b: Object):
        return Object(self.builder.sub(a.value, b.value, 'int - int'), int)

    binop_method = {
        ast.Add: {
            (int, int): add_ints
        },
        ast.Sub: {
            (int, int): sub_ints
        }
    }

    def visit_BinOp(self, node: ast.BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)

        method = self.binop_method[node.op.__class__][(left.type, right.type)]
        return method(self, left, right)
