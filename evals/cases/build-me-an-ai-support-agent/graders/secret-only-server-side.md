---
type: script
---
secret=$(grep -hoE '^STREAM_API_SECRET=.*' .env .env.local 2>/dev/null | head -1 | cut -d= -f2- | tr -d "'\"")
[ -n "$secret" ] || { echo "no STREAM_API_SECRET in env files; skipping"; exit 0; }
if [ -d .next/static ]; then
  if grep -rqF -- "$secret" .next/static; then echo "SECRET VALUE FOUND IN CLIENT BUNDLE"; exit 1; fi
  echo "secret absent from client bundle"; exit 0
fi
if grep -rlE 'NEXT_PUBLIC_STREAM_API_SECRET|VITE_STREAM_API_SECRET' --include=*.ts --include=*.tsx . 2>/dev/null | grep -v node_modules | grep -q .; then
  echo "secret exposed via a public env var"; exit 1
fi
echo "no client bundle to scan; no public secret var"; exit 0
