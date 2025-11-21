_builtin_exit = """
; rdi: exit_code
exit:
    mov rax, 60
    syscall"""

_builtin_atoi = """
; rdi: str_ptr, rsi: str_len
atoi:
    push rbp
    mov rbp, rsp
    xor rax, rax
    mov r9, rdi ; r9: ptr into str
    lea r11, [rdi + rsi] ; r11: end ptr

.loop:
    cmp r9, r11
    je .return

    movzx r10, byte [r9]
    sub r10, '0'
    imul rax, 10
    add rax, r10
    inc r9
    jmp .loop

.return:
    pop rbp
    ret"""

_builtin_itoa = """
; rdi: int
itoa:
    mov rbx, 10 ; factor 10 used for division and modulo
    mov rax, rdi ; rax: number

    xor r8, r8 ; r8 == 0 => positive
    test rax, rax
    jns .positive ; jump if not sign
    neg rax ; rax = -rax
    inc r8 ; r8 == 1 => negative

.positive:
    mov r9, 32 ; r9: index

.loop:
    dec r9
    xor rdx, rdx
    div rbx ; rax / 10, remainder in rdx
    add dl, '0' ; take first byte of rdx
    mov byte [__itoa_buf+r9], dl ; only write first byte of rdx into buffer
    cmp rax, 0
    je .end_loop
    jmp .loop

.end_loop:
    cmp r8, 0 ; check if negative (0 == positve; 1 == negative)
    je .return
    dec r9
    mov byte [__itoa_buf+r9], '-'

.return:
    lea rax, [__itoa_buf + r9] ; pointer to start of string
    mov rdi, 32
    sub rdi, r9 ; length
    ret"""

_builtin_btoa = """
; rdi: bool
btoa:
    push rbp
    mov rbp, rsp

    cmp rdi, 1
    je .ret_true

    lea rax, [__false]
    mov rdi, __false_len
    jmp .end

.ret_true:
    lea rax, [__true]
    mov rdi, __true_len

.end:
    pop rbp
    ret
"""

_builtin_stdout = """
; rdi: str_ptr, rsi: str_len
stdout:
    push rbp
    mov rbp, rsp

    mov r9, rdi
    mov r10, rsi

    mov rax, 1
    mov rdi, 1 ; stdout
    mov rsi, r9
    mov rdx, r10
    syscall

    pop rbp
    ret"""

_builtin_stderr = """
; rdi: str_ptr, rsi: str_len
stderr:
    push rbp
    mov rbp, rsp

    mov r9, rdi
    mov r10, rsi

    mov rax, 1
    mov rdi, 2 ; stderr
    mov rsi, r9
    mov rdx, r10
    syscall

    pop rbp
    ret"""

_builtin_c_strlen = """
; rdi: str_ptr
c_strlen:
    xor rax, rax

.loop:
    cmp byte [rdi], 0
    je .return
    inc rdi
    inc rax
    jmp .loop

.return:
    ret"""
