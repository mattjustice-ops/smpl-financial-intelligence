/**
 * After CDP stores window.__aio_b64, write it to tmp/last.b64 in parts via argv,
 * OR decode+post from tmp/last.b64.
 *
 * Preferred flow when CDP returnByValue can hold full b64:
 *   1) CDP builds window.__aio_b64
 *   2) Agent writes tmp/last.b64 from CDP result
 *   3) node scripts/aio-from-b64.mjs < tmp/last.b64
 *
 * For oversized payloads:
 *   node scripts/aio-b64-part.mjs --reset N
 *   node scripts/aio-b64-part.mjs i PART
 *   node scripts/aio-b64-part.mjs --finish
 */
console.log("see aio-from-b64.mjs / aio-b64-part.mjs");
