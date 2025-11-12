#set page(margin: 1cm)

#align(center)[= Grammar for BBF-Lang]
#v(1em)

#let e(x) = math.text("\"" + str(x) + "\"")

$
"Program" arrow & "{Statement}" \
"Statement" arrow & cases(
  "exit(Expression)",
  "print(Expression)",
  "eprint(Expression)",
  "Declaration",
  "Assignment",
  "If-Statement",
  "For-Statement",
) \
"Declaration" arrow &  "Identifier : (" #e("Int") | #e("String") ")" = "Expression" \
"Assignment" arrow & "Identifier" = "Expression" \
"Scope" arrow & {"Statement"} \
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
"Primary" arrow
    & "IntegerLit" \
    & | "StringLit" \
    & | "Identifier" \
    & | #e("(") "Expression" #e(")") \
    & | "argv" #e("[") "Expression" #e("]") \
    & | "atoi(Expression)" \
"Condition" arrow & "Expression" \
"Identifier" arrow & "Letter" ("Letter" | "Digit" )* \
"IntegerLit" arrow & (#e("+") | #e("-"))? "Digit" ( #e("_") "Digit" | "Digit" )* \
"StringLit" arrow & #e("\"") ("~"#e("\""))* #e("\"") \
"Letter" arrow & #e("A")..#e("Z") | #e("a")..#e("z") | #e("_") \
"Digit" arrow & #e("0")..#e("9") \
$

