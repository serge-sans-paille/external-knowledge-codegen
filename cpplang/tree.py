
from .ast import Node

# ------------------------------------------------------------------------------


class TranslationUnit(Node):
    attrs = ("stmts",)


class Import(Node):
    attrs = ("path", "static", "wildcard")


class OverrideAttr(Node):
    attrs = ()


class Documented(Node):
    attrs = ("documentation",)


class Comment(Node):
    attrs = ("comment",)


class FullComment(Comment):
    attrs = ()


class BlockCommandComment(Comment):
    attrs = ()


class ParagraphComment(Comment):
    attrs = ()


class TextComment(Comment):
    attrs = ()


class Declaration(Documented):
    attrs = ()


class EmptyDeclaration(Declaration):
    attrs = ()


class NonEmptyDeclaration(Declaration):
    attrs = ("modifiers", "annotations")


class TypeDeclaration(NonEmptyDeclaration):
    attrs = ("name",)

    @property
    def fields(self):
        return [decl for decl in self.body if isinstance(decl,
                                                         FieldDecl)]

    @property
    def methods(self):
        return [decl for decl in self.body if isinstance(decl,
                                                         MethodDecl)]

    @property
    def constructors(self):
        return [decl for decl in self.body if isinstance(
          decl, ConstructorDeclaration)]


class PackageDeclaration(NonEmptyDeclaration):
    attrs = ("name",)


class CXXRecordDecl(TypeDeclaration):
    attrs = ("kind", "bases", "complete_definition", "subnodes",)


class RecordDecl(TypeDeclaration):
    attrs = ()


class CXXConstructorDecl(Declaration):
    attrs = ("name", "noexcept", "default", "subnodes",)


class CXXCtorInitializer(Node):
    attrs = ("name", "subnodes",)


class CXXDestructorDecl(Declaration):
    attrs = ("name", "virtual", "default", "noexcept", "subnodes",)


class AccessSpecDecl(Declaration):
    attrs = ("access_spec",)


class EnumDeclaration(TypeDeclaration):
    attrs = ("implements",)

    @property
    def fields(self):
        return [decl for decl in self.body.declarations if isinstance(
          decl, FieldDecl)]

    @property
    def methods(self):
        return [decl for decl in self.body.declarations if isinstance(
          decl, MethodDeclaration)]


class InterfaceDeclaration(TypeDeclaration):
    attrs = ("type_parameters", "extends",)


class AnnotationDeclaration(TypeDeclaration):
    attrs = ()


class StaticInitializer(NonEmptyDeclaration):
    attrs = ("block",)


class InstanceInitializer(NonEmptyDeclaration):
    attrs = ("block",)

# ------------------------------------------------------------------------------


class ArrayDimension(Node):
    attrs = ("dim",)


class Modifier(Node):
    attrs = ("value",)


class Operator(Node):
    attrs = ("operator",)

# ------------------------------------------------------------------------------


class Type(Node):
    attrs = ("name", "dimensions",)

class BuiltinType(Node):
    attrs = ("name",)

class ConstantArrayType(Node):
    attrs = ("type", "size", )

class DecayedType(Node):
    attrs = ("type",)

class ElaboratedType(Node):
    attrs = ("type", "qualifiers", )

class FunctionProtoType(Node):
    attrs = ("return_type", "parameter_types",)

class LValueReferenceType(Node):
    attrs = ("type",)

class RValueReferenceType(Node):
    attrs = ("type",)

class IncompleteArrayType(Node):
    attrs = ("type",)

class ParenType(Node):
    attrs = ("type",)

class PointerType(Node):
    attrs = ("type",)

class QualType(Node):
    attrs = ("qualifiers", "type",)

class RecordType(Node):
    attrs = ("name",)

class EnumType(Node):
    attrs = ("name",)

class DiamondType(Type):
    attrs = ("sub_type",)


class ReferenceType(Type):
    attrs = ("arguments", "sub_type",)


class TypeArgument(Node):
    attrs = ("type", "pattern_type",)

# ------------------------------------------------------------------------------


class TypeParameter(Node):
    attrs = ("name", "extends",)

# ------------------------------------------------------------------------------


class Annotation(Node):
    attrs = ("name", "element",)


class NormalAnnotation(Annotation):
    attrs = ()


class MarkerAnnotation(Annotation):
    attrs = ()


class SingleElementAnnotation(Annotation):
    attrs = ()


class ElementValuePair(Node):
    attrs = ("name", "value",)


class ElementArrayValue(Node):
    attrs = ("values",)


class InitListExpr(Node):
    attrs = ("values",)

# ------------------------------------------------------------------------------


class Member(NonEmptyDeclaration):
    attrs = ()


class CXXMethodDecl(Declaration):
    attrs = ("virtual", "return_type", "name", "noexcept", "const", "default", "subnodes",)


