_macro_push_intlit = """
%macro PUSH_INT 1
    ; %1: value
    mov rax, %1
    push rax
%endmacro"""

_macro_push_slice = """
%macro PUSH_SLICE 2
    ; %1: ptr
    ; %2: len
    lea rax, [%1]
    push rax
    push qword [%2]
%endmacro"""

_macro_push_bool = """
%macro PUSH_BOOL 1
    ; %1: value (1 true, 0 false)
    %if %1
        push TRUE
    %else
        push FALSE
    %endif
%endmacro"""

_macro_program_prologue = """
%macro PROGRAM_PROLOGUE 0
    ; init base pointer
    mov rbp, rsp

    ; save argc and argv into .bss
    mov rax, [rbp]
    mov [__argc], rax
    lea rax, [rbp+8] ; addr of rbp + 8
    mov [__argv], rax

%endmacro"""

_macro_fn_prologue = """
%macro FN_PROLOGUE 0
    push rbp
    mov rbp, rsp
%endmacro"""

_macro_fn_epologue = """
%macro FN_EPILOGUE 0
    mov rsp, rbp
    pop rbp
    ret
%endmacro"""

_macro_binary_add = """
%macro PUSH_BINARY_ADD 0
    pop rbx
    pop rax
    add rax, rbx
    push rax
%endmacro"""

_macro_binary_sub = """
%macro PUSH_BINARY_SUB 0
    pop rbx
    pop rax
    sub rax, rbx
    push rax
%endmacro"""

_macro_binary_mul = """
%macro PUSH_BINARY_MUL 0
    pop rbx
    pop rax
    cqo
    imul rbx
    push rax
%endmacro"""

_macro_binary_div = """
%macro PUSH_BINARY_DIV 0
    pop rbx
    pop rax
    cqo
    idiv rbx
    push rax
%endmacro"""

_macro_binary_mod = """
%macro PUSH_BINARY_MOD 0
    pop rbx
    pop rax
    cqo
    idiv rbx
    push rdx
%endmacro"""

_macro_compare = """
%macro PUSH_COMPARE 1
    ; %1 = setcc mnemonic
    pop rbx
    pop rax
    cmp rax, rbx
    %1 al
    movzx rax, al
    push rax
%endmacro"""

_macro_argv_access = """
%macro PUSH_ARGV_STRING 0
    pop rax
    imul rax, 8 ; calc offset into argv

    mov rbx, [__argv] ; addr of ptr to arg[0]
    add rbx, rax ; addr of ptr to arg[i]
    mov rdi, [rbx] ; ptr to arg[i]

    push rdi ; str_ptr
    call c_strlen
    push rax ; str_len
%endmacro"""

_macro_negate = """
%macro PUSH_NEGATE 0
    pop rax
    neg rax
    push rax
%endmacro"""

_macro_check_bool_jump = """
%macro CHECK_BOOL_JUMP 2
    ; %1: jump_label
    ; %2: value
    pop rax
    cmp rax, %2
    je %1
%endmacro"""

_macro_reserve_space = """
%macro RESERVE_SPACE 1
    ; %1: size
    sub rsp, %1
%endmacro
"""

_macro_free_space = """
%macro FREE_SPACE 1
    ; %1: size
    add rsp, %1
%endmacro
"""

_macro_argc = """
%macro PUSH_ARGC 0
    push qword [__argc]
%endmacro
"""

_macro_push_var = """
%macro PUSH_VAR 1
    ; %1: offset
    push qword [rbp%1]
%endmacro"""

_macro_store_var = """
%macro STORE_VAR 1
    ; %1: offset
    pop rax
    mov [rbp%1], rax
%endmacro"""
