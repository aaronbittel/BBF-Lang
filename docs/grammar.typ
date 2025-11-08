= Grammar for BBF-Lang

#let e(x) = math.text("\"" + str(x) + "\"")

$
"Program" arrow & "{Statement}" \
"Statement" arrow & cases(
                    "exit(Expression)",
                    "print(Expression)",
                    "Declaration",
                    "Assignment",
                    "If-Statement",
                    ) \
"Declaration" arrow &  "Identifier : (" #(e("Int")) | #(e("String")) ")" = "Expression" \
"Assignment" arrow & "Identifier" = "Expression" \
"If-Statement" arrow & "if Condition then {Statement} {Elif-Statement} [Else-Statement] end" \
"Elif-Statement" arrow & "elif Condition then {Statement}" \
"Else-Statement" arrow & "else {Statement}" \
"Expression" arrow & "Equality" \
"Equality" arrow & "Comparison" ( (#(e("!=")) | #(e("=="))) "Comparison" )* \
"Comparison" arrow & "Term" ((#(e(">")) | #(e(">=")) | #(e("<")) | #(e("<="))) "Term")* \
"Term" arrow & "Factor" ((#(e("-")) | #(e("+"))) "Factor")* \
"Factor" arrow & "Unary" (((#e("/")) | #(e("*")) | #(e("%"))) "Unary")* \
"Unary" arrow & ( #(e("-")) | "not") "Unary" \ & | "Primary" \
"Primary" arrow
    & "IntegerLit" \
    & | "StringLit" \
    & | "Identifier" \
    & | #e(("(")) "Expression" #e((")")) \
"Condition" arrow & "Expression"
$

