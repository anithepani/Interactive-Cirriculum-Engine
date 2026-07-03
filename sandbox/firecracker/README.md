# Firecracker microVM (prod sandbox)

Strongest isolation for production code execution (locked decision #2). Lands in Phase 5.

## Why Firecracker

- Hardware-virtualization isolation (stronger than containers)
- <125ms microVM startup
- Per-submission resource caps (CPU/mem/time/net)
- No filesystem persistence; tenant-tagged

## Fallback

nsjail if Firecracker is unavailable on a node.

Paper [OPT]: Firecracker whitepaper (AWS).