class FunctionDecl(Declaration):
    attrs = ("name", "return_type", "storage", "variadic", "inline", "body", "parameters")


class ClassTemplateDecl(Declaration):
    attrs = ("subnodes",)


class FunctionTemplateDecl(Declaration):
    attrs = ("subnodes",)


class TemplateTypeParmDecl(Declaration):
    attrs = ("name", "subnodes",)


class NonTypeTemplateParmDecl(Declaration):
    attrs = ("name", "type", "subnodes",)


class ParmVarDecl(Declaration):
    attrs = ("type", "name", "default")


class FieldDecl(Declaration):
    attrs = ("type", "name", "init",)


# ------------------------------------------------------------------------------


class ConstantDeclaration(FieldDecl):
    attrs = ()


class VariableInitializer(Node):
    """
    A VariableInitializer is either an expression or an array initializer
    https://docs.oracle.com/javase/specs/jls/se8/html/jls-8.html#jls-8.3
    TODO This is not C++ !!!
    """
    attrs = ("expression", "array",)


class ArrayInitializer(Node):
    attrs = ("initializers", "comma",)


class VariableDeclaration(NonEmptyDeclaration):
    attrs = ("type", "declarators",)


class LocalVariableDeclaration(VariableDeclaration):
    attrs = ()


class VariableDeclarator(Declaration):
    attrs = ("name", "dimensions", "initializer")


class FormalParameter(NonEmptyDeclaration):
    attrs = ("type", "name", "dimensions", "varargs")


class InferredFormalParameter(Node):
    attrs = ('expression',)

# ------------------------------------------------------------------------------


class Statement(Node):
    attrs = ()


class DoStmt(Statement):
    attrs = ("cond", "body",)


class LocalVariableDeclarationStmt(Statement):
    attrs = ("variable",)


class TypeDeclarationStmt(Statement):
    attrs = ("declaration",)


class IfStmt(Statement):
    attrs = ("cond", "var", "true_body", "false_body")


class ForStmt(Statement):
    attrs = ("init", "cond", "inc", "body")


class WhileStmt(Statement):
    attrs = ("cond", "var", "body",)


class ContinueStmt(Statement):
    attrs = ()


class AssertStmt(Statement):
    attrs = ("condition", "value")


class LabelStmt(Statement):
    attrs = ("name", "stmt",)


class GotoStmt(Statement):
    attrs = ("target",)


class ContinueStmt(Statement):
    attrs = ("goto",)


class ThrowStmt(Statement):
    attrs = ("expression",)


class SynchronizedStmt(Statement):
    attrs = ("lock", "block")


class TryStmt(Statement):
    attrs = ("resources", "block", "catches", "finally_block")


class SwitchStmt(Statement):
    attrs = ("cond", "body",)


class BreakStmt(Statement):
    attrs = ()


class DefaultStmt(Statement):
    attrs = ("stmt",)


class BlockStmt(Statement):
    attrs = ("statements",)


# statemenents are the subnodes (from Node)
class CompoundStmt(Statement):
    attrs = ("stmts",)


class ReturnStmt(Statement):
    attrs = ("value",)


class NamespaceDecl(Declaration):
    attrs = ("name", "subnodes",)


class UsingDirectiveDecl(Declaration):
    attrs = ("name",)


class DeclStmt(Statement):
    attrs = ("decls",)


class VarDecl(Declaration):
    attrs = ("name", "type", "storage_class", "init_mode", "implicit", "referenced", "init")


class TypedefDecl(Declaration):
    attrs = ("name", "type")


class TypeRef(Node):
    attrs = ("name",)


#class NamespaceRef(Node):
    #attrs = ("name",)


class ExpressionStmt(Statement):
    attrs = ("expression",)


class GCCAsmStmt(Statement):
    attrs = ("string", "output_operands", "input_operands", "clobbers", "labels",)

class ExprWithCleanups(Node):
    attrs = ("subnodes",)

class ConstrainedExpression(Node):
    attrs = ("expr", "constraint")

class CXXForRangeStmt(Node):
    attrs = ("subnodes",)


# ------------------------------------------------------------------------------


class TryResource(NonEmptyDeclaration):
    attrs = ("type", "name", "value")


class CatchClause(Statement):
    attrs = ("parameter", "block")


class CatchClauseParameter(NonEmptyDeclaration):
    attrs = ("types", "name")

# ------------------------------------------------------------------------------


class CaseStmt(Statement):
    attrs = ("pattern", "stmt",)


class ForControl(Node):
    attrs = ("init", "condition", "update")


class EnhancedForControl(Node):
    attrs = ("var", "iterable")


class ExprStmt(Node):
    attrs = ("expr",)

# ------------------------------------------------------------------------------


class Expression(Node):
    attrs = ()


class DeclRefExpr(Expression):
    attrs = ("name", "kind",)


class ElementValueArrayInitializer(Expression):
    attrs = ("initializer",)


