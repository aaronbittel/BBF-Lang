_builtin_exit = """
; rdi: exit_code
__sys_exit:
    mov rax, SYS_EXIT
    syscall"""

_builtin_atoi = """
; rdi: str_ptr, rsi: str_len
__builtin_atoi:
    FN_PROLOGUE
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
    FN_EPILOGUE"""

_builtin_itoa = """
; rdi: int
__builtin_itoa:
    FN_PROLOGUE
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
    FN_EPILOGUE"""

_builtin_btoa = """
; rdi: bool
__builtin_btoa:
    FN_PROLOGUE

    cmp rdi, 1
    je .ret_true

    lea rax, [__false]
    mov rdi, __false_len
    jmp .end

.ret_true:
    lea rax, [__true]
    mov rdi, __true_len

.end:
    FN_EPILOGUE
"""

_builtin_stdout = """
; rdi: str_ptr, rsi: str_len
__sys_stdout:
    FN_PROLOGUE

    mov r9, rdi
    mov r10, rsi

    mov rax, SYS_WRITE
    mov rdi, STDOUT
    mov rsi, r9
    mov rdx, r10
    syscall

    FN_EPILOGUE"""

_builtin_stderr = """
; rdi: str_ptr, rsi: str_len
__sys_stderr:
    FN_PROLOGUE

    mov r9, rdi
    mov r10, rsi

    mov rax, SYS_WRITE
    mov rdi, STDERR
    mov rsi, r9
    mov rdx, r10
    syscall

    FN_EPILOGUE"""

_builtin_c_strlen = """
; rdi: str_ptr
__builtin_c_strlen:
    FN_PROLOGUE
    xor rax, rax

.loop:
    cmp byte [rdi], 0
    je .return
    inc rdi
    inc rax
    jmp .loop

.return:
    FN_EPILOGUE"""

_builtin_read_entire_file = """
; rdi: ptr_filename, _rsi: len (unused) -> null-terminated string for `sys_open`
__builtin_read_entire_file:
    FN_PROLOGUE

    mov rsi, RDONLY
    mov rdx, 0
    call __sys_open
    mov r10, rax ; r10: fd

    PUSH_MEM_PTR
    pop r9     ; r9: out_ptr
    xor r8, r8 ; r8: total bytes
    mov rdi, r10
    mov rsi, r9
    mov rdx, PAGE_SIZE

.loop:
    call __sys_read

    add r8, rax
    add rsi, rax
    cmp rax, PAGE_SIZE
    je .loop

    mov rdi, r10
    call __sys_close

    ADD_MEM_PTR r8, 1

    mov rax, r9
    mov rdi, r8
    FN_EPILOGUE"""

_builtin_open_file = """
; rdi: filename_ptr, rsi: flags, rdx: mode
__sys_open:
    mov rax, SYS_OPEN
    syscall
    ret"""

_builtin_close = """
; rdi: fd
__sys_close:
    mov rax, SYS_CLOSE
    syscall
    ret"""

_builtin_read = """
; rdi: fd, rsi: ptr, rdx: count
__sys_read:
    mov rax, SYS_READ
    syscall
    ret"""

_builtin_mmap = """
; rdi: length
__sys_mmap:
    mov r9, rdi ; r9: length

    mov rax, SYS_MMAP
    mov rdi, 0              ; addr = NULL (let kernel choose)
    mov rsi, r9             ; length = 1 MB
    mov rdx, 3              ; PROT_READ | PROT_WRITE
    mov r10, 0x20 | 0x02    ; MAP_PRIVATE | MAP_ANONYMOUS
    mov r8, -1              ; fd = -1
    mov r9, 0               ; offset = 0
    syscall
    ret
"""

