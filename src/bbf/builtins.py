_builtin_exit = """
; rdi: exit_code
__builtin_exit:
    mov rax, 60
    syscall"""

_builtin_print = """
; rdi: str_ptr, rsi: str_len
__builtin_print:
    mov rax, 1 ; sys_write
    mov rdi, 1 ; stdout
    syscall
    ret"""

_builtin_eprint = """
; rdi: str_ptr, rsi: str_len
__builtin_eprint:
    mov rax, 1 ; sys_write
    mov rdi, 2 ; stderr
    syscall
    ret"""

_builtin_atoi = """
; rdi: str_ptr
__builtin_atoi:
    mov rax, 0
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
    ret"""

_builtin_itoa = """
; rdi: int
__builtin_itoa:
    mov rbx, 10 ; factor 10 used for division and modulo
    mov rax, rdi ; rax: number

    xor r8, r8 ; r8 == 0 => positive
    test rax, rax
    jns .positive ; jump if not sign
    neg rax ; rax = -rax
    inc r8 ; r8 == 1 => negative

.positive:
    mov r9, 31 ; r9: index

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
    mov rdx, 32
    sub rdx, r9 ; length
    ret"""

_builtin_write = """
; rdi: str_ptr, rsi: str_len
__builtin_write:
    mov r9, rsi
    mov r8, rdi

    mov rax, 1
    mov rdi, 1
    mov rsi, r8
    mov rdx, r9
    syscall
    ret"""

_builtin_c_strlen = """
; rdi: str_ptr
__builtin_c_strlen:
    xor rax, rax

.loop:
    cmp byte [rdi], 0
    je .return
    inc rdi
    inc rax
    jmp .loop

.return:
    ret"""
