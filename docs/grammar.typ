= Grammar for BBF-Lang

#let e(x) = math.text("\"" + str(x) + "\"")

$
"Program" arrow & "{Statement}" \
"Statement" arrow & cases(
                    "exit(Expression)",
                    "print(Expression)",
                    "Identifier = Expression",
                    "If-Statement",
                    ) \
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
    & "Integer" \
    & | "String" \
    & | "Identifier" \
    & | #e(("(")) "Expression" #e((")")) \
"Condition" arrow & "Expression"
$

