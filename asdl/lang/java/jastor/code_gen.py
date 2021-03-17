# -*- coding: utf-8 -*-
"""
Part of the astor library for Python AST manipulation.

License: 3-clause BSD

Copyright (c) 2008      Armin Ronacher
Copyright (c) 2012-2017 Patrick Maupin
Copyright (c) 2013-2017 Berker Peksag

This module converts an AST into Python source code.

Before being version-controlled as part of astor,
this code came from here (in 2012):

    https://gist.github.com/1250562

"""

from javalang.ast import Node
import math
import sys

from .op_util import get_op_symbol, get_op_precedence, Precedence
from .node_util import ExplicitNodeVisitor
from .string_repr import pretty_string, string_triplequote_repr
from .source_repr import pretty_source


def to_source(node, indent_with=' ' * 4, add_line_information=False,
              pretty_string=pretty_string, pretty_source=pretty_source):
    """This function can convert a node tree back into python sourcecode.
    This is useful for debugging purposes, especially if you're dealing with
    custom asts not generated by python itself.

    It could be that the sourcecode is evaluable when the AST itself is not
    compilable / evaluable.  The reason for this is that the AST contains some
    more data than regular sourcecode does, which is dropped during
    conversion.

    Each level of indentation is replaced with `indent_with`.  Per default this
    parameter is equal to four spaces as suggested by PEP 8, but it might be
    adjusted to match the application's styleguide.

    If `add_line_information` is set to `True` comments for the line numbers
    of the nodes are added to the output.  This can be used to spot wrong line
    number information of statement nodes.

    """
    generator = SourceGenerator(indent_with, add_line_information,
                                pretty_string)
    generator.visit(node)
    generator.result.append('\n')
    if set(generator.result[0]) == set('\n'):
        generator.result[0] = ''
    return pretty_source(generator.result)


def precedence_setter(AST=Node, get_op_precedence=get_op_precedence,
                      isinstance=isinstance, list=list):
    """ This only uses a closure for performance reasons,
        to reduce the number of attribute lookups.  (set_precedence
        is called a lot of times.)
    """

    def set_precedence(value, *nodes):
        """Set the precedence (of the parent) into the children.
        """
        if isinstance(value, Node):
            value = get_op_precedence(value)
        for node in nodes:
            if isinstance(node, Node):
                node._pp = value
            elif isinstance(node, list):
                set_precedence(value, *node)
            else:
                assert node is None, node

    return set_precedence


set_precedence = precedence_setter()


class Delimit(object):
    """A context manager that can add enclosing
       delimiters around the output of a
       SourceGenerator method.  By default, the
       parentheses are added, but the enclosed code
       may set discard=True to get rid of them.
    """

    discard = False

    def __init__(self, tree, *args):
        """ use write instead of using result directly
            for initial data, because it may flush
            preceding data into result.
        """
        delimiters = '()'
        node = None
        op = None
        for arg in args:
            if isinstance(arg, Node):
                if node is None:
                    node = arg
                else:
                    op = arg
            else:
                delimiters = arg
        tree.write(delimiters[0])
        result = self.result = tree.result
        self.index = len(result)
        self.closing = delimiters[1]
        if node is not None:
            self.p = p = get_op_precedence(op or node)
            self.pp = pp = tree.get__pp(node)
            self.discard = p >= pp

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        result = self.result
        start = self.index - 1
        if self.discard:
            result[start] = ''
        else:
            result.append(self.closing)


