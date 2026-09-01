---
# timeout may be a named *MINUTES constant
type: regex
target: files
match: contains
---
banUser[\s\S]{0,200}timeout:\s*(60\b|[A-Z_]*MINUTES?\w*\b)
