#set page(margin: 1cm)
#show math.equation: set block(breakable: true)

#align(center)[= Grammar for BBF-Lang]
#v(1em)

#let e(x) = math.text("\"" + str(x) + "\"")

#block(breakable: true)
$
"Program" arrow & "{Statement}" \
"Statement" arrow & cases(
  "Declaration",
  "Assignment",
  "If-Statement",
  "For-Statement",
  "Scope-Statement",
  "FunctionCall",
) \
"Declaration" arrow &  "Identifier" #e(":") "VarType" #e("=") "Expression" \
"Assignment" arrow & "Identifier" #e("=") "Expression" \
"Scope" arrow & {"Statement"} \
"Scope-Statement" arrow & "do" {"Statement"} "end" \
"If-Statement" arrow & "if Condition then" \ & "{Scope}" \ & "{Elif-Statement}" \ & "[Else-Statement]" \ &  "end" \
"Elif-Statement" arrow & "elif Condition then {Scope}" \
"Else-Statement" arrow & "else {Scope}" \
"For-Statement" arrow & "for Identifier in Range do {Scope} end" \
"Range" arrow & "Expression"..[#e("=")]"Expression" \
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
"FunctionCall" arrow & "Identifier" #e("(") ["ArgumentList"] #e(")") \
"ArgumentList" arrow & "Expression" | "Expression", "ArgumentList" \
"Condition" arrow & "Expression" \
"Identifier" arrow & "Letter" ("Letter" | "Digit" )* \
"IntegerLit" arrow & (#e("+") | #e("-"))? "Digit" ( #e("_") "Digit" | "Digit" )* \
"StringLit" arrow & #e("\"") ("~"#e("\""))* #e("\"") \
"Letter" arrow & #e("A")..#e("Z") | #e("a")..#e("z") | #e("_") \
"Digit" arrow & #e("0")..#e("9") \
"VarType" arrow & cases(
  "Int",
  "String",
  "Void",
) \
$

