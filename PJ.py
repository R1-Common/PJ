import ast
import astor

class LuaCompiler(ast.NodeTransformer):
    def __init__(self):
        self.scope_stack = []

    def visit_FunctionDef(self, node):
        # Add an additional statement at the beginning of each function
        extra_stmt = ast.Expr(value=ast.Call(
            func=ast.Name(id='print', ctx=ast.Load()),
            args=[ast.Str(s='This is an additional statement.')],
            keywords=[]
        ))
        node.body.insert(0, extra_stmt)
        return self.generic_visit(node)

    def visit_If(self, node):
        # Transform an 'if' statement into an 'if-elseif' chain for Lua compatibility
        if len(node.orelse) == 0:
            return node

        if_stmt = ast.If(test=node.test, body=node.body, orelse=[])
        current_if = if_stmt

        for orelse in node.orelse:
            if isinstance(orelse, ast.If):
                current_if.orelse.append(orelse)
                current_if = orelse
            else:
                current_if.orelse.append(ast.If(test=orelse.test, body=orelse.body, orelse=[]))
                current_if = current_if.orelse[0]

        return if_stmt

    def visit_For(self, node):
        # Transform a 'for' loop into a 'while' loop for Lua compatibility
        target = node.target.id
        start = ast.Constant(value=node.iter.args[0], kind=None)
        stop = ast.Constant(value=node.iter.args[1], kind=None)
        step = ast.Constant(value=node.iter.args[2], kind=None) if len(node.iter.args) > 2 else None

        init_assign = ast.Assign(
            targets=[ast.Name(id=target, ctx=ast.Store())],
            value=start
        )

        loop_condition = ast.Compare(
            left=ast.Name(id=target, ctx=ast.Load()),
            ops=[ast.Lt()],
            comparators=[stop]
        )

        loop_body = node.body

        if step:
            loop_body.append(ast.Assign(
                targets=[ast.Name(id=target, ctx=ast.Store())],
                value=ast.BinOp(
                    left=ast.Name(id=target, ctx=ast.Load()),
                    op=ast.Add(),
                    right=step
                )
            ))
        else:
            loop_body.append(ast.AugAssign(
                target=ast.Name(id=target, ctx=ast.Store()),
                op=ast.Add(),
                value=ast.Constant(value=1, kind=None)
            ))

        while_loop = ast.While(
            test=loop_condition,
            body=loop_body,
            orelse=[]
        )

        return [init_assign, while_loop]

    def visit_Assign(self, node):
        # Transform an assignment statement with multiple targets into separate statements in Lua
        if len(node.targets) > 1:
            assign_stmts = []
            for target in node.targets:
                assign_stmt = ast.Assign(targets=[target], value=node.value)
                assign_stmts.append(assign_stmt)
            return assign_stmts
        return self.generic_visit(node)

    def visit_BinOp(self, node):
        # Transform Python's '//' floor division operator to Lua's '/' operator
        if isinstance(node.op, ast.FloorDiv):
            node.op = ast.Div()
        return self.generic_visit(node)

    def visit_UnaryOp(self, node):
        # Transform Python's 'not' operator to Lua's 'not' operator
        if isinstance(node.op, ast.Not):
            node.op = ast.Not()
        return self.generic_visit(node)

    def visit_Compare(self, node):
        # Transform Python's 'in' operator to Lua's '==' operator
        if isinstance(node.ops[0], ast.In):
            node.ops[0] = ast.Eq()
        return self.generic_visit(node)

    def visit_Call(self, node):
        # Transform Python's 'len' function to Lua's equivalent 'string.len' or 'table.getn' function
        if isinstance(node.func, ast.Name) and node.func.id == 'len':
            if isinstance(node.args[0], ast.Str):
                node.func.id = 'string.len'
            else:
                node.func.id = 'table.getn'
        return self.generic_visit(node)

    def visit_Return(self, node):
        # Transform a 'return' statement into an assignment to a special variable for Lua compatibility
        if not self.scope_stack:
            return node

        scope = self.scope_stack[-1]
        if scope == 'function':
            assign_stmt = ast.Assign(
                targets=[ast.Name(id='_retval', ctx=ast.Store())],
                value=node.value
            )
            return [assign_stmt, ast.Return(value=ast.Name(id='_retval', ctx=ast.Load()))]
        return node

    def visit_FunctionDef(self, node):
        # Add an additional statement at the beginning of each function
        extra_stmt = ast.Expr(value=ast.Call(
            func=ast.Name(id='print', ctx=ast.Load()),
            args=[ast.Str(s='This is an additional statement.')],
            keywords=[]
        ))
        node.body.insert(0, extra_stmt)
        return self.generic_visit(node)

def compile_lua(code):
    try:
        parsed_ast = ast.parse(code)
        transformed_ast = LuaCompiler().visit(parsed_ast)
        compiled_code = astor.to_source(transformed_ast)
        return compiled_code
    except SyntaxError as e:
        print(f"Syntax error: {e}")
        return None

# Example usage
lua_code = """
function greet()
    print("Hello, World!")
end

if a == 1 then
    print("A is 1")
elseif a == 2 then
    print("A is 2")
else
    print("A is not 1 or 2")
end

for i in range(1, 5):
    print("Iteration:", i)

local x, y = 1, 2

local result = not (x == y) // (x + y in {3, 4})

local str = "Hello, Lua"
local str_length = len(str)
print("String length:", str_length)

local arr = {1, 2, 3, 4, 5}
local arr_length = len(arr)
print("Array length:", arr_length)

-- Additional statements
local function additional_statement()
    print("This is an additional function.")
end

additional_statement()
"""

compiled_code = compile_lua(lua_code)
if compiled_code:
    print(compiled_code)
