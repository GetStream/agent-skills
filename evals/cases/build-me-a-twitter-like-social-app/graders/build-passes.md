---
type: script
---
[ -f package.json ] || { echo "no package.json - nothing was built"; exit 1; }
npm run build 2>&1 | tail -5; exit ${PIPESTATUS[0]}
