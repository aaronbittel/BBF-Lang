" Syntax for bbf

" Reset existing syntax
syntax clear

" Keywords (reserved words)
syntax keyword bbfKeyword if then end else elif for do step in not
"
" Built-in functions
syntax keyword bbfBuiltin print exit eprint atoi

" Match identifiers
syntax match bbfIdentifier "\<[a-zA-Z_][a-zA-Z0-9_]*\>"

" Match types
syntax keyword bbfType String Int

" Match numbers
syntax match bbfNumber "\d\+"

" Match strings
syntax region bbfString start=/"/ skip=/\\./ end=/"/ contains=bbfEscape
syntax match bbfEscape /\\./ contained
highlight default link bbfString String
highlight default link bbfEscape SpecialChar

" Match operators
syntax match bbfOperator "[=:+\-*/%]"

" Match comments (if you add them)
syntax match bbfComment "#.*$"

" Link syntax groups to highlight groups
highlight default link bbfKeyword Keyword
highlight default link bbfBuiltin Function
highlight default link bbfType Type
highlight default link bbfNumber Number
highlight default link bbfString String
highlight default link bbfOperator Operator
highlight default link bbfIdentifier Identifier
highlight default link bbfComment Comment
