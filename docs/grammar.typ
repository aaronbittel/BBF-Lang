= Grammar for BBF-Lang

#let e(x) = math.text("\"" + str(x) + "\"")

$
"Program" arrow & "Statement*" \
"Statement" arrow & cases(
                    "exit(Expression)",
                    "print(Expression)",
                    "Identifier = Expression"
                    ) \
"Expression" arrow & "Factor" ((#(e("-")) | #(e("+"))) "Factor")* \
"Factor" arrow & "Unary" (((#e("/")) | #(e("*")) | #(e("%"))) "Unary")* \
"Unary" arrow & #(e("-")) "Unary" \ & | "Primary" \
"Primary" arrow
    & "Integer" \
    & | "String" \
    & | "Identifier" \
    & | #e(("(")) "Expression" #e((")")) \
$

