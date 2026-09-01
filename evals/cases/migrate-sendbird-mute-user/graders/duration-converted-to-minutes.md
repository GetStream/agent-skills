---
type: regex
target: files
match: contains
# the value may live in a named constant (SILENCE_TIMEOUT_MINUTES = 60); the literal alone missed a correct migration in C
---
timeout:\s*60\b|[A-Z_]*MINUTES?\w*\s*=\s*60\b
