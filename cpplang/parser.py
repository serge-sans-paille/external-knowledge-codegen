import json
import re
import shutil
import subprocess
import sys
import os
from typing import (List, Set, Tuple)



from . import util
from . import tree

ENABLE_DEBUG_SUPPORT = True

preprocess_command = [
    shutil.which("clang"), "-x", "c++", "-std=c++17",
    "-E", "-"]

module_dir = os.path.dirname(__file__)
plugin_path = os.path.join(module_dir, "JSONTypeDumper.so")

def rebuild_clang_plugin():
    plugin_src = os.path.join(module_dir, "JSONDumpTypes.cpp")

    src_mtime = os.path.getmtime(plugin_src)
    try:
        plugin_mtime = os.path.getmtime(plugin_path)
    except:
        plugin_mtime = 0

    if src_mtime > plugin_mtime:
        raw_llvm_compile_flags = subprocess.check_output(
                [shutil.which("llvm-config"), '--cxxflags', '--ldflags'])
        llvm_compile_flags = raw_llvm_compile_flags.split()
        subprocess.check_call([
            shutil.which("clang"),
            plugin_src,
            "-O2", "-fPIC",
            "-shared",
            "-o", plugin_path] + llvm_compile_flags)

rebuild_clang_plugin()

def parse_debug(method):
    global ENABLE_DEBUG_SUPPORT

    if ENABLE_DEBUG_SUPPORT:
        def _method(self, node):
            if not hasattr(self, 'recursion_depth'):
                self.recursion_depth = 0

            if self.debug:
                depth = "%02d" % (self.recursion_depth,)
                token = self.get_node_source_code(node)
                start_value = self.get_node_source_code(node)
                name = method.__name__
                sep = ("-" * self.recursion_depth)
                e_message = ""

                print("%s %s> %s(%s)" % (depth, sep, name, token))

                self.recursion_depth += 1

                try:
                    r = method(self, node)

                except CppSyntaxError as e:
                    e_message = e.description
                    raise

                except Exception as e:
                    e_message = e.__repr__()
                    raise

                finally:
                    if self.stack:
                        token = self.get_node_source_code(self.stack[-1])
                    else:
                        token = ""
                    print(f"{depth} <{sep} {name}({start_value}, {token}) {e_message}")
                    self.recursion_depth -= 1
            else:
                self.recursion_depth += 1
                try:
                    r = method(self, node)
                finally:
                    self.recursion_depth -= 1

            return r

        return _method

    else:
        return method

# ------------------------------------------------------------------------------
# ---- Parsing exception ----

class CppParserBaseException(Exception):
    def __init__(self, message=''):
        super(CppParserBaseException, self).__init__(message)

class CppSyntaxError(CppParserBaseException):
    def __init__(self, description, at=None):
        super(CppSyntaxError, self).__init__()

        self.description = description
        self.at = at

class CppParserError(CppParserBaseException):
    pass

# ------------------------------------------------------------------------------
# ---- Parser class ----

class Parser(object):
    operator_precedence = [ set(('||',)),
                            set(('&&',)),
                            set(('|',)),
                            set(('^',)),
                            set(('&',)),
                            set(('==', '!=')),
                            set(('<', '>', '>=', '<=', 'instanceof')),
                            set(('<<', '>>', '>>>')),
                            set(('+', '-')),
                            set(('*', '/', '%'))]

    def __init__(self, cpp_code, filepath=None):
        try:
            self.filepath = filepath
            # TODO replace in commandss below the include path by thosee given by the
            # C++ project build system
            preprocess = subprocess.run(
                preprocess_command,
                capture_output=True,
                input=cpp_code.encode(),
                check=True)
        except subprocess.CalledProcessError as e:
            if self.filepath is not None:
                print(f"While handling {self.filepath},\n")
            print(f"Preprocessing error {e.returncode}:\n{e.stderr.decode()}", file=sys.stderr)
            raise
        preprocess_stdout_data = preprocess.stdout
        # if ENABLE_DEBUG_SUPPORT:
        #     print(f"\npreprocess_stdout_data:\n{preprocess_stdout_data.decode()}\n",
        #           file=sys.stderr)
        preprocess_stderr_data = preprocess.stderr
        process_command = [
            shutil.which("clang"), "-x", "c++", "-std=c++17",
            "-fplugin={}".format(plugin_path),
            "-fsyntax-only", "-"]
        # if ENABLE_DEBUG_SUPPORT:
        #     print(f"process_command:\n{' '.join(process_command)}\n\n", file=sys.stderr)
        try:
            p = subprocess.run(
                process_command,
                capture_output=True,
                input=preprocess_stdout_data,
                check=True)
        except subprocess.CalledProcessError as e:
            if self.filepath is not None:
                print(f"While handling {self.filepath},\n")
            print(f"Parsing error {e.returncode}:\n{e.stderr.decode()}", file=sys.stderr)
            print(f"    command was:\n{' '.join(process_command)}", file=sys.stderr)
            raise
        stdout_data = p.stdout
        # if ENABLE_DEBUG_SUPPORT:
        #     print(f"stdout_data:\n{stdout_data.decode()}\n\n", file=sys.stderr)
        stderr_data = p.stdout
        # print(stderr_data.decode(), file=sys.stderr)
        self.tu = json.loads(stdout_data.decode())
        self.type_informations = {}
        self.asm_informations = {}
        self.stack = []
        self.debug = False
        self.anonymous_types = {}
        self.parsed_gotos = {}
        self.parsed_labels = {}
        self.source_code = preprocess_stdout_data.decode()

# ------------------------------------------------------------------------------
# ---- Debug control ----

    def set_debug(self, debug=True):
        self.debug = debug

# ------------------------------------------------------------------------------
# ---- Parsing entry point ----

    def parse(self) -> tree.TranslationUnit:
        self.parse_type_summary(self.tu["TypeSummary"])
        return self.parse_TranslationUnit(self.tu["Content"])

