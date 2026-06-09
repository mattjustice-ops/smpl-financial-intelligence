/** Patch board HTML export UI + handlers for /board static assets. */
export function patchBoardExportHandlers(html) {
  const boardReview = "/board/exports/SMPL_Board_Review_Q2_2026.pptx";
  const mdaPackage = "/board/exports/SMPL_MDA_Package_June2026.xlsx";

  let patched = html;

  patched = patched.replace(
    /<div class="export-btns">[\s\S]*?<\/div>\s*(?=<\/div>\s*\n\s*<script)/,
    "",
  );

  patched = patched.replace(
    /(<span class="period-badge"[^>]*><\/span>\s*)(<button class="ai-global-btn"[\s\S]*?<\/button>\s*)+/,
    `$1<button class="ai-global-btn" onclick="openMdaDeck()">✦ MD&A Deck ↗</button>
    <button class="ai-global-btn" onclick="openVarianceCommentary()">✦ Variance Commentary ↗</button>
`,
  );

  const exportBlock = `const BOARD_EXPORTS = {
  boardReview: '${boardReview}',
  mdaPackage: '${mdaPackage}',
};

function openBoardExport(url, label) {
  const opened = window.open(url, '_blank', 'noopener,noreferrer');
  if (!opened) window.location.assign(url);
}

function openMdaDeck() {
  openBoardExport(BOARD_EXPORTS.boardReview, 'MD&A Deck');
}

function openVarianceCommentary() {
  openBoardExport(BOARD_EXPORTS.mdaPackage, 'Variance Commentary');
}`;

  const legacyPattern =
    /function globalMDA\(\)\{window\.open\('[^']+'\);\}\s*function varComm\(\)\{window\.open\('[^']+'\);\}\s*function decBrief\(\)\{window\.open\('[^']+'\);\}/;

  const patchedExportsPattern =
    /const BOARD_EXPORTS = \{[\s\S]*?\};\s*function openBoardExport[\s\S]*?function decBrief\(\) \{[\s\S]*?\n\}/;

  if (legacyPattern.test(patched)) {
    patched = patched.replace(legacyPattern, exportBlock);
  } else if (patchedExportsPattern.test(patched)) {
    patched = patched.replace(patchedExportsPattern, exportBlock);
  } else if (patched.includes("const BOARD_EXPORTS")) {
    patched = patched
      .replace(/boardReview:\s*'[^']+'/, `boardReview: '${boardReview}'`)
      .replace(/mdaPackage:\s*'[^']+'/, `mdaPackage: '${mdaPackage}'`);
  } else {
    throw new Error("Could not locate board export handlers to patch.");
  }

  return patched;
}
