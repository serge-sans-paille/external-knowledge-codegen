#include "clang/Frontend/FrontendPluginRegistry.h"
#include "clang/AST/AST.h"
#include "clang/AST/ASTConsumer.h"
#include "clang/AST/Attr.h"
#include "clang/Lex/Preprocessor.h"
#include "clang/Lex/LexDiagnostic.h"

#include "clang/AST/ASTContext.h"
#include "clang/AST/ASTDumperUtils.h"
#include "clang/AST/ASTNodeTraverser.h"
#include "clang/AST/AttrVisitor.h"
#include "clang/AST/CommentCommandTraits.h"
#include "clang/AST/CommentVisitor.h"
#include "clang/AST/ExprConcepts.h"
#include "clang/AST/ExprCXX.h"
#include "clang/AST/Mangle.h"
#include "clang/AST/JSONNodeDumper.h"
#include "clang/AST/Type.h"
#include "llvm/Support/JSON.h"

#include "clang/AST/Type.h"
#include "clang/Basic/SourceManager.h"
#include "clang/Basic/Specifiers.h"
#include "clang/Lex/Lexer.h"
#include "llvm/ADT/StringExtras.h"
#include "llvm/Support/raw_ostream.h"
#include <optional>


namespace clang {

// Custom, manual type visitor. this is producing the bare minimal information
// description of each type, as needed by the cpplang/parser.py.
// The type description is a strict subset of what's produced by the generic
// JSONDumper.
// This could/should rely on the visitor pattern provided by Clang, but I find
// it easier to implement this way.

static llvm::json::Object fullType(const ASTContext &Ctx, QualType T);

static llvm::json::Object fullType(const ASTContext &Ctx, const Type * Ty) {
  llvm::json::Object Ret;
  Ret["kind"] = (llvm::Twine(Ty->getTypeClassName()) + "Type").str();
  auto const& PP = Ctx.getPrintingPolicy();
  if(auto * BuiltinTy = dyn_cast<BuiltinType>(Ty)) {
    Ret["type"] = llvm::json::Object{{"qualType", BuiltinTy->getName(PP)}};
  }
  else if(auto * ConstantArrayTy = dyn_cast<ConstantArrayType>(Ty)) {
    Ret["size"] = ConstantArrayTy->getSize().getZExtValue();
    llvm::json::Array Inner;
    Inner.push_back(fullType(Ctx, ConstantArrayTy->getElementType()));
    Ret["inner"] = llvm::json::Value(std::move(Inner));
  }
  else if(auto * FunctionProtoTy = dyn_cast<FunctionProtoType>(Ty)) {
    llvm::json::Array Inner;
    Inner.push_back(fullType(Ctx, FunctionProtoTy->getReturnType()));
    for(auto ParamTy : FunctionProtoTy->param_types ())
      Inner.push_back(fullType(Ctx, ParamTy));
    Ret["inner"] = llvm::json::Value(std::move(Inner));
  }
  else if(auto * ReferenceTy = dyn_cast<ReferenceType>(Ty)) {
    llvm::json::Array Inner;
    Inner.push_back(fullType(Ctx, ReferenceTy->getPointeeType()));
    Ret["inner"] = llvm::json::Value(std::move(Inner));
  }
  else if(auto * ParenTy = dyn_cast<ParenType>(Ty)) {
    llvm::json::Array Inner;
    Inner.push_back(fullType(Ctx, ParenTy->getInnerType()));
    Ret["inner"] = llvm::json::Value(std::move(Inner));
  }
  else if(auto * PointerTy = dyn_cast<PointerType>(Ty)) {
    llvm::json::Array Inner;
    Inner.push_back(fullType(Ctx, PointerTy->getPointeeType()));
    Ret["inner"] = llvm::json::Value(std::move(Inner));
  }
  else if(auto * RecordTy = dyn_cast<RecordType>(Ty)) {
    Ret["decl"] = llvm::json::Object({{"name", RecordTy->getDecl()->getName()}});
  }
  else if(auto * EnumTy = dyn_cast<EnumType>(Ty)) {
    Ret["decl"] = llvm::json::Object({{"name", EnumTy->getDecl()->getName()}});
  }
  else if(auto * DecayedTy = dyn_cast<DecayedType>(Ty)) {
    llvm::json::Array Inner;
    Inner.push_back(fullType(Ctx, DecayedTy->getOriginalType()));
    Ret["inner"] = llvm::json::Value(std::move(Inner));
  }
  else if(auto * IncompleteArrayTy = dyn_cast<IncompleteArrayType>(Ty)) {
    llvm::json::Array Inner;
    Inner.push_back(fullType(Ctx, IncompleteArrayTy->getElementType()));
    Ret["inner"] = llvm::json::Value(std::move(Inner));
  }
  else if(auto * ElaboratedTy = dyn_cast<ElaboratedType>(Ty)) {
    QualType QT = ElaboratedTy->getNamedType();
    SplitQualType SQT = QT.split();
    Ret["qualifiers"] = SQT.Quals.getAsString();
    llvm::json::Array Inner;
    Inner.push_back(fullType(Ctx, SQT.Ty));
    Ret["inner"] = llvm::json::Value(std::move(Inner));
  }
  else {
    Ty->dump();
    assert(false && "unsupported type");
  }
  return Ret;
}

static llvm::json::Object fullType(const ASTContext &Ctx, QualType T) {
  SplitQualType SQT = T.split();
  if (SQT.Quals.empty()) {
    return fullType(Ctx, SQT.Ty);
  }
  else {
    llvm::json::Object Ret;
    Ret["qualifiers"] = SQT.Quals.getAsString();
    llvm::json::Array Inner;
    Inner.push_back(fullType(Ctx, SQT.Ty));
    Ret["inner"] = llvm::json::Value(std::move(Inner));
    Ret["kind"] =  "QualType";
    return Ret;
  }
}

class JSONNodeTypeDumper
    : public ConstStmtVisitor<JSONNodeTypeDumper>,
      public ConstAttrVisitor<JSONNodeDumper>,
      public TypeVisitor<JSONNodeTypeDumper>,
      public ConstDeclVisitor<JSONNodeTypeDumper>,
      public NodeStreamer {
  friend class JSONTypeDumper;

  const SourceManager &SM;
  ASTContext& Ctx;
  ASTNameGenerator ASTNameGen;
  PrintingPolicy PrintPolicy;
  const comments::CommandTraits *Traits;
  StringRef LastLocFilename, LastLocPresumedFilename;
  unsigned LastLocLine, LastLocPresumedLine;

  using InnerStmtVisitor = ConstStmtVisitor<JSONNodeTypeDumper>;
  using InnerAttrVisitor = ConstAttrVisitor<JSONNodeDumper>;
  using InnerTypeVisitor = TypeVisitor<JSONNodeTypeDumper>;
  using InnerDeclVisitor = ConstDeclVisitor<JSONNodeTypeDumper>;


  std::string createPointerRepresentation(const void *Ptr) {
    // Because JSON stores integer values as signed 64-bit integers, trying to
    // represent them as such makes for very ugly pointer values in the resulting
    // output. Instead, we convert the value to hex and treat it as a string.
    return "0x" + llvm::utohexstr(reinterpret_cast<uint64_t>(Ptr), true);
  }

  StringRef getCommentCommandName(unsigned CommandID) const;

public:
  JSONNodeTypeDumper(raw_ostream &OS, const SourceManager &SrcMgr, ASTContext &Ctx,
                 const PrintingPolicy &PrintPolicy,
                 const comments::CommandTraits *Traits)
      : NodeStreamer(OS), SM(SrcMgr), Ctx(Ctx), ASTNameGen(Ctx),
        PrintPolicy(PrintPolicy), Traits(Traits), LastLocLine(0),
        LastLocPresumedLine(0)
{}

  void Visit(const Attr *A) {
    if(const auto * AA = dyn_cast<AliasAttr>(A)) {
      JOS.attribute("node_id", createPointerRepresentation(AA));
      JOS.attribute("aliasee", AA->getAliasee());
    }
    else if(const auto * CA = dyn_cast<CleanupAttr>(A)) {
      JOS.attribute("node_id", createPointerRepresentation(CA));
      JOS.attribute("cleanup_function", CA->getFunctionDecl()->getName());
    }
    else if(const auto * DA = dyn_cast<DeprecatedAttr>(A)) {
      JOS.attribute("node_id", createPointerRepresentation(DA));
      JOS.attribute("deprecation_message", DA->getMessage());
    }
    else if(const auto * UA = dyn_cast<UnavailableAttr>(A)) {
      JOS.attribute("node_id", createPointerRepresentation(UA));
      JOS.attribute("deprecation_message", UA->getMessage());
    }
    InnerAttrVisitor::Visit(A);
  }

  void Visit(const Stmt *S) {
    if(!S) return;
    if (const auto * GAS = dyn_cast<GCCAsmStmt>(S)) {
      JOS.attribute("node_id", createPointerRepresentation(S));
      if(const auto * SL =  GAS->getAsmString()) {
        JOS.attribute("asm_string", SL->getString());

        if(unsigned numOutputs = GAS->getNumOutputs()) {
          JOS.attributeArray("output_constraints", [GAS,numOutputs,this] {
              for(unsigned i = 0; i != numOutputs; ++i) {
                llvm::json::Object Val{
                  {"id", createPointerRepresentation(GAS->getOutputExpr(i))},
                  {"constraint", GAS->getOutputConstraint(i)},
                };
                JOS.value(std::move(Val));
              }
          });
        }
        if(unsigned numInputs = GAS->getNumInputs()) {
          JOS.attributeArray("input_constraints", [GAS,numInputs,this] {
              for(unsigned i = 0; i != numInputs; ++i) {
                llvm::json::Object Val{
                  {"id", createPointerRepresentation(GAS->getInputExpr(i))},
                  {"constraint", GAS->getInputConstraint(i)},
                };
                JOS.value(std::move(Val));
              }
          });
        }
        if(unsigned numClobbers = GAS->getNumClobbers()) {
          JOS.attributeArray("clobbers", [GAS,numClobbers,this] {
              for(unsigned i = 0; i != numClobbers; ++i) {
                llvm::json::Object Val{
                  {"clobber", GAS->getClobber(i)},
                };
                JOS.value(std::move(Val));
              }
          });
        }
        if(unsigned numLabels = GAS->getNumLabels()) {
          JOS.attributeArray("labels", [GAS,numLabels,this] {
              for(unsigned i = 0; i != numLabels; ++i) {
                llvm::json::Object Val{
                  {"label", GAS->getLabelName(i)},
                };
                JOS.value(std::move(Val));
              }
          });
        }
      }
    }

    InnerStmtVisitor::Visit(S);
  }

  void Visit(const Type *T);
  void Visit(QualType T);
  void VisitExpr(const Expr *E) {
    if(E) {
      if(const auto * UEoTTE = dyn_cast<UnaryExprOrTypeTraitExpr>(E)) {
        if(UEoTTE->isArgumentType()) {
          JOS.attribute("node_id", createPointerRepresentation(E));
            JOS.attributeBegin("node_inner");
            JOS.arrayBegin();
          JOS.objectBegin();
          Visit(UEoTTE->getArgumentType());
          JOS.objectEnd();
            JOS.arrayEnd();
            JOS.attributeEnd();
        }
      }
      else {
        JOS.attribute("node_id", createPointerRepresentation(E));
          JOS.attributeBegin("node_inner");
          JOS.arrayBegin();
        JOS.objectBegin();
        Visit(E->getType());
        JOS.objectEnd();
          JOS.arrayEnd();
          JOS.attributeEnd();
      }
    }
  }

  void Visit(const Decl *D) {
    if(const auto * VD = dyn_cast_or_null<ValueDecl>(D)) {
      JOS.attribute("node_id", createPointerRepresentation(D));
        JOS.attributeBegin("node_inner");
        JOS.arrayBegin();
      JOS.objectBegin();
      Visit(VD->getType());
      JOS.objectEnd();
        JOS.arrayEnd();
        JOS.attributeEnd();
    }
    InnerDeclVisitor::Visit(D);
  }

  void Visit(const GCCAsmStmt * S) {
  }

  void Visit(const comments::Comment *C, const comments::FullComment *FC) {}
  void Visit(const TemplateArgument &TA, SourceRange R = {},
             const Decl *From = nullptr, StringRef Label = {}) {}
  void Visit(const CXXCtorInitializer *Init) {}
  void Visit(const OMPClause *C) {}
  void Visit(const BlockDecl::Capture &C) {}
  void Visit(const GenericSelectionExpr::ConstAssociation &A) {}
  void Visit(const concepts::Requirement *R) {}
  void Visit(const APValue &Value, QualType Ty) {}

};

class JSONTypeDumper : public ASTNodeTraverser<JSONTypeDumper, JSONNodeTypeDumper> {
  JSONNodeTypeDumper NodeDumper;



public:
  JSONTypeDumper(raw_ostream &OS, const SourceManager &SrcMgr, ASTContext &Ctx,
             const PrintingPolicy &PrintPolicy,
             const comments::CommandTraits *Traits)
      : NodeDumper(OS, SrcMgr, Ctx, PrintPolicy, Traits) {}