# ------------------------------------------------------------------------------
# ---- Helper methods ----

    #def illegal(self, description, at=None):
        #if not at:
            #at = self.tokens.look()

        #raise CppSyntaxError(description, at)

    #def accept(self, *accepts):
        #last = None

        #if len(accepts) == 0:
            #raise CppParserError("Missing acceptable values")

        #for accept in accepts:
            #token = next(self.tokens)
            #if isinstance(accept, six.string_types) and (
                    #not token.value == accept):
                #self.illegal("Expected '%s'" % (accept,))
            #elif isinstance(accept, type) and not isinstance(token, accept):
                #self.illegal("Expected %s" % (accept.__name__,))

            #last = token

        #return last.value

    #def would_accept(self, *accepts):
        #if len(accepts) == 0:
            #raise CppParserError("Missing acceptable values")

        #for i, accept in enumerate(accepts):
            #token = self.tokens.look(i)

            #if isinstance(accept, six.string_types) and (
                    #not token.value == accept):
                #return False
            #elif isinstance(accept, type) and not isinstance(token, accept):
                #return False

        #return True

    #def try_accept(self, *accepts):
        #if len(accepts) == 0:
            #raise CppParserError("Missing acceptable values")

        #for i, accept in enumerate(accepts):
            #token = self.tokens.look(i)

            #if isinstance(accept, six.string_types) and (
                    #not token.value == accept):
                #return False
            #elif isinstance(accept, type) and not isinstance(token, accept):
                #return False

        #for i in range(0, len(accepts)):
            #next(self.tokens)

        #return True

    #def build_binary_operation(self, parts, start_level=0) -> tree.BinaryOperation:
        #if len(parts) == 1:
            #return parts[0]

        #operands = list()
        #operators = list()

        #i = 0

        #for level in range(start_level, len(self.operator_precedence)):
            #for j in range(1, len(parts) - 1, 2):
                #if parts[j].operator in self.operator_precedence[level]:
                    #operand = self.build_binary_operation(parts[i:j], level + 1)
                    #operator = parts[j]
                    #i = j + 1

                    #operands.append(operand)
                    #operators.append(operator)

            #if operands:
                #break

        #operand = self.build_binary_operation(parts[i:], level + 1)
        #operands.append(operand)

        #operation = operands[0]

        #for operator, operandr in zip(operators, operands[1:]):
            #operation = tree.BinaryOperation(operandl=operation)
            #operation.operator = operator
            #operation.operandr = operandr

        #return operation

    #def is_annotation(self, i=0):
        #""" Returns true if the position is the start of an annotation application
        #(as opposed to an annotation declaration)

        #"""

        #return (isinstance(self.tokens.look(i), Annotation)
                #and not self.tokens.look(i + 1).value == 'interface')

    #def is_annotation_declaration(self, i=0):
        #""" Returns true if the position is the start of an annotation application
        #(as opposed to an annotation declaration)

        #"""

        #return (isinstance(self.tokens.look(i), Annotation)
                #and self.tokens.look(i + 1).value == 'interface')

    def parse_subnodes(self, node, *, keep_empty=False):
        if 'inner' in node:
            assert len(node['inner']) > 0
            result = [self.parse_node(c) for c in node['inner']]
            if keep_empty:
                return result
            else:
                return [c for c in result if c is not None]
        else:
            return []

    def collect_comment(self, node) -> str:
        if node['kind'] == 'TextComment':
            return node['text']
        return " ".join([self.collect_comment(subnode) for subnode in node['inner']])

    def get_node_source_code(self, node) -> str:
        if ('range' not in node or 'begin' not in node['range']
                or 'offset' not in node['range']['begin']):
            return ''
        return self.source_code[
            node['range']['begin']['offset']:node['range']['end']['offset']].strip()
# ------------------------------------------------------------------------------
# ---- Parsing methods ----

# ------------------------------------------------------------------------------
# -- Identifiers --

    #@parse_debug
    #def parse_identifier(self):
        #return self.accept(Identifier)

    #@parse_debug
    #def parse_qualified_identifier(self):
        #qualified_identifier = list()

        #while True:
            #identifier = self.parse_identifier()
            #qualified_identifier.append(identifier)

            #if not self.try_accept('.'):
                #break

        #return '.'.join(qualified_identifier)

    #@parse_debug
    #def parse_qualified_identifier_list(self):
        #qualified_identifiers = list()

        #while True:
            #qualified_identifier = self.parse_qualified_identifier()
            #qualified_identifiers.append(qualified_identifier)

            #if not self.try_accept(','):
                #break

        #return qualified_identifiers

    def abort_visit(node):  # XXX: self?
        msg = (f"No defined parse handler for clang node of type `{node['kind']}`.\n"
               f"please define `parse_{node['kind']}` in cpplang/parser.py.")
        raise AttributeError(msg)

    @parse_debug
    def parse_node(self, node, abort=abort_visit) -> tree.Node:
        if node is None or 'kind' not in node:
            return None
        if ENABLE_DEBUG_SUPPORT:
            print(f"parse_node {node['kind']}", file=sys.stderr)
        if ('isImplicit' in node and node['isImplicit'] and not ('isReferenced' in node and node['isReferenced'])):
            return None
        elif 'isImplicit' in node and node['isImplicit'] and 'isReferenced' in node and node['isReferenced'] and node['kind'] == 'TypedefDecl':
            return None
        elif (('loc' in node and 'includedFrom' in node['loc'])
            or ('range' in node and 'includedFrom' in node['range']['begin'])
            or ('loc' in node and 'range' in node['loc']
                and 'includedFrom' in node['loc']['range']['begin'])
            or ('loc' in node and 'spellingLoc' in node['loc'] and 'includedFrom' in node['loc']['spellingLoc'])
            or ('range' in node and 'spellingLoc' in node['range']['begin'] and 'includedFrom' in node['range']['begin']['spellingLoc'])
            ):
            return None
        elif ((len(self.stack) == 0 and node['loc'] and 'file' in node['loc']
             and node['loc']['file'] == "<stdin>")
                or len(self.stack) > 0):
            self.stack.append(node)
            parse_method = getattr(self, "parse_"+node['kind'], abort)
            result = parse_method(node)
            self.stack.pop()
            return result
        elif ((len(self.stack) == 0 and 'loc' in node
               and 'file' not in node['loc']
               and 'includedFrom' not in node['loc']
               and ('range' not in node['loc']
                    or 'includedFrom' not in node['loc']['range']['begin'])
               and ('spellingLoc' not in node['loc']
                    or 'includedFrom' not in node['loc']['spellingLoc']))
                or len(self.stack) > 0):
            self.stack.append(node)
            parse_method = getattr(self, "parse_"+node['kind'], abort)
            result = parse_method(node)
            self.stack.pop()
            return result
        else:
            return None

