import ast
from pathlib import Path

from llvmlite import ir, binding as llvm


class PycCompiler(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.module = ir.Module(str(path), context=ir.Context())
        self.module.triple = llvm.get_default_triple()
        
        self.builder = ir.IRBuilder()
        
        self.path = path
    
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
        entry_block = func.append_basic_block('entry')
        previous_block = self.builder.block
        self.builder.position_at_end(entry_block)

        for stmt in node.body:
            self.visit(stmt)

        if previous_block is not None:
            self.builder.position_at_end(previous_block)
        
        return func

    def visit_Return(self, node: ast.Return):
        if node.value is None:
            return self.builder.ret_void()
        
        value = self.visit(node.value)
        return self.builder.ret(value)

    def visit_Constant(self, node: ast.Constant):
        match node.value:
            case int() as i:
                return ir.Constant(ir.IntType(32), i)
            case _:
                raise NotImplementedError(node.value)
