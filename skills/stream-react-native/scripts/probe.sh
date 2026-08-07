#!/usr/bin/env bash
# Project signals — read-only probe of an RN/Expo workspace.
#
#   bash scripts/probe.sh [project-dir]     # defaults to cwd
#
# Prints one labelled block per signal. Run ONCE per session; hold the result in
# context. Re-run only after a directory change, an install, or a lane change.
set -u
cd "${1:-.}" 2>/dev/null || { echo "PROBE_ERROR: no such directory: ${1:-.}"; exit 1; }
echo "=== CWD ==="; pwd

echo "=== PACKAGE ==="
if [ -f package.json ]; then
  grep -oE '"(stream-chat|stream-chat-react-native|stream-chat-expo|@stream-io/video-react-native-sdk|@stream-io/feeds-react-native-sdk|@stream-io/react-native-webrtc|@stream-io/react-native-callingx|react-native|react|react-dom|expo|@react-navigation/[^"]+|expo-router|react-native-reanimated|react-native-worklets|react-native-teleport|react-native-gesture-handler|react-native-svg|@react-native-community/netinfo|@op-engineering/op-sqlite|@sendbird/[^"]+)": *"[^"]*"' package.json
else
  echo "-"
fi

echo "=== EXPO ==="
find . -maxdepth 2 \( -name app.json -o -name 'app.config.*' -o -path './app/_layout.*' \) -print 2>/dev/null

echo "=== NATIVE ==="
find . -maxdepth 2 \( -name ios -o -name android \) -type d -print 2>/dev/null

echo "=== CONFIG ==="
find . -maxdepth 2 \( -name babel.config.js -o -name metro.config.js \) -print 2>/dev/null

echo "=== EXPO_SDK ==="
node -e 'try{console.log(require("./node_modules/expo/package.json").version)}catch(e){try{console.log(require("./package.json").dependencies.expo||"-")}catch(e){console.log("-")}}' 2>/dev/null || echo "-"

echo "=== PKG_MANAGER ==="
for l in pnpm-lock.yaml yarn.lock package-lock.json bun.lockb; do [ -f "$l" ] && echo "$l"; done
[ -f pnpm-lock.yaml ] || [ -f yarn.lock ] || [ -f package-lock.json ] || [ -f bun.lockb ] || echo "-"

echo "=== NEW_ARCH ==="
grep -hoE 'newArchEnabled" *[=:] *"?(true|false)|newArchEnabled *= *(true|false)' \
  android/gradle.properties app.json app.config.js 2>/dev/null | sort -u | grep . || echo "-"

echo "=== REANIMATED_FLAG ==="
node -e 'try{const p=require("./package.json");console.log(JSON.stringify(p.reanimated?.staticFeatureFlags??"-"))}catch(e){console.log("-")}' 2>/dev/null || echo "-"

echo "=== EMPTY ==="
[ -z "$(ls -A 2>/dev/null)" ] && echo "EMPTY_CWD" || echo "NON_EMPTY"

# Peer-version hazards the agent must act on, asserted here rather than remembered.
echo "=== HAZARDS ==="
node - <<'NODE' 2>/dev/null || echo "-"
const fs = require('fs');
const v = n => { try { return require(`./node_modules/${n}/package.json`).version } catch { return null } };
const lt = (a, b) => {
  const pa = a.split('.').map(Number), pb = b.split('.').map(Number);
  for (let i = 0; i < 3; i++) { if ((pa[i]|0) !== (pb[i]|0)) return (pa[i]|0) < (pb[i]|0) }
  return false;
};
const out = [];
const rea = v('react-native-reanimated'), wor = v('react-native-worklets');
if (rea && lt(rea, '4.5.1')) out.push(`reanimated ${rea} < 4.5.1 — known crash pair, bump + rebuild native`);
if (wor && lt(wor, '0.10.2')) out.push(`worklets ${wor} < 0.10.2 — known crash pair, bump + rebuild native`);
if (rea && rea.startsWith('4.')) {
  const p = JSON.parse(fs.readFileSync('./package.json', 'utf8'));
  const f = p.reanimated?.staticFeatureFlags?.FORCE_REACT_RENDER_FOR_SETTLED_ANIMATIONS;
  if (f !== false) out.push('Reanimated 4 without FORCE_REACT_RENDER_FOR_SETTLED_ANIMATIONS:false in root package.json — set it and pod install');
}
const expo = v('expo');
const hasNav = fs.existsSync('./node_modules/@react-navigation/native');
if (expo && !lt(expo, '56.0.0') && fs.existsSync('./node_modules/expo-router') && hasNav) {
  out.push(`expo ${expo} + expo-router + @react-navigation/* — Metro will refuse to bundle; uninstall @react-navigation/*`);
}
console.log(out.length ? out.join('\n') : 'none');
NODE
