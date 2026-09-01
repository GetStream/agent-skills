---
type: script
---
n=$(find app -path '*token*' -name 'route.ts' | wc -l); echo "token routes: $n"; [ "$n" -eq 1 ]
