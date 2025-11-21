#set page(margin: 1cm, fill: rgb("#B0B0B0"))
#show math.equation: set block(breakable: true)

#align(center)[= Grammar for BBFLang]
#v(1em)

#let e(x) = math.text("\"" + str(x) + "\"")
#let k(x) = math.text("'" + str(x) + "'")

#block(breakable: true)
$
"Program" arrow & {"TopLevelStmt"} "EOF" \
"TopLevelStmt" arrow & cases(
  "FnDef",
  "Stmt"
) \
"Stmt" arrow & cases(
  "CompoundStmt",
  "SimpleStmt",
) \
"CompoundStmt" arrow & cases(
  "IfStmt",
  "ForStmt",
  "DoBlock",
) \
"SimpleStmt" arrow & cases(
  "Declaration",
  "Assignment",
  "ExprStmt",
  "ReturnStmt"
) \
"ExprStmt" arrow & "Expr" \
"FnDef" arrow & #k("fn") italic("Name") #e("(") {"Params"} #e(")") \" arrow \" italic("VarType") #k("do") "Block" #k("end") \
"Params" arrow & cases(
  italic("Name") #e(":") italic("VarType"),
  italic("Name") #e(":") italic("VarType") #e(",") "Params",
) \
"IfStmt" arrow & cases(
  #k("if") "Expr" #k("then") "Block" "ElifStmt",
  #k("if") "Expr" #k("then") "Block" ["ElseBlock"] #k("end"),
) \
"ElifStmt" arrow & cases(
  #k("elif") "Expr" #k("then") "Block" "ElifStmt",
  #k("elif") "Expr" #k("then") "Block" ["ElseBlock"] #k("end"),
) \
"ElseBlock" arrow & #k("else") "Block" \
"ForStmt" arrow & #k("for") italic("Name") #k("in") "Range" #k("do") "Block" #k("end") \
"Range" arrow & "Expr" #e("..") [#e("=")] "Expr" \
"DoBlock" arrow & #k("do") "Block" #k("end")\
"Block" arrow & {"Stmt"} \
"Declaration" arrow & italic("Name") #e(":") "VarType" #e("=") "Expr" \
"Assignment" arrow & italic("Name") #e("=") "Expr" \
"ReturnStmt" arrow & #k("return") ["Expr"] \
"Expr" arrow & "BoolExpr" \
"BoolExpr" arrow & "OrExpr" (#k("or") "OrExpr")* \
"OrExpr" arrow & "AndExpr" (#k("and") "AndExpr")* \
"AndExpr" arrow & "Equality" \
"Equality" arrow & "Comparison" ( (#e("!=") | #e("==")) "Comparison" )* \
"Comparison" arrow & "Term" ((#e(">") | #e(">=") | #e("<") | #e("<=")) "Term")* \
"Term" arrow & "Factor" ((#e("-") | #e("+")) "Factor")* \
"Factor" arrow & "Unary" ((#e("/") | #e("*") | #e("%")) "Unary")* \
"Unary" arrow & cases(
  ( #e("-") | #e("+") | #k("not")) "Unary",
  "Primary",
) \
"Primary" arrow & cases(
  italic("IntegerLit"),
  italic("StringLit"),
  italic("Name"),
  #e("(") "Expr" #e(")"),
  "argv" #e("[") "Expr" #e("]"),
  italic("Name") #e("(") ["Arguments"] #e(")"),
  #k("true"),
  #k("false"),
) \
"Arguments" arrow & cases(
  "Expr",
  "Expr" #e(",") "Arguments"
) \
$