class SourceGenerator(ExplicitNodeVisitor):
    """This visitor is able to transform a well formed syntax tree into Python
    sourcecode.

    For more details have a look at the docstring of the `node_to_source`
    function.

    """

    using_unicode_literals = False

    def __init__(self, indent_with, add_line_information=False,
                 pretty_string=pretty_string,
                 # constants
                 len=len, isinstance=isinstance, callable=callable):
        self.result = []
        self.indent_with = indent_with
        self.add_line_information = add_line_information
        self.indentation = 0  # Current indentation level
        self.new_lines = 0  # Number of lines to insert before next code
        self.colinfo = 0, 0  # index in result of string containing linefeed, and
                             # position of last linefeed in that string
        self.pretty_string = pretty_string
        AST = Node

        visit = self.visit
        newline = self.newline
        result = self.result
        append = result.append

        def write(*params):
            """ self.write is a closure for performance (to reduce the number
                of attribute lookups).
            """
            for item in params:
                if isinstance(item, AST):
                    visit(item)
                elif callable(item):
                    item()
                elif item == '\n':
                    newline()
                else:
                    if self.new_lines:
                        append('\n' * self.new_lines)
                        self.colinfo = len(result), 0
                        append(self.indent_with * self.indentation)
                        self.new_lines = 0
                    if item:
                        append(item)

        self.write = write

    def __getattr__(self, name, defaults=dict(keywords=(),
                    _pp=Precedence.highest).get):
        """ Get an attribute of the node.
            like dict.get (returns None if doesn't exist)
        """
        if not name.startswith('get_'):
            raise AttributeError
        geta = getattr
        shortname = name[4:]
        default = defaults(shortname)

        def getter(node):
            return geta(node, shortname, default)

        setattr(self, name, getter)
        return getter

    def delimit(self, *args):
        return Delimit(self, *args)

    def conditional_write(self, *stuff):
        if stuff[-1] is not None:
            self.write(*stuff)
            # Inform the caller that we wrote
            return True

    def newline(self, node=None, extra=0):
        self.new_lines = max(self.new_lines, 1 + extra)
        if node is not None and self.add_line_information:
            self.write('# line: %s' % node.lineno)
            self.new_lines = 1

    def visit_arguments(self, node):
        want_comma = []

        def write_comma():
            if want_comma:
                self.write(', ')
            else:
                want_comma.append(True)

        def loop_args(args, defaults):
            set_precedence(Precedence.Comma, defaults)
            padding = [None] * (len(args) - len(defaults))
            for arg, default in zip(args, padding + defaults):
                self.write(write_comma, arg)
                self.conditional_write('=', default)

        loop_args(node.args, node.defaults)
        self.conditional_write(write_comma, '*', node.vararg)

        kwonlyargs = self.get_kwonlyargs(node)
        if kwonlyargs:
            if node.vararg is None:
                self.write(write_comma, '*')
            loop_args(kwonlyargs, node.kw_defaults)
        self.conditional_write(write_comma, '**', node.kwarg)

    def statement(self, node, *params, **kw):
        self.newline(node)
        self.write(*params)

    def decorators(self, node, extra):
        self.newline(extra=extra)
        for decorator in node.decorator_list:
            self.statement(decorator, '@', decorator)

    def comma_list(self, items, trailing=False):
        # set_precedence(Precedence.Comma, *items)
        for idx, item in enumerate(items):
            self.write(', ' if idx else '', item)
        self.write(',' if trailing else '')

    # Statements

    def visit_CompilationUnit(self, node):
        if node.package:
            self.write(node.package)
        if node.imports:
            for imp in node.imports:
                self.write(imp)
        if node.types:
            for type in node.types:
                self.write(type)

    def visit_Annotation(self, node):
        self.write('@', node.name, ' ')

    def visit_PackageDeclaration(self, node):
        if node.documentation:
            self.write(node.documentation)
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        self.write('package ', node.name, ';')

    def visit_ClassDeclaration(self, node):
        if node.documentation:
            self.write(node.documentation)
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        self.write('class', ' ')
        if node.type_parameters:
            self.write('< ', node.name)
            self.comma_list(node.type_parameters)
            self.write(' >')
        self.write(node.name)
        if node.extends:
            self.write('extends')
            self.write(node.extends)
        if node.implements:
            self.write('implements ')
            self.comma_list(node.implements)
        if node.body:
            self.write(' {')
            for element in node.body:
                self.write(element)
            self.write('}')

    def visit_MethodDeclaration(self, node):
        if node.documentation:
            self.write(node.documentation)
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        if node.return_type:
            self.write(node.return_type, " ")
        else:
            self.write("void ")
        if node.type_parameters:
            self.write('< ', node.name)
            self.comma_list(node.type_parameters)
            self.write(' >')
        self.write(node.name)
        if node.parameters:
            self.write('(')
            self.comma_list(node.parameters)
            self.write(')')
        if node.throws:
            self.write(' throws ')
            self.comma_list(node.throws)
        if node.body:
            self.write(node.body)

    # ConstructorDeclaration(fieldmodifier* modifiers, annotation* annotations, string? documentation, type_parameter* type_parameters, identifier name, parameter* parameters, identifier* throws, statement* body)
    def visit_ConstructorDeclaration(self, node):
        if node.documentation:
            self.write(node.documentation)
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        if node.type_parameters:
            self.write('< ', node.name)
            self.comma_list(node.type_parameters)
            self.write(' >')
        self.write(node.name)
        if node.parameters:
            self.write('(')
            self.comma_list(node.parameters)
            self.write(')')
        if node.throws:
            self.write(' throws ')
            self.comma_list(node.throws)
        if node.body:
            self.write(node.body)

    # FieldDeclaration(string? documentation, fieldmodifier* modifiers,
    # annotation* annotations, type type, declarator* declarators)
    def visit_FieldDeclaration(self, node):
        if node.documentation:
            self.write(node.documentation)
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        self.write(node.type, ' ')
        if node.declarators:
            self.comma_list(node.declarators)
        self.write(';')

    # ConstantDeclaration(string? documentation, fieldmodifier* modifiers,
    # annotation* annotations, type type, declarator* declarators)
    def visit_ConstantDeclaration(self, node):
        if node.documentation:
            self.write(node.documentation)
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        self.write(node.type, ' ')
        if node.declarators:
            self.comma_list(node.declarators)
        self.write(';')

    def visit_ReferenceType(self, node):
        self.write(node.name)
        if node.dimensions:
            for _ in range(len(node.dimensions)):
                self.write("[]")

    def visit_VariableDeclarator(self, node):
        self.write(" ", node.name)
        if node.initializer:
            self.write(" = ", node.initializer)

    def visit_ArrayInitializer(self, node):
        self.write("{")
        if node.initializers:
            self.comma_list(node.initializers)
        self.write("}")

    def visit_Literal(self, node):
        for op in node.prefix_operators:
            self.write(op)
        if node.qualifier:
            self.write(node.qualifier, ".")
        self.write(node.value)
        if node.selectors:
            for selector in node.selectors:
                self.write(selector)
        for op in node.postfix_operators:
            self.write(op)

    def visit_FormalParameter(self, node):
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        self.write(node.type, ' ', node.name)

    def visit_Statement(self, node):
        if node.label:
            self.write(node.label, ": ")
        self.write(";")

    def visit_StatementExpression(self, node):
        if node.label:
            self.write(node.label, ": ")
        self.write(node.expression, ";")

    def visit_TernaryExpression(self, node):
        self.write(node.condition, " ? ", node.if_true, " : ", node.if_false)

    def visit_MethodInvocation(self, node):
        if node.prefix_operators:
          for op in node.prefix_operators:
              self.write(op)
        if node.qualifier:
            self.write(node.qualifier, ".")
        self.write(node.member)
        if node.type_arguments:
            self.comma_list(node.type_arguments)
        if node.selectors:
            for selector in node.selectors:
                self.write(selector)
        self.write("(")
        self.comma_list(node.arguments)
        self.write(")")
        if node.postfix_operators:
            for op in node.postfix_operators:
                self.write(op)
        self.write(';')

    def visit_ForStatement(self, node):
        self.write("for (")
        self.write(node.control)
        self.write(") ")
        self.write(node.body)

    def visit_WhileStatement(self, node):
        self.write("while (")
        self.write(node.condition)
        self.write(")")
        self.write(node.body)

    def visit_DoStatement(self, node):
        self.write("do")
        self.write(node.body)
        self.write("while (")
        self.write(node.condition)
        self.write(") ")
        self.write(";")

    def visit_AssertStatement(self, node):
        self.write("assert")
        self.write(node.condition)
        if node.value:
            self.write(":")
            self.write(node.value)
        self.write(";")

    def visit_SynchronizedStatement(self, node):
        self.write("synchronized")
        self.write("(")
        self.write(node.lock)
        self.write(") ")
        self.write(node.block)

    def visit_ForControl(self, node):
        if node.init:
            self.comma_list(node.init)
        self.write("; ")
        if node.condition:
            self.write(node.condition)
        self.write("; ")
        if node.update:
            self.comma_list(node.update)

    def visit_StatementExpressionList(self, node):
        self.comma_list(node.statement)

    def visit_VariableDeclaration(self, node):
        self.write(node.type, " ")
        self.comma_list(node.declarators)
        self.write(';')

    def visit_BinaryOperation(self, node):
        self.write(node.operandl)
        # self.write(" ", get_op_symbol(node.operator, ' %s '), " ")
        self.write(" ", node.operator, " ")
        self.write(node.operandr)

    def visit_MemberReference(self, node):
        if node.prefix_operators:
            for op in node.prefix_operators:
                # self.write(get_op_symbol(op, ' %s '))
                self.write(op.operator)
        if node.qualifier:
            self.write(node.qualifier, ".")
        self.write(node.member)
        if node.selectors:
            for selector in node.selectors:
                self.write(selector)
        if node.postfix_operators:
            for op in node.postfix_operators:
                # self.write(get_op_symbol(op, ' %s '))
                self.write(op.operator)

    def visit_BasicType(self, node):
        self.write(node.name)
        if node.dimensions:
            for _ in range(len(node.dimensions)):
                self.write("[]")

    def visit_Void(self, node):
        self.write("void")

    def visit_ArraySelector(self, node):
        self.write("[", node.index, "]")

    def visit_Modifier(self, node):
        self.write(node.value, " ")

    # ['modifiers', 'annotations', 'type', 'declarators']
    def visit_LocalVariableDeclaration(self, node):
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        self.write(node.type, ' ')
        self.comma_list(node.declarators)
        self.write(';')

    def visit_Operator(self, node):
        self.write(node.operator)

    # Import(identifier path, identifier static, identifier wildcard)
    def visit_Import(self, node):
        self.write('import ')
        if node.static:
            self.write('static ')
        self.write(node.path)
        if node.wildcard:
            self.write('.*',)
        self.write(';', '\n')

    # Assignment(expression expressionl, expression value,
    # assign_operator type)
    def visit_Assignment(self, node):
        self.write(node.expressionl, node.type, node.value)

    # This(prefix_operator* prefix_operators,
    # postfix_operator* postfix_operators, identifier? qualifier,
    # selector* selectors)
    def visit_This(self, node):
        for op in node.prefix_operators:
            self.write(op.operator)
        if node.qualifier:
            self.write(node.qualifier, ".")
        if node.selectors:
            for selector in node.selectors:
                self.write(selector)
        for op in node.postfix_operators:
            self.write(op.operator)

    # ReturnStatement(identifier* label, expression expression)
    def visit_ReturnStatement(self, node):
        if node.label:
            self.write(node.label, ": ")
        self.write('return ', node.expression, ";", '\n')

    # IfStatement(identifier? label, expression condition, statement then_statement, statement else_statement)
    def visit_IfStatement(self, node):
        if node.label:
            self.write(node.label, ': ')
        self.write(node.condition, ' ')
        self.write(node.then_statement)
        if node.else_statement:
            self.write(node.else_statement)

    # BlockStatement(identifier? label, statement* statements)
    def visit_BlockStatement(self, node):
        if node.label:
            self.write(node.label, ": ")
        self.write('{', '\n')
        for statement in node.statements:
            self.write(statement)
        self.write('}', '\n')

    # EnhancedForControl(expression var, statement iterable)
    def visit_EnhancedForControl(self, node):
        self.write(node.var, " : ", node.iterable)

    # Cast(type type, expression expression)
    def visit_Cast(self, node):
        self.write('(', node.type, ") ", node.expression)

    # TryStatement(identifier? label, identifier? resources, statement* block, catch* catches, statement? finally_block)
    def visit_TryStatement(self, node):
        if node.label:
            self.write(node.label, ": ")
        self.write('try')
        if node.resources:
            self.write('(')
            for idx, item in enumerate(node.resources):
                self.write('; ' if idx else '', item)
            self.write(')')
        self.write(node.block)
        if node.catches:
            for clause in node.catches:
                self.write(clause)
        if node.finally_block:
            self.write('finally', node.finally_block)

    def visit_TryResource(self, node):
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')

    # CatchClause(identifier? label, catch_clause_parameter parameter, statement* block)
    def visit_CatchClause(self, node):
        if node.label:
            self.write(node.label, ": ")
        self.write('catch (', node.parameter, ')', node.block)

    # CatchClauseParameter(fieldmodifier* modifiers, annotation* annotations, identifier* types, identifier name)
    def visit_CatchClauseParameter(self, node):
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        self.write('.'.join(node.types), ' ', node.name)

    # ThrowStatement(identifier? label, expression expression)
    def visit_ThrowStatement(self, node):
        if node.label:
            self.write(node.label, ": ")
        self.write('throw ', node.expression, ';')

    # SuperConstructorInvocation(prefix_operator* prefix_operators, postfix_operator* postfix_operators, identifier? qualifier, selector* selectors, type_argument* type_arguments, argument* arguments)
    def visit_SuperConstructorInvocation(self, node):
        if node.prefix_operators:
            for op in node.prefix_operators:
                self.write(op)
        if node.qualifier:
            self.write(node.qualifier, ".")
        if node.type_arguments:
            self.comma_list(node.type_arguments)
        if node.selectors:
            for selector in node.selectors:
                self.write(selector)
        self.write("(")
        self.comma_list(node.arguments)
        self.write(")")
        if node.postfix_operators:
            for op in node.postfix_operators:
                self.write(op)

    # ClassCreator(prefix_operator* prefix_operators, postfix_operator* postfix_operators, identifier? qualifier, selector* selectors, type type, identifier* constructor_type_arguments, argument* arguments, statement* body)
    def visit_ClassCreator(self, node):
        if node.prefix_operators:
            for op in node.prefix_operators:
                self.write(op)
        if node.qualifier:
            self.write(node.qualifier, ".")
        if node.constructor_type_arguments:
            self.comma_list(node.constructor_type_arguments)
        if node.selectors:
            for selector in node.selectors:
                self.write(selector)
        self.write(node.type)
        self.write("(")
        if node.arguments:
            self.comma_list(node.arguments)
        self.write(")")
        if node.body:
            self.write("{")
            for statement in node.body:
                self.write(statement)
            self.write("}")
        if node.postfix_operators:
            for op in node.postfix_operators:
                self.write(op)

    # LambdaExpression(parameter* parameters, statement body)
    def visit_LambdaExpression(self, node):
        self.write("(")
        if node.parameters:
            self.comma_list(node.parameters)
        self.write(") -> ", node.body)

    def visit_InferredFormalParameter(self, node):
        self.write(node.name)

    def visit_SwitchStatement(self, node):
        if node.label:
            self.write(node.label, ": ")
        self.write('(', node.expression, ') {')
        for case in node.cases:
            self.write(case)
        self.write('}')

    def visit_SwitchStatementCase(self, node):
        self.write('case ')
        self.comma_list(node.case)
        for statement in node.statements:
            self.write(statement)

    def visit_StaticInitializer(self, node):
        self.write('static', node.block)

    def visit_InstanceInitializer(self, node):
        self.write(node.block)

    # ClassReference(prefix_operator* prefix_operators, postfix_operator* postfix_operators, identifier? qualifier, selector* selectors, type type)
    def visit_ClassReference(self, node):
        # TypeExtractor.class.getCanonicalName()
        for op in node.prefix_operators:
            self.write(op)
        if node.qualifier:
            self.write(node.qualifier, ".")
        self.write(node.type, '.class')
        if node.selectors:
            for selector in node.selectors:
                self.write(selector)
        for op in node.postfix_operators:
            self.write(op)

    # MethodReference(expression expression, identifier method, type_argument* type_arguments)
    def visit_MethodReference(self, node):
        self.write(node.expression, '::', node.method)
        if node.type_arguments:
            raise Exception("TODO MethodReference type_arguments")

    def visit_TypeParameter(self, node):
        self.write(node.name)
        if node.extends:
            self.write(' extends ')
            self.comma_list(node.extends)

    def visit_TypeArgument(self, node):
        self.write(node.pattern_type, ' ', node.type)

    # Primary(prefix_operator* prefix_operators, postfix_operator* postfix_operators, identifier? qualifier, selector* selectors)
    def visit_Primary(self, node):
        raise Exception("TODO Primary")

    # ExplicitConstructorInvocation(prefix_operator* prefix_operators, postfix_operator* postfix_operators, identifier? qualifier, selector* selectors, type_argument* type_arguments, argument* arguments)
    def visit_ExplicitConstructorInvocation(self, node):
        raise Exception("TODO ExplicitConstructorInvocation")

    def visit_SuperMethodInvocation(self, node):
        if node.prefix_operators:
          for op in node.prefix_operators:
              self.write(op)
        self.write('super.')
        if node.qualifier:
            self.write(node.qualifier, ".")
        self.write(node.member)
        if node.type_arguments:
            self.comma_list(node.type_arguments)
        if node.selectors:
            for selector in node.selectors:
                self.write(selector)
        self.write("(")
        self.comma_list(node.arguments)
        self.write(")")
        if node.postfix_operators:
            for op in node.postfix_operators:
                self.write(op)

    def visit_BreakStatement(self, node):
        if node.label:
            self.write(node.label, ": ")
        self.write('break')
        if node.goto:
            self.write(node.goto)
        self.write(';', '\n')

    def visit_ContinueStatement(self, node):
        if node.label:
            self.write(node.label, ": ")
        self.write('continue')
        if node.goto:
            self.write(node.goto)
        self.write(';', '\n')

    # public interface AssociableToASTTest<T extends Node> {
    # public interface ResolvedAnnotationDeclarationTest extends ResolvedReferenceTypeDeclarationTest {
    # ['modifiers', 'annotations', 'documentation', 'name', 'body', 'type_parameters', 'extends']
    def visit_InterfaceDeclaration(self, node):
        if node.documentation:
            self.write(node.documentation)
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        self.write('interface', ' ')
        if node.type_parameters:
            self.write('< ', node.name)
            self.comma_list(node.type_parameters)
            self.write(' >')
        self.write(node.name)
        if node.extends:
            self.write('extends ')
            self.comma_list(node.extends)
        if node.body:
            self.write(' {')
            for element in node.body:
                self.write(element)
            self.write('}')

    def visit_AnnotationDeclaration(self, node):
        if node.documentation:
            self.write(node.documentation)
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        self.write('@interface', ' ')
        self.write(node.name)
        if node.body:
            self.write(' {')
            for element in node.body:
                self.write(element)
            self.write('}')

    # AnnotationMethod(fieldmodifier* modifiers, annotation* annotations, identifier name", type return_type, int* dimensions, identifier? default)
    def visit_AnnotationMethod(self, node):
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        if node.return_type:
            self.write(node.return_type, " ")
        self.write(node.name)
        if node.dimensions:
            for _ in range(len(node.dimensions)):
                self.write("[]")
        if node.default:
            self.write('=')
            self.write(node.default)

    def visit_SuperMemberReference(self, node):
        if node.prefix_operators:
            for op in node.prefix_operators:
                self.write(op)
        if node.qualifier:
            self.write(node.qualifier, ".")
        self.write(node.member)
        if node.selectors:
            for selector in node.selectors:
                self.write(selector)
        if node.postfix_operators:
            for op in node.postfix_operators:
                self.write(op)
        self.write(';')

    # ExplicitConstructorInvocation(prefix_operator* prefix_operators,
    # postfix_operator* postfix_operators, identifier? qualifier,
    # selector* selectors, type_argument* type_arguments, argument* arguments)
    def visit_ExplicitConstructorInvocation(self, node):
        if node.prefix_operators:
            for op in node.prefix_operators:
                self.write(op)
        if node.qualifier:
            self.write(node.qualifier, ".")
        if node.type_arguments:
            self.comma_list(node.type_arguments)
        if node.selectors:
            for selector in node.selectors:
                self.write(selector)
        self.write("(")
        self.comma_list(node.arguments)
        self.write(")")
        if node.postfix_operators:
            for op in node.postfix_operators:
                self.write(op)
        self.write(';')

    # enumdeclaration = EnumDeclaration(fieldmodifier* modifiers, annotation* annotations, string? documentation ,identifier name, dottedname* implements, enumbody body)
    def visit_EnumDeclaration(self, node):
        if node.documentation:
            self.write(node.documentation)
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        self.write('enum', node.name)
        self.write(node.body)
        if node.implements:
            self.write('implements')
            self.comma_list(node.implements)

    #enumbody = EnumBody(enumconstant* constants, enumdeclaration* declarations)
    def visit_EnumBody(self, node):
        self.write('{')
        self.comma_list(node.constants)
        self.write(';')
        if node.declarations:
            for declaration in node.declarations:
                self.write(declaration)
        self.write('}')

    # enumconstant = EnumConstantDeclaration(annotation* annotations, string? documentation, fieldmodifier* modifiers, identifier name, argument* arguments, statement body)
    def visit_EnumConstantDeclaration(self, node):
        if node.documentation:
            self.write(node.documentation)
        if node.modifiers:
            for modifier in node.modifiers:
                self.write(modifier, ' ')
        if node.annotations:
            for annotation in node.annotations:
                self.write(annotation, ' ')
        self.write(node.name)
        if node.arguments:
            self.write('(')
            self.comma_list(node.arguments)
            self.write(')')
        if node.body:
            self.write(' {')
            for element in node.body:
                self.write(element)
            self.write('}')

    # ['prefix_operators', 'postfix_operators', 'qualifier', 'selectors', 'type', 'dimensions', 'initializer']
    def visit_ArrayCreator(self, node):
        if node.prefix_operators:
            for op in node.prefix_operators:
                self.write(op)
        if node.qualifier:
            self.write(node.qualifier, ".")
        if node.selectors:
            for selector in node.selectors:
                self.write(selector)
        self.write(node.type)
        if node.dimensions:
            for dim in node.dimensions:
                self.write("[")
                self.write(dim)
                self.write("]")
        if node.initializer:
              self.write(node.initializer)
        if node.postfix_operators:
            for op in node.postfix_operators:
                self.write(op)
        self.write(';')

    # InnerClassCreator(prefix_operator* prefix_operators, postfix_operator* postfix_operators, identifier? qualifier, selector* selectors, type type, identifier* constructor_type_arguments, argument* arguments, statement body)
    def visit_InnerClassCreator(self, node):
        if node.prefix_operators:
            for op in node.prefix_operators:
                self.write(op)
        if node.qualifier:
            self.write(node.qualifier, ".")
        if node.constructor_type_arguments:
            self.comma_list(node.constructor_type_arguments)
        if node.selectors:
            for selector in node.selectors:
                self.write(selector)
        self.write('class')
        self.write(node.type)
        self.write("(")
        if node.arguments:
            self.comma_list(node.arguments)
        self.write(")")
        if node.body:
            self.write("{")
            for statement in node.body:
                self.write(statement)
            self.write("}")
        if node.postfix_operators:
            for op in node.postfix_operators:
                self.write(op)

    ## Primary(prefix_operator* prefix_operators, postfix_operator* postfix_operators, identifier? qualifier, selector* selectors)
    #def visit_Primary(self, node):
        #raise Exception("TODO Primary")