class ReferenceTypeExpression(Expression):
    attrs = ("type",)


class BlockExpression(Expression):
    attrs = ("block",)


class NoExpression(Expression):
    attrs = ()


class Primary(Expression):
    attrs = ()
    #attrs = ("prefix_operators", "postfix_operators", "qualifier", "selectors")


class ParenExpr(Primary):
    attrs = ("expr",)


class Assignment(Primary):
    attrs = ("expressionl", "value", "type")


class BinaryOperator(Expression):
    attrs = ("opcode", "lhs", "rhs",)

class CompoundAssignOperator(Expression):
    attrs = ("opcode", "lhs", "rhs",)


class UnaryOperator(Expression):
    attrs = ("opcode", "expr", "postfix",)


class ConditionalOperator(Expression):
    attrs = ("cond", "true_expr", "false_expr")


class ArraySubscriptExpr(Expression):
    attrs = ("base", "index",)


class MethodReference(Primary):
    attrs = ("expression", "method", "type_arguments")


class LambdaExpression(Primary):
    attrs = ('parameter', 'parameters', 'body')


class CXXConstructExpr(Expression):
    attrs = ("type", "subnodes",)


class MaterializeTemporaryExpr(Expression):
    attrs = ("expr",)


class CXXBindTemporaryExpr(Expression):
    attrs = ("subnodes",)


class CXXNewExpr(Expression):
    attrs = ("subnodes",)


class UnaryExprOrTypeTraitExpr(Expression):
    attrs = ("name", "expr", "type")


class ImplicitCastExpr(Expression):
    attrs = ("type", "expr",)

# ------------------------------------------------------------------------------


class Identifier(Primary):
    attrs = ("id",)


class Literal(Primary):
    attrs = ("value",)


class CharacterLiteral(Literal):
    attrs = ()


class IntegerLiteral(Literal):
    attrs = ("type",)


class FloatingLiteral(Literal):
    attrs = ("type",)


class StringLiteral(Literal):
    attrs = ()


class CXXNullPtrLiteralExpr(Literal):
    attrs = ()


class CXXThisExpr(Primary):
    attrs = ("subnodes",)


class MemberExpr(Primary):
    attrs = ("name", "op", "expr")


class ConstantExpr(Primary):
    attrs = ("value", "expr",)


class CXXMemberCallExpr(Primary):
    attrs = ("subnodes",)


class CallExpr(Primary):
    attrs = ("callee", "args",)


class CXXOperatorCallExpr(Primary):
    attrs = ("left", "op", "right",)


class CXXBoolLiteralExpr(Primary):
    attrs = ("value",)


class CXXTemporaryObjectExpr(Node):
    attrs = ("type", "subnodes",)


class CXXFunctionalCastExpr(Node):
    attrs = ("type", "subnodes",)


class NullStmt(Statement):
    attrs = ()


class Cast(Primary):
    attrs = ("type", "expression")


class FieldReference(Primary):
    attrs = ("field",)


class MemberReference(Primary):
    attrs = ("member",)


class Invocation(Primary):
    attrs = ("type_arguments", "arguments")


class ExplicitConstructorInvocation(Invocation):
    attrs = ()


class SuperConstructorInvocation(Invocation):
    attrs = ()


class MethodInvocation(Invocation):
    attrs = ("member",)


class SuperMethodInvocation(Invocation):
    attrs = ("member",)


class SuperMemberReference(Primary):
    attrs = ("member",)


class ArraySelector(Expression):
    attrs = ("index",)


class ClassReference(Primary):
    attrs = ("type",)


class VoidClassReference(ClassReference):
    attrs = ()

# ------------------------------------------------------------------------------


class Creator(Primary):
    attrs = ("type",)


class ArrayCreator(Creator):
    attrs = ("dimensions", "initializer")


class ClassCreator(Creator):
    attrs = ("constructor_type_arguments", "arguments", "body")


class InnerClassCreator(Creator):
    attrs = ("constructor_type_arguments", "arguments", "body")


class ClassBody(Node):
    attrs = ("declarations",)


class EmptyClassBody(Node):
    attrs = ()


class ImplicitValueInitExpr(Node):
    attrs = ()


class CXXConversionDecl(Declaration):
    attrs = ("name", "subnodes",)

# ------------------------------------------------------------------------------


class EnumConstantDecl(Declaration):
    attrs = ("name", "init",)


class EnumDecl(Declaration):
    attrs = ("name", "fields",)


class AnnotationMethod(NonEmptyDeclaration):
    attrs = ("name", "return_type", "dimensions", "default")


class EmptyDecl(Declaration):
    attrs = ()


class CStyleCastExpr(Node):
    attrs = ("type", "expr",)


class FriendDecl(Declaration):
    attrs = ("type",)


class CXXStdInitializerListExpr(Node):
    attrs = ("subnodes",)

