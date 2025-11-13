#set page(margin: 1cm)
#show math.equation: set block(breakable: true)

#align(center)[= Grammar for BBF-Lang]
#v(1em)

#let e(x) = math.text("\"" + str(x) + "\"")

#block(breakable: true)
$
"Program" arrow & "{TopLevel}" \
"TopLevel" arrow & "FunctionDefiniton" | "GlobalStatement" \
"GlobalStatement" arrow & cases(
  "Declaration",
  "Assignment",
  "IfStatement",
  "ForStatement",
  "DoBlock",
  "FunctionCall",
) \
"FunctionDefiniton" arrow &
  #e("fn") "Identifier" #e("(") ["FuncDefArgs"] #e(")") \"arrow\" "VarType" #e("do") \
  & {"FunctionStatement"} \
  & #e("end") \
"FunctionStatement" arrow & "GlobalStatement" | "ReturnStatement" \
"ReturnStatement" arrow & #e("return") "Expression" \
"Declaration" arrow & "Identifier" #e(":") "VarType" #e("=") "Expression" \
"Assignment" arrow & "Identifier" #e("=") "Expression" \

"IfStatement" arrow &
  #e("if") "Condition" #e("then") \
  & "Block" \
  & {"ElifClause"} \
  & ["ElseClause"] \
  & #e("end") \
"ElifClause" arrow & #e("elif") "Condition" #e("then") "Block" \
"ElseClause" arrow & #e("else") "Block" \
"ForStatement" arrow & #e("for") "Identifier" #e("in") "Range" #e("do") "Block" #e("end") \
"Range" arrow & "Expression"..[#e("=")]"Expression" \
"Block" arrow & {"FunctionStatement"} \
"DoBlock" arrow & #e("do") "Block" #e("end") \

"FuncDefArgs" arrow & "FuncDefArg" {#e(",") "FuncDefArg"} \
"FuncDefArg" arrow & "Identifier" #e(":") "VarType" \
"FunctionCall" arrow & "Identifier" #e("(") ["ArgList"] #e(")") \
"ArgList" arrow & "Expression" {#e(",") "Expression"} \
"Condition" arrow & "Expression" \
"Identifier" arrow & "Letter" ("Letter" | "Digit" )* \
"VarType" arrow & cases(
  "Int",
  "String",
  "Void",
) \
$
#pagebreak()
$
"Expression" arrow & "Equality" \
"Equality" arrow & "Comparison" ( (#e("!=") | #e("==")) "Comparison" )* \
"Comparison" arrow & "Term" ((#e(">") | #e(">=") | #e("<") | #e("<=")) "Term")* \
"Term" arrow & "Factor" ((#e("-") | #e("+")) "Factor")* \
"Factor" arrow & "Unary" ((#e("/") | #e("*") | #e("%")) "Unary")* \
"Unary" arrow & ( #e("-") | #e("+") | "not") "Unary" \ & | "Primary" \
"Primary" arrow & cases(
  "IntegerLit",
  "StringLit",
  "Identifier",
  #e("(") "Expression" #e(")"),
  "argv" #e("[") "Expression" #e("]"),
  "FunctionCall",
) \
"IntegerLit" arrow & (#e("+") | #e("-"))? "Digit" ( #e("_") "Digit" | "Digit" )* \
"StringLit" arrow & #e("\"") ("~"#e("\""))* #e("\"") \
"Letter" arrow & #e("A")..#e("Z") | #e("a")..#e("z") | #e("_") \
"Digit" arrow & #e("0")..#e("9") \
$


