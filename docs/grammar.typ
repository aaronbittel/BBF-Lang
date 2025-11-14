#set page(margin: 1cm, fill: rgb("#B0B0B0"))
#show math.equation: set block(breakable: true)

#align(center)[= Grammar for BBFLang]
#v(1em)

#let e(x) = math.text("\"" + str(x) + "\"")
#let k(x) = math.text("'" + str(x) + "'")

#block(breakable: true)
$
"Program" arrow & {"TopLevelStatement"} "EOF" \
"TopLevelStatement" arrow & cases(
  "FunctionDefinition",
  "Statement"
) \
"Statement" arrow & cases(
  "CompoundStatement",
  "SimpleStatement",
) \
"CompoundStatement" arrow & cases(
  "IfStatement",
  "ForStatement",
  "DoBlock",
) \
"SimpleStatement" arrow & cases(
  "Declaration",
  "Assignment",
  "ExpressionStmt",
) \
"ExpressionStmt" arrow & "Expression" \
"IfStatement" arrow & cases(
  #k("if") "Expression" #k("then") "Block" "ElifStatement",
  #k("if") "Expression" #k("then") "Block" ["ElseBlock"] #k("end"),
) \
"ElifStatement" arrow & cases(
  #k("elif") "Expression" #k("then") "Block" "ElifStatement",
  #k("elif") "Expression" #k("then") "Block" ["ElseBlock"] #k("end"),
) \
"ElseBlock" arrow & #k("else") "Block" \
"ForStatement" arrow & #k("for") italic("Name") #k("in") "Range" #k("do") "Block" #k("end") \
"Range" arrow & "Expression" #e("..") [#e("=")] "Expression" \
"DoBlock" arrow & #k("do") "Block" #k("end")\
"Block" arrow & {"Statement"} \
"Declaration" arrow & italic("Name") #e(":") "VarType" #e("=") "Expression" \
"Assignment" arrow & italic("Name") #e("=") "Expression" \
"Expression" arrow & "Equality" \
"Equality" arrow & "Comparison" ( (#e("!=") | #e("==")) "Comparison" )* \
"Comparison" arrow & "Term" ((#e(">") | #e(">=") | #e("<") | #e("<=")) "Term")* \
"Term" arrow & "Factor" ((#e("-") | #e("+")) "Factor")* \
"Factor" arrow & "Unary" ((#e("/") | #e("*") | #e("%")) "Unary")* \
"Unary" arrow & cases(
  ( #e("-") | #e("+") | "not") "Unary",
  "Primary",
) \
"Primary" arrow & cases(
  italic("IntegerLit"),
  italic("StringLit"),
  italic("Name"),
  #e("(") "Expression" #e(")"),
  "argv" #e("[") "Expression" #e("]"),
  italic("Name") #e("(") ["Arguments"] #e(")"),
) \
"Arguments" arrow & cases(
  "Expression",
  "Expression" #e(",") "Arguments"
) \
$