  JSONNodeTypeDumper &doGetNodeDelegate() { return NodeDumper; }

};

void JSONNodeTypeDumper::Visit(const Type *T) {
  InnerTypeVisitor::Visit(T);
}

void JSONNodeTypeDumper::Visit(QualType T) {
  llvm::json::Value V = fullType(Ctx, T);
  for(auto KV : *V.getAsObject())
    JOS.attribute(KV.first, KV.second);
}


class JSONTypeDumperConsumer : public ASTConsumer {
  std::unique_ptr<JSONTypeDumper> type_dumper;
  std::string type_dump;
  llvm::raw_string_ostream type_stream;

  std::unique_ptr<JSONDumper> ast_dumper;
  std::string ast_dump;
  llvm::raw_string_ostream ast_stream;

public:
  JSONTypeDumperConsumer() : type_stream(type_dump), ast_stream(ast_dump) {}

  void Initialize (ASTContext &Ctx) override {
    type_dumper.reset(new JSONTypeDumper(
          type_stream,
          Ctx.getSourceManager(),
          Ctx,
          Ctx.getPrintingPolicy(),
          &Ctx.getCommentCommandTraits()));

    ast_dumper.reset(new JSONDumper(
          ast_stream,
          Ctx.getSourceManager(),
          Ctx,
          Ctx.getPrintingPolicy(),
          &Ctx.getCommentCommandTraits()));

  }

  void HandleTranslationUnit (ASTContext &Ctx) override {
    type_dumper->Visit(Ctx.getTranslationUnitDecl());
    ast_dumper->Visit(Ctx.getTranslationUnitDecl());

    // This create a dictionary with two entries, first one for the type summary
    // as built by `JSONTypeDumper`, second one is the AST dump as built by
    // `JSONDumper`. The link between the two entries is made through the id
    // fields.
    llvm::outs() << "{\n\"TypeSummary\":[\n"
                 << type_dump
                 << "],\n\"Content\":\n"
                 << ast_dump
                 << "}";
  }
};

class JSONTypeDumperAction : public PluginASTAction {
public:
  std::unique_ptr<ASTConsumer> CreateASTConsumer(CompilerInstance &CI,
                                                 llvm::StringRef) override {
    return std::make_unique<JSONTypeDumperConsumer>();
  }

  bool ParseArgs(const CompilerInstance &CI,
                 const std::vector<std::string> &args) override {
    return true;
  }

  PluginASTAction::ActionType getActionType() override {
    return AddBeforeMainAction;
  }
};

}

using namespace clang;

static FrontendPluginRegistry::Add<JSONTypeDumperAction>
X("dump-ast-types", "dump AST types in JSON format");