# ------------------------------------------------------------------------------
# -- Top level units --

    def parse_type_summary(self, node):
        for child in node:
            if 'node_inner' in child:
                inner_child, = child['node_inner']
                self.type_informations[child['node_id']] = inner_child
            if 'inner' in child:
                self.parse_type_summary(child['inner'])
            if 'asm_string' in child:
                asm_infos = {'asm_string': child['asm_string']}

                self.asm_informations[child['node_id']] = asm_infos

                if "output_constraints" in child:
                    output_constraints = {n['id']: n['constraint'] for n in
                                        child['output_constraints']}
                else:
                    output_constraints = {}

                if "input_constraints" in child:
                    input_constraints = {n['id']: n['constraint'] for n in
                                         child['input_constraints']}
                else:
                    input_constraints = {}

                asm_infos['output_constraints'] = output_constraints
                asm_infos['input_constraints'] = input_constraints

                asm_infos['clobbers'] = [x['clobber'] for x in
                                         child.get('clobbers', [])]
                asm_infos['labels'] = [x['label'] for x in child.get('labels',
                                                                     [])]


    @parse_debug
    def parse_TranslationUnit(self, node) -> tree.TranslationUnit:
        assert node['kind'] == "TranslationUnitDecl"
        # print(f"parse_TranslationUnit {node}", file=sys.stderr)
        subnodes = self.parse_subnodes(node)
        return tree.TranslationUnit(stmts=self.as_statements(subnodes))

    @parse_debug
    def parse_CXXRecordDecl(self, node) -> tree.CXXRecordDecl:
        assert node['kind'] == "CXXRecordDecl"
        if 'isImplicit' in node and node['isImplicit']:
            return None
        name = node.get('name')
        if name is None:
            loc = node['loc']
            where = '(unnamed struct at {}:{}:{})'.format(
                    loc.get('file', '<stdin>'),
                    loc.get('presumedLine', loc['line']),
                    loc['col'])
            name = '$_{}'.format(len(self.anonymous_types))
            self.anonymous_types[where] = name

        kind = node['tagUsed']
        complete_definition = ('complete_definition'
                               if ('completeDefinition' in node
                                   and node['completeDefinition'])
                               else '')
        bases = ""
        if "bases" in node:
            s = self.get_node_source_code(node)
            p = r"^[^:]*:([^{]*){"
            temp = re.search(p, s).group(1)
            bases = temp.replace("\\n", "")
        subnodes = self.parse_subnodes(node)

        # specific support for anonymous record through indirect field
        indirect_field_names = {n['name'] for n in node['inner']
                                if n['kind'] == 'IndirectFieldDecl'}
        anonymous_records = [n for n in node['inner']
                             if n['kind'] == 'CXXRecordDecl'
                             if 'name' not in n]

        for subnode in subnodes:
            if not isinstance(subnode, tree.CXXRecordDecl):
                continue
            if subnode.name not in self.anonymous_types.values():
                continue
            field_names = {field.name for field in subnode.subnodes
                           if isinstance(field, tree.FieldDecl)}

            # Force the record name to empty to correctly represent indirect
            # fields.
            if field_names.issubset(indirect_field_names):
                subnode.name = ""


        return tree.CXXRecordDecl(name=name, kind=kind, bases=bases,
                                  complete_definition=complete_definition,
                                  subnodes=subnodes)

    @parse_debug
    def parse_RecordDecl(self, node) -> tree.RecordDecl:
        print(node)

    @parse_debug
    def parse_CXXConstructorDecl(self, node) -> tree.CXXConstructorDecl:
        assert node['kind'] == "CXXConstructorDecl"
        if 'isImplicit' in node and node['isImplicit']:
            return None
        name = self.get_node_source_code(node).split("(")[0]
        stmts = self.parse_subnodes(node)
        noexcept = ""
        type_ = node['type']['qualType']
        try:
            i = type_.index('noexcept')
            noexcept = type_[i:]
        except Exception as _:
            pass
        if len(noexcept) == 0:
            try:
                i = type_.index('throw')
                noexcept = type_[i:]
            except Exception as _:
                pass
        default = ''
        if 'explicitlyDefaulted' in node:
            if node['explicitlyDefaulted'] == "default":
                default = "default"
            elif node['explicitlyDefaulted'] == "deleted":
                default = "delete"

        return tree.CXXConstructorDecl(name=name, noexcept=noexcept, default=default,
                                       stmts=stmts)

    @parse_debug
    def parse_CXXCtorInitializer(self, node) -> tree.CXXCtorInitializer:
        assert node['kind'] == "CXXCtorInitializer"
        #if 'message.toStdString' in self.get_node_source_code(node['inner'][0]):
            #breakpoint()
        if (len(self.get_node_source_code(node['inner'][0])) == 0
                and node['inner'][0]['kind'] == 'CXXConstructExpr'):
            return None
        elif 'anyInit' in node:
            name = node['anyInit']['name']
        #elif 'baseInit' in node:
            #name = node['baseInit']['qualType']
            #if name == "Lima::LimaException":
                #breakpoint()
        elif (len(self.get_node_source_code(node['inner'][0])) > 0
                and node['inner'][0]['kind'] in ['CXXConstructExpr',
                                                 'ExprWithCleanups']):
            name = self.get_node_source_code(node['inner'][0])
            try:
                i = name.index("(")
                name = name[:i]
            except Exception as _:
                pass
            #breakpoint()
        else:
            name = None
        subnodes = self.parse_subnodes(node)
        return tree.CXXCtorInitializer(name=name, subnodes=subnodes)

    @parse_debug
    def parse_CXXDestructorDecl(self, node) -> tree.CXXDestructorDecl:
        assert node['kind'] == "CXXDestructorDecl"
        if 'isImplicit' in node and node['isImplicit']:
            return None
        virtual = 'virtual' if 'virtual' in node and node['virtual'] else ''
        name = self.get_node_source_code(node).split("(")[0]
        try:
            i = name.index("~")
            name = name[i:]
        except Exception as _:
            pass
        noexcept = ""
        type_ = node['type']['qualType']
        try:
            i = type_.index('noexcept')
            if 'noexcept' in self.get_node_source_code(node):
                noexcept = type_[i:]
        except Exception as _:
            pass
        if len(noexcept) == 0:
            try:
                i = type_.index('throw')
                noexcept = type_[i:]
            except Exception as _:
                pass
        default = ''
        if 'explicitlyDefaulted' in node:
            if node['explicitlyDefaulted'] == "default":
                default = "default"
            elif node['explicitlyDefaulted'] == "deleted":
                default = "delete"
        subnodes = self.parse_subnodes(node)
        #if not virtual:
            #subnodes = self.parse_subnodes(node)
        #else:
            ##breakpoint()
            #subnodes = []
        return tree.CXXDestructorDecl(name=name, virtual=virtual, default=default,
                                      noexcept=noexcept, subnodes=subnodes)

    @parse_debug
    def parse_AccessSpecDecl(self, node) -> tree.AccessSpecDecl:
        assert node['kind'] == "AccessSpecDecl"
        access_spec = node['access']
        subnodes = self.parse_subnodes(node)

        return tree.AccessSpecDecl(access_spec=access_spec, subnodes=subnodes)

    @parse_debug
    def parse_CXXMethodDecl(self, node) -> tree.CXXMethodDecl:
        assert node['kind'] == "CXXMethodDecl"
        if 'isImplicit' in node and node['isImplicit']:
            return None
        name = self.get_node_source_code(node).split("(")[0].strip().split(" ")[-1]
        iname = self.get_node_source_code(node).index(name)
        return_type = self.get_node_source_code(node)[:iname].strip()
        virtual = ""
        if return_type.startswith("virtual "):
            virtual = "virtual"
            return_type = return_type.removeprefix("virtual ")
        noexcept = ""
        try:
            i = self.get_node_source_code(node).index('noexcept')
            noexcept = self.get_node_source_code(node)[i:]
            if "{" in noexcept:
                i = noexcept.index("{")
                noexcept = noexcept[:i]
        except Exception as _:
            pass
        if len(noexcept) == 0:
            try:
                i = self.get_node_source_code(node).index('throw')
                noexcept = self.get_node_source_code(node)[i:]
                if "{" in noexcept:
                    i = noexcept.index("{")
                    noexcept = noexcept[:i]
            except Exception as _:
                pass
        qualType = re.sub(r"^.*?\)", "", node['type']['qualType'].replace(" ", ""))
        const = ""
        if "const" in qualType:
            const = "const"
        default = ""
        if 'explicitlyDefaulted' in node:
            if node['explicitlyDefaulted'] == "default":
                default = "default"
            elif node['explicitlyDefaulted'] == "deleted":
                default = "delete"
        if 'explicitlyDeleted' in node and node['explicitlyDeleted']:
            default = "delete"
        subnodes = self.parse_subnodes(node)
        return tree.CXXMethodDecl(name=name, virtual=virtual, return_type=return_type,
                                  noexcept=noexcept, const=const, default=default,
                                  subnodes=subnodes)

    @parse_debug
    def parse_FunctionDecl(self, node) -> tree.FunctionDecl:
        assert node['kind'] == "FunctionDecl"
        self.parsed_gotos.clear()
        self.parsed_labels.clear()

        name = node['name']
        return_type = self.parse_node(self.type_informations[node['id']]).return_type
        variadic = "..." if node['type']['qualType'].endswith('...)') else None
        inline = "inline" if node.get('inline') else None
        storage = node.get('storageClass')
        inner_nodes = self.parse_subnodes(node)
        body, args = None, []
        for inner_node in inner_nodes:
            if isinstance(inner_node, tree.ParmVarDecl):
                args.append(inner_node)
            else:
                assert body is None
                body = inner_node

        return tree.FunctionDecl(name=name, return_type=return_type,
                                 variadic=variadic, parameters=args,
                                 inline=inline, storage=storage,
                                 body=body)

    @parse_debug
    def parse_GCCAsmStmt(self, node) -> tree.GCCAsmStmt:
        assert node['kind'] == "GCCAsmStmt"
        exprs = self.parse_subnodes(node)
        asm_infos = self.asm_informations[node['id']]

        asm_string = asm_infos['asm_string']
        input_constraints, input_exprs = [], []
        input_constraints_mapping = asm_infos.get('input_constraints', {})
        output_constraints, output_exprs = [], []
        output_constraints_mapping = asm_infos.get('output_constraints', {})
        for expr, subnode in zip(exprs, node.get('inner', ())):
            subnode_id = subnode['id']
            input_constraint = input_constraints_mapping.get(subnode_id, '')
            if input_constraint:
                input_constraints.append(input_constraint)
                input_exprs.append(expr)
            output_constraint = output_constraints_mapping.get(subnode_id, '')
            if output_constraint:
                output_constraints.append(output_constraint)
                output_exprs.append(expr)

        clobbers = asm_infos.get('clobbers', [])
        labels = asm_infos.get('labels', [])
        return tree.GCCAsmStmt(string=asm_string,
                               clobbers=clobbers,
                               labels=labels,
                               input_operands=[
                                   tree.ConstrainedExpression(expr=input_expr,
                                                              constraint=input_constraint)
                                   for input_expr, input_constraint in
                                   zip(input_exprs, input_constraints)],
                               output_operands=[
                                   tree.ConstrainedExpression(expr=output_expr,
                                                              constraint=output_constraint)
                                   for output_expr, output_constraint in
                                   zip(output_exprs, output_constraints)])

    @parse_debug
    def parse_TypedefDecl(self, node) -> tree.TypedefDecl:
        assert node['kind'] == "TypedefDecl"
        name = node['name']
        type_, = self.parse_subnodes(node)
        return tree.TypedefDecl(name=name, type=type_)

    @parse_debug
    def parse_ParmVarDecl(self, node) -> tree.ParmVarDecl:
        assert node['kind'] == "ParmVarDecl"
        name = node.get('name')
        var_type = self.parse_node(self.type_informations[node['id']])
        subnodes = self.parse_subnodes(node)
        return tree.ParmVarDecl(name=name, type=var_type,
                                default=subnodes or None)

    def as_statement(self, subnode):
        if isinstance(subnode, tree.Expression):
            return tree.ExprStmt(expr=subnode)
        if isinstance(subnode, tree.Declaration):
            return tree.DeclStmt(decls=[subnode])
        else:
            assert isinstance(subnode, tree.Statement), subnode
            return subnode

    def as_statements(self, subnodes):
        for i, subnode in enumerate(subnodes):
            subnodes[i] = self.as_statement(subnode)
        return subnodes

    @parse_debug
    def parse_CompoundStmt(self, node) -> tree.CompoundStmt:
        assert node['kind'] == "CompoundStmt"
        inner_nodes = self.parse_subnodes(node)
        return tree.CompoundStmt(stmts=self.as_statements(inner_nodes))

    @parse_debug
    def parse_IfStmt(self, node) -> tree.IfStmt:
        assert node['kind'] == "IfStmt"
        cond, *subnodes = self.parse_subnodes(node)
        if node.get('hasVar'):
            assert isinstance(cond, tree.DeclStmt)
            if len(cond.decls) != 1:
                raise NotImplementedError()
            cond = tree.DeclOrExpr(decl=cond.decls, expr=None)
            subnodes = subnodes[1:]  # pop the implicit condition evaluation
        else:
            cond = tree.DeclOrExpr(decl=None, expr=cond)

        if len(subnodes) == 1:
            true_body, false_body = subnodes[0], None
        else:
            true_body, false_body = subnodes
        return tree.IfStmt(cond=cond,
                           true_body=self.as_statement(true_body),
                           false_body=false_body and self.as_statement(false_body))

    @parse_debug
    def parse_LabelStmt(self, node) -> tree.LabelStmt:
        assert node['kind'] == "LabelStmt"
        name = node['name']
        decl_id = node['declId']
        self.parsed_labels[decl_id] = name
        child, = self.parse_subnodes(node)
        for target_id, goto in self.parsed_gotos.items():
            if target_id == decl_id:
                goto.target = name
        return tree.LabelStmt(name=name,
                              stmt=self.as_statement(child))

    @parse_debug
    def parse_GotoStmt(self, node) -> tree.LabelStmt:
        assert node['kind'] == "GotoStmt"
        decl_id = node['targetLabelDeclId']
        target = self.parsed_labels.get(decl_id)
        tnode = tree.GotoStmt(target=target)
        self.parsed_gotos[decl_id] = tnode
        return tnode

    @parse_debug
    def parse_ForStmt(self, node) -> tree.ForStmt:
        assert node['kind'] == "ForStmt"
        init, cond_decl, cond, inc, body = self.parse_subnodes(node, keep_empty=True)

        if isinstance(init, tree.Expression):
            init = tree.DeclOrExpr(expr=init, decl=None)
        elif isinstance(init, tree.DeclStmt):
            init = tree.DeclOrExpr(expr=None, decl=init.decls)

        if cond_decl:
            assert isinstance(cond_decl, tree.DeclStmt)
            cond = tree.DeclOrExpr(expr=None, decl=cond_decl.decls)
        elif cond:
            assert isinstance(cond, tree.Expression)
            cond = tree.DeclOrExpr(expr=cond, decl=None)

        return tree.ForStmt(
                init=init,
                cond=cond,
                inc=inc,
                body=self.as_statement(body))

    @parse_debug
    def parse_WhileStmt(self, node) -> tree.WhileStmt:
        assert node['kind'] == "WhileStmt"
        if node.get('hasVar'):
            var, cond, body = self.parse_subnodes(node)
            assert isinstance(var, tree.DeclStmt), var
            if len(var.decls) != 1:
                raise NotImplementedError()
            cond = tree.DeclOrExpr(decl=var.decls, expr=None)
        else:
            cond, body = self.parse_subnodes(node)
            cond =  tree.DeclOrExpr(decl=None, expr=cond)
        return tree.WhileStmt(cond=cond,
                              body=self.as_statement(body))

    @parse_debug
    def parse_DoStmt(self, node) -> tree.DoStmt:
        assert node['kind'] == "DoStmt"
        body, cond = self.parse_subnodes(node)
        return tree.DoStmt(cond=cond,
                           body=self.as_statement(body))

    @parse_debug
    def parse_ContinueStmt(self, node) -> tree.ContinueStmt:
        assert node['kind'] == "ContinueStmt"
        return tree.ContinueStmt()

    @parse_debug
    def parse_ReturnStmt(self, node) -> tree.ReturnStmt:
        assert node['kind'] == "ReturnStmt"
        subnodes = self.parse_subnodes(node)
        assert len(subnodes) <= 1
        value = subnodes[0] if len(subnodes) == 1 else None
        return tree.ReturnStmt(value=value)

    def parse_SwitchStmt(self, node) -> tree.SwitchStmt:
        assert node['kind'] == "SwitchStmt"
        cond, body = self.parse_subnodes(node)
        return tree.SwitchStmt(cond=cond,
                               body=self.as_statement(body))

    def parse_CaseStmt(self, node) -> tree.CaseStmt:
        assert node['kind'] == "CaseStmt"
        pattern, child = self.parse_subnodes(node)
        return tree.CaseStmt(pattern=pattern,
                             stmt=self.as_statement(child))

    def parse_BreakStmt(self, node) -> tree.BreakStmt:
        assert node['kind'] == "BreakStmt"
        return tree.BreakStmt()

    def parse_DefaultStmt(self, node) -> tree.DefaultStmt:
        assert node['kind'] == "DefaultStmt"
        child, = self.parse_subnodes(node)
        return tree.DefaultStmt(stmt=self.as_statement(child))

    def parse_CXXThisExpr(self, node) -> tree.CXXThisExpr:
        assert node['kind'] == "CXXThisExpr"
        if node.get('implicit'):
            return None
        return tree.CXXThisExpr()

    def parse_MemberExpr(self, node) -> tree.MemberExpr:
        assert node['kind'] == "MemberExpr"
        name = node['name']
        op = "->" if node.get('isArrow') else "."
        inner_nodes = self.parse_subnodes(node)
        if inner_nodes:
            expr, = inner_nodes
        else:
            expr = None
        return tree.MemberExpr(name=name, op=op, expr=expr)

    def parse_ConstantExpr(self, node) -> tree.ConstantExpr:
        assert node['kind'] == "ConstantExpr"
        value = node['value']
        expr, = self.parse_subnodes(node)
        return tree.ConstantExpr(value=value, expr=expr)

    @parse_debug
    def parse_DeclRefExpr(self, node) -> tree.DeclRefExpr:
        assert node['kind'] == "DeclRefExpr"
        name = self.get_node_source_code(node)+node['referencedDecl']['name']
        kind = node['referencedDecl']['kind']
        return tree.DeclRefExpr(name=name, kind=kind)

    @parse_debug
    def parse_IntegerLiteral(self, node) -> tree.IntegerLiteral:
        assert node['kind'] == "IntegerLiteral"
        value = node['value']
        type_ = self.parse_node(self.type_informations[node['id']])
        return tree.IntegerLiteral(type=type_, value=value)

    @parse_debug
    def parse_FloatingLiteral(self, node) -> tree.FloatingLiteral:
        assert node['kind'] == "FloatingLiteral"
        value = node['value']
        type_ = self.parse_node(self.type_informations[node['id']])
        return tree.FloatingLiteral(type=type_, value=value)

    @parse_debug
    def parse_CharacterLiteral(self, node) -> tree.CharacterLiteral:
        assert node['kind'] == "CharacterLiteral"
        value = node['value']
        return tree.CharacterLiteral(value=chr(value))

    @parse_debug
    def parse_StringLiteral(self, node) -> tree.StringLiteral:
        assert node['kind'] == "StringLiteral"
        value = node['value']
        return tree.StringLiteral(value=value)

    @parse_debug
    def parse_CXXNullPtrLiteralExpr(self, node) -> tree.CXXNullPtrLiteralExpr:
        assert node['kind'] == "CXXNullPtrLiteralExpr"
        return tree.CXXNullPtrLiteralExpr()

    @parse_debug
    def parse_NamespaceDecl(self, node) -> tree.NamespaceDecl:
        assert node['kind'] == "NamespaceDecl"
        name = node['name']
        subnodes = self.parse_subnodes(node)
        return tree.NamespaceDecl(name=name, subnodes=subnodes)

    #@parse_debug
    #def parse_Namespace(self, node) -> tree.Namespace:
        #assert node['kind'] == "Namespace"
        #name = node['name']
        #subnodes = self.parse_subnodes(node)
        #return tree.Namespace(name=name, subnodes=subnodes)

    @parse_debug
    def parse_UsingDirectiveDecl(self, node) -> tree.UsingDirectiveDecl:
        assert node['kind'] == "UsingDirectiveDecl"
        name = (self.get_node_source_code(node).replace('using namespace','').strip()
                + node['nominatedNamespace']['name'])
        return tree.UsingDirectiveDecl(name=name)

    @parse_debug
    def parse_DeclStmt(self, node) -> tree.DeclStmt:
        assert node['kind'] == "DeclStmt"
        decls = self.parse_subnodes(node)
        return tree.DeclStmt(decls=decls)

    def mangle_anonymous_type(self, qual_type):
        if qual_type.startswith('struct (unnamed struct'):
            return self.anonymous_types[qual_type[7:]]
        else:
            return qual_type

    @parse_debug
    def parse_QualType(self, node) -> tree.QualType:
        assert node['kind'] == "QualType"
        type_, = self.parse_subnodes(node)
        qualifiers = node['qualifiers']
        return tree.QualType(qualifiers=qualifiers, type=type_)

    @parse_debug
    def parse_VarDecl(self, node) -> tree.VarDecl:
        assert node['kind'] == "VarDecl"
        name = node['name']
        implicit = node.get('isImplicit')
        referenced = node.get('isReferenced')
        storage_class = node.get('storageClass')

        type_ = self.parse_node(self.type_informations[node['id']])

        if 'init' in node:
            init, = self.parse_subnodes(node)
            init_mode = node['init']
        else:
            init = None
            init_mode = ''

        return tree.VarDecl(name=name,
                            storage_class=storage_class,
                            type=type_,
                            init_mode=init_mode,
                            implicit=implicit,
                            referenced=referenced,
                            init=init)

    @parse_debug
    def parse_InitListExpr(self, node) -> tree.InitListExpr:
        assert node['kind'] == "InitListExpr"
        values = self.parse_subnodes(node)
        return tree.InitListExpr(values=values)

    @parse_debug
    def parse_TypeRef(self, node) -> tree.TypeRef:
        assert node['kind'] == "TypeRef"
        name = node['name']
        subnodes = self.parse_subnodes(node)
        return tree.TypeRef(name=name, subnodes=subnodes)

    #@parse_debug
    #def parse_NamespaceRef(self, node) -> tree.NamespaceRef:
        #assert node['kind'] == "NamespaceRef"
        #name = node['name']
        #subnodes = self.parse_subnodes(node)
        #return tree.NamespaceRef(name=name, subnodes=subnodes)

    @parse_debug
    def parse_ExprWithCleanups(self, node) -> tree.ExprWithCleanups:
        assert node['kind'] == "ExprWithCleanups"
        subnodes = self.parse_subnodes(node)
        return tree.ExprWithCleanups(subnodes=subnodes)

    @parse_debug
    def parse_CXXConstructExpr(self, node) -> tree.CXXConstructExpr:
        assert node['kind'] == "CXXConstructExpr"
        #if len(self.get_node_source_code(node)) == 0:
            #breakpoint()
            #return None

        type_ = node['type']['qualType']
        subnodes = self.parse_subnodes(node)
        return tree.CXXConstructExpr(type=type_, subnodes=subnodes)

    @parse_debug
    def parse_MaterializeTemporaryExpr(self, node) -> tree.MaterializeTemporaryExpr:
        assert node['kind'] == "MaterializeTemporaryExpr"
        expr, = self.parse_subnodes(node)
        return tree.MaterializeTemporaryExpr(expr=expr)

    @parse_debug
    def parse_CXXBindTemporaryExpr(self, node) -> tree.CXXBindTemporaryExpr:
        assert node['kind'] == "CXXBindTemporaryExpr"
        subnodes = self.parse_subnodes(node)
        assert len(subnodes) > 0
        return tree.CXXBindTemporaryExpr(subnodes=subnodes)

    @parse_debug
    def parse_ImplicitCastExpr(self, node) -> tree.ImplicitCastExpr:
        assert node['kind'] == "ImplicitCastExpr"
        #type_ = self.reparse_type(node['type'])
        type_ = self.parse_node(self.type_informations[node['id']])
        expr, = self.parse_subnodes(node)
        return tree.ImplicitCastExpr(type=type_, expr=expr)

    @parse_debug
    def parse_CXXDefaultArgExpr(self, node) -> None:
        assert node['kind'] == "CXXDefaultArgExpr"
        return None

    @parse_debug
    def parse_FieldDecl(self, node) -> tree.FieldDecl:
        assert node['kind'] == "FieldDecl"
        name = node['name']
        #var_type = self.reparse_type(node['type']) #name, node['range'])
        var_type = self.parse_node(self.type_informations[node['id']])
        if 'hasInClassInitializer' in node:
            init, = self.parse_subnodes(node)
        else:
            init = None
        return tree.FieldDecl(name=name, type=var_type, init=init)

    @parse_debug
    def parse_BinaryOperator(self, node) -> tree.BinaryOperator:
        assert node['kind'] == "BinaryOperator"
        opcode = node['opcode']
        lhs, rhs = self.parse_subnodes(node)
        return tree.BinaryOperator(opcode=opcode, lhs=lhs, rhs=rhs)

    @parse_debug
    def parse_CompoundAssignOperator(self, node) -> tree.CompoundAssignOperator:
        assert node['kind'] == "CompoundAssignOperator"
        opcode = node['opcode']
        lhs, rhs = self.parse_subnodes(node)
        return tree.CompoundAssignOperator(opcode=opcode, lhs=lhs, rhs=rhs)

    @parse_debug
    def parse_UnaryOperator(self, node) -> tree.UnaryOperator:
        assert node['kind'] == "UnaryOperator"
        opcode = node['opcode']
        expr, = self.parse_subnodes(node)
        postfix = str(node['isPostfix'])
        return tree.UnaryOperator(opcode=opcode, expr=expr, postfix=postfix)

    @parse_debug
    def parse_ConditionalOperator(self, node) -> tree.ConditionalOperator:
        assert node['kind'] == "ConditionalOperator"
        cond, true_expr, false_expr = self.parse_subnodes(node)
        return tree.ConditionalOperator(cond=cond, true_expr=true_expr,
                                        false_expr=false_expr)

    @parse_debug
    def parse_ArraySubscriptExpr(self, node) -> tree.ArraySubscriptExpr:
        assert node['kind'] == "ArraySubscriptExpr"
        base, index = self.parse_subnodes(node)
        return tree.ArraySubscriptExpr(base=base, index=index)

    @parse_debug
    def parse_ParenExpr(self, node) -> tree.ParenExpr:
        assert node['kind'] == "ParenExpr"
        expr, = self.parse_subnodes(node)
        return tree.ParenExpr(expr=expr)

    @parse_debug
    def parse_UnaryExprOrTypeTraitExpr(self, node) -> tree.UnaryExprOrTypeTraitExpr:
        assert node['kind'] == "UnaryExprOrTypeTraitExpr"
        name = node['name']
        if 'argType' in node:
            expr = None
            type_ = self.parse_node(self.type_informations[node['id']])
        else:
            expr = self.parse_subnodes(node)[0]
            type_ = None
        return tree.UnaryExprOrTypeTraitExpr(name=name, expr=expr, type=type_)

    @parse_debug
    def parse_ClassTemplateDecl(self, node) -> tree.ClassTemplateDecl:
        assert node['kind'] == "ClassTemplateDecl"
        subnodes = self.parse_subnodes(node)
        return tree.ClassTemplateDecl(subnodes=subnodes)

    @parse_debug
    def parse_FunctionTemplateDecl(self, node) -> tree.FunctionTemplateDecl:
        assert node['kind'] == "FunctionTemplateDecl"
        subnodes = self.parse_subnodes(node)
        return tree.FunctionTemplateDecl(subnodes=subnodes)

    @parse_debug
    def parse_TemplateTypeParmDecl(self, node) -> tree.TemplateTypeParmDecl:
        assert node['kind'] == "TemplateTypeParmDecl"
        name = node['name']
        subnodes = self.parse_subnodes(node)
        return tree.TemplateTypeParmDecl(name=name, subnodes=subnodes)

    @parse_debug
    def parse_NonTypeTemplateParmDecl(self, node) -> tree.NonTypeTemplateParmDecl:
        assert node['kind'] == "NonTypeTemplateParmDecl"
        name = node['name']
        type_ = node['type']['qualType']
        subnodes = self.parse_subnodes(node)
        return tree.NonTypeTemplateParmDecl(name=name, type=type_, subnodes=subnodes)

    @parse_debug
    def parse_FullComment(self, node) -> tree.FullComment:
        assert node['kind'] == "FullComment"
        comment = self.collect_comment(node)
        return tree.FullComment(comment=comment)

    @parse_debug
    def parse_OverrideAttr(self, node) -> tree.OverrideAttr:
        assert node['kind'] == "OverrideAttr"
        return tree.OverrideAttr()

    @parse_debug
    def parse_CXXMemberCallExpr(self, node) -> tree.CXXMemberCallExpr:
        assert node['kind'] == "CXXMemberCallExpr"
        subnodes = self.parse_subnodes(node)
        return tree.CXXMemberCallExpr(subnodes=subnodes)

    @parse_debug
    def parse_CallExpr(self, node) -> tree.CallExpr:
        assert node['kind'] == "CallExpr"
        callee, *args = self.parse_subnodes(node)
        return tree.CallExpr(calee=callee, args=args)

    @parse_debug
    def parse_CXXOperatorCallExpr(self, node) -> tree.CXXOperatorCallExpr:
        assert node['kind'] == "CXXOperatorCallExpr"
        subnodes = self.parse_subnodes(node)
        assert len(subnodes) >= 2
        op = subnodes[0]
        left = subnodes[1]
        right = subnodes[2] if len(subnodes) == 3 else None
        return tree.CXXOperatorCallExpr(left=left, op=op, right=right)

    @parse_debug
    def parse_CXXBoolLiteralExpr(self, node) -> tree.CXXBoolLiteralExpr:
        assert node['kind'] == "CXXBoolLiteralExpr"
        subnodes = self.parse_subnodes(node)
        return tree.CXXBoolLiteralExpr(value=str(node['value']))

    @parse_debug
    def parse_CXXTemporaryObjectExpr(self, node) -> tree.CXXTemporaryObjectExpr:
        assert node['kind'] == "CXXTemporaryObjectExpr"
        type_ = node['type']['qualType']
        subnodes = self.parse_subnodes(node)
        # assert len(subnodes) > 0
        return tree.CXXTemporaryObjectExpr(type=type_, subnodes=subnodes)

    @parse_debug
    def parse_CXXFunctionalCastExpr(self, node) -> tree.CXXFunctionalCastExpr:
        assert node['kind'] == "CXXFunctionalCastExpr"
        type_ = self.get_node_source_code(node).split("(")[0]
        #type_ = node['type']['qualType']
        #type_ = node['conversionFunc']['name']
        if type_ == 'Lima::Common::XMLConfigurationFiles::ModuleConfigurationStructure':
            breakpoint()
        elif type_ == 'basic_string':
            breakpoint()
        subnodes = self.parse_subnodes(node)
        return tree.CXXFunctionalCastExpr(type=type_, subnodes=subnodes)

    @parse_debug
    def parse_NullStmt(self, node) -> tree.NullStmt:
        assert node['kind'] == "NullStmt"
        return tree.NullStmt()

    @parse_debug
    def parse_EnumConstantDecl(self, node) -> tree.EnumConstantDecl:
        assert node['kind'] == "EnumConstantDecl"
        name = node['name']
        children = self.parse_subnodes(node)
        init = None if not children else children[0]
        return tree.EnumConstantDecl(name=name, init=init)

    @parse_debug
    def parse_EnumDecl(self, node) -> tree.EnumDecl:
        assert node['kind'] == "EnumDecl"
        name = node.get('name')
        fields = self.parse_subnodes(node)
        return tree.EnumDecl(name=name, fields=fields)

    @parse_debug
    def parse_ImplicitValueInitExpr(self, node) -> tree.ImplicitValueInitExpr:
        assert node['kind'] == "ImplicitValueInitExpr"
        return tree.ImplicitValueInitExpr()

    @parse_debug
    def parse_CXXConversionDecl(self, node) -> tree.CXXConversionDecl:
        assert node['kind'] == "CXXConversionDecl"
        name = self.get_node_source_code(node).split("{")[0]
        subnodes = self.parse_subnodes(node)
        return tree.CXXConversionDecl(name=name, subnodes=subnodes)

    @parse_debug
    def parse_EmptyDecl(self, node) -> tree.EmptyDecl:
        assert node['kind'] == "EmptyDecl"
        return tree.EmptyDecl()

    @parse_debug
    def parse_CStyleCastExpr(self, node) -> tree.CStyleCastExpr:
        assert node['kind'] == "CStyleCastExpr"
        #type_ = self.reparse_type(node['type'])
        type_ = self.parse_node(self.type_informations[node['id']])
        expr, = self.parse_subnodes(node)
        return tree.CStyleCastExpr(type=type_, expr=expr)

    @parse_debug
    def parse_FriendDecl(self, node) -> tree.FriendDecl:
        assert node['kind'] == "FriendDecl"
        type_ = node['type']['qualType']
        return tree.FriendDecl(type=type_)

    @parse_debug
    def parse_CXXStdInitializerListExpr(self, node) -> tree.CXXStdInitializerListExpr:
        assert node['kind'] == "CXXStdInitializerListExpr"
        subnodes = self.parse_subnodes(node)
        return tree.CXXStdInitializerListExpr(subnodes=subnodes)

    @parse_debug
    def parse_CXXNewExpr(self, node) -> tree.CXXNewExpr:
        assert node['kind'] == "CXXNewExpr"
        subnodes = self.parse_subnodes(node)

    @parse_debug
    def parse_CXXForRangeStmt(self, node) -> tree.CXXForRangeStmt:
        assert node['kind'] == "CXXForRangeStmt"
        subnodes = self.parse_subnodes(node)
        return tree.CXXForRangeStmt(subnodes=subnodes)

    @parse_debug
    def parse_BuiltinType(self, node) -> tree.BuiltinType:
        assert node['kind'] == "BuiltinType"
        return tree.BuiltinType(name=node['type']['qualType'])

    @parse_debug
    def parse_ConstantArrayType(self, node) -> tree.ConstantArrayType:
        assert node['kind'] == "ConstantArrayType"
        size = str(node['size'])
        type_, = self.parse_subnodes(node)
        return tree.ConstantArrayType(type=type_, size=size)

    @parse_debug
    def parse_ElaboratedType(self, node) -> tree.ElaboratedType:
        assert node['kind'] == "ElaboratedType"
        type_, = self.parse_subnodes(node)
        qualifiers = node.get('qualifiers')
        return tree.ElaboratedType(qualifiers=qualifiers, type=type_)

    @parse_debug
    def parse_DecayedType(self, node) -> tree.DecayedType:
        assert node['kind'] == "DecayedType"
        type_, = self.parse_subnodes(node)
        return tree.DecayedType(type=type_)

    @parse_debug
    def parse_FunctionProtoType(self, node) -> tree.FunctionProtoType:
        assert node['kind'] == "FunctionProtoType"
        return_type, *parameter_types = self.parse_subnodes(node)
        return tree.FunctionProtoType(return_type=return_type,
                                      parameter_types=parameter_types)

    @parse_debug
    def parse_IncompleteArrayType(self, node) -> tree.IncompleteArrayType:
        assert node['kind'] == "IncompleteArrayType"
        type_, = self.parse_subnodes(node)
        return tree.IncompleteArrayType(type=type_)

    @parse_debug
    def parse_ParenType(self, node) -> tree.ParenType:
        assert node['kind'] == "ParenType"
        type_, = self.parse_subnodes(node)
        return tree.ParenType(type=type_)

    @parse_debug
    def parse_PointerType(self, node) -> tree.PointerType:
        assert node['kind'] == "PointerType"
        type_, = self.parse_subnodes(node)
        return tree.PointerType(type=type_)

    @parse_debug
    def parse_RecordType(self, node) -> tree.RecordType:
        assert node['kind'] == "RecordType"
        return tree.RecordType(name=node['decl']['name'])

    @parse_debug
    def parse_EnumType(self, node) -> tree.EnumType:
        assert node['kind'] == "EnumType"
        return tree.EnumType(name=node['decl']['name'])

    @parse_debug
    def parse_LValueReferenceType(self, node) -> tree.LValueReferenceType:
        assert node['kind'] == "LValueReferenceType"
        type_, = self.parse_subnodes(node)
        return tree.LValueReferenceType(type=type_)

    @parse_debug
    def parse_RValueReferenceType(self, node) -> tree.RValueReferenceType:
        assert node['kind'] == "RValueReferenceType"
        type_, = self.parse_subnodes(node)
        return tree.RValueReferenceType(type=type_)


def parse(tokens, debug=False, filepath=None):
    parser = Parser(tokens, filepath)
    parser.set_debug(debug)
    return parser.parse()

