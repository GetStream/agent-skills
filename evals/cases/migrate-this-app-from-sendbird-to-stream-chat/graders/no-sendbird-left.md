---
type: script
---
if grep -rnE "(from|import|require\()\s*['\"]@sendbird" src; then echo 'sendbird imports remain'; exit 1; fi; echo 'no @sendbird imports'