_builtin_strcmp = """
; rdi: ptr1, rsi: len1, rdx: ptr2, rcx: len2
__builtin_strcmp:
    ; compare lengths
    cmp rsi, rcx
    jne .return_false

    test rsi, rsi
    je .return_true

    ; compare content
.loop:
    mov al, byte [rdi]
    mov bl, byte [rdx]
    cmp al, bl
    jne .return_false

    ; move ptrs forward
    inc rdi
    inc rdx

    ; decrement lhs length
    dec rsi

    jnz .loop

.return_true:
    mov rax, TRUE
    jmp .end

.return_false:
    mov rax, FALSE

.end:
    ret"""

_builtin_append_8 = """
; rdi: struct_ptr, rsi: int / bool
__builtin_append_8:
    FN_PROLOGUE

    RESERVE_SPACE 8
    mov [rbp-8], rdi

    mov r11, rsi

    PUSH_PTR_STRUCT_FIELD -8, 8
    pop rsi
    PUSH_PTR_STRUCT_FIELD -8, 16
    pop rdx

    cmp rsi, rdx
    jl .add

    push rdx ; save old_cap

    PUSH_PTR_STRUCT_FIELD -8, 0
    pop rdx ; old data ptr

    PUSH_MEM_PTR
    pop r8 ; new data ptr
    STORE_PTR_STRUCT_FIELD -8, 0, r8 ; save new data ptr into struct

    mov rdi, r8
    call __builtin_copy_slice_8

    pop rdx ; restore old_cap
    shl rdx, 1
    STORE_PTR_STRUCT_FIELD -8, 16, rdx
    ADD_MEM_PTR rdx, 8

.add:
    PUSH_PTR_STRUCT_FIELD -8, 0
    pop rax
    mov qword [rax + rsi * 8], r11
    inc rsi
    STORE_PTR_STRUCT_FIELD -8, 8, rsi

    FN_EPILOGUE

; rdi: new_ptr, rsi: len, rdx: old_ptr
__builtin_copy_slice_8:
    mov r9, rdi  ; r9:  new_ptr
    mov r10, rsi ; r10: len_count

.loop:
    cmp r10, 0
    je .end

    mov rax, [rdx]
    mov [r9], rax
    add r9, 8
    add rdx, 8
    dec r10
    jmp .loop

.end:
    ret
"""

_builtin_append_16 = """
; rdi: struct_ptr, rsi: str_ptr, rdx: str_len
__builtin_append_16:
    FN_PROLOGUE
    RESERVE_SPACE 8
    mov [rbp-8], rdi

    push rdx ; save str_len
    mov r11, rsi

    PUSH_PTR_STRUCT_FIELD -8, 8
    pop rsi ; struct len
    PUSH_PTR_STRUCT_FIELD -8, 16
    pop r13 ; struct cap

    cmp rsi, r13
    jl .add

    PUSH_PTR_STRUCT_FIELD -8, 0
    pop rdx ; old data ptr

    PUSH_MEM_PTR
    pop r8 ; new data ptr
    STORE_PTR_STRUCT_FIELD -8, 0, r8 ; save new data ptr into struct

    mov rdi, r8
    call __builtin_copy_slice_16

    shl r13, 1
    STORE_PTR_STRUCT_FIELD -8, 16, r13
    ADD_MEM_PTR r13, 16

.add:
    PUSH_PTR_STRUCT_FIELD -8, 0
    pop rax

    mov r12, rsi
    shl r12, 4
    mov qword [rax + r12], r11
    add r12, 8
    pop rdx ; restore str_len
    mov qword [rax + r12], rdx

    inc rsi
    STORE_PTR_STRUCT_FIELD -8, 8, rsi

    FN_EPILOGUE

; rdi: new_ptr, rsi: len, rdx: old_ptr
__builtin_copy_slice_16:
    mov r9, rdi  ; r9:  new_ptr
    mov r10, rsi ; r10: len_count

.loop:
    cmp r10, 0
    je .end

    mov rax, [rdx]
    mov [r9], rax
    add r9, 8
    add rdx, 8
    mov rax, [rdx]
    mov [r9], rax
    add r9, 8
    add rdx, 8
    dec r10
    jmp .loop

.end:
    ret
"""
