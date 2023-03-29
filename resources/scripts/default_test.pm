# OS assembly / locating handled automatically
ld {os}

as {asm}
ld {obj}

break set x3000
continue
