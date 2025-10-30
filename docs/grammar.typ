= Grammar for BBF-Lang

$  "[Prog]" arrow & "[Stmt]*"\
  "[Stmt]" arrow & cases(
                    "exit([expr])",
                    "ident = [expr]"
                    )\
  "[expr]" arrow & cases(
                    "int_lit",
                    "ident"
                    )\
$
