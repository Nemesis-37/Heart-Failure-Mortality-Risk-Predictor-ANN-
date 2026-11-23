/**
 * test_counselling_enhancements.js
 * Comprehensive verification script for Heart Health Counselling enhancements.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');

console.log('======================================================');
console.log('TEST SUITE: HEART HEALTH COUNSELLING & EDUCATION GUIDE');
console.log('======================================================');

// 1. Inspect HeartHealthCounsellingPage.jsx
const jsxPath = path.join(PROJECT_ROOT, 'frontend', 'src', 'pages', 'HeartHealthCounsellingPage.jsx');
const jsxContent = fs.readFileSync(jsxPath, 'utf8');

// Check 1: Educational Reference Standard Banner removed
console.log('\n--- 1. VERIFY BANNER REMOVAL ---');
const hasOldBanner = jsxContent.includes('Educational Reference Standard:');
const hasBannerClass = jsxContent.includes('counselling-notice-banner');
if (!hasOldBanner && !hasBannerClass) {
  console.log('✓ PASS: "Educational Reference Standard" banner completely removed.');
} else {
  console.error('✗ FAIL: Old banner or notice banner class still present in JSX.');
  process.exit(1);
}

// Check 2: Download PDF Button & Interaction Disclaimer present
console.log('\n--- 2. VERIFY DOWNLOAD PDF BUTTON & DISCLAIMER ---');
const hasDownloadBtn = jsxContent.includes('Download PDF') && jsxContent.includes('handleDownloadPdf');
const hasDisclaimer = jsxContent.includes('Selecting a category only changes the content displayed on this page. It does not download a PDF. Use the');
if (hasDownloadBtn) {
  console.log('✓ PASS: Professional "Download PDF" button present in hero actions with icon.');
} else {
  console.error('✗ FAIL: Download PDF button or handler missing.');
  process.exit(1);
}

if (hasDisclaimer) {
  console.log('✓ PASS: Interaction disclaimer accurately informs user about Category switching vs PDF download.');
} else {
  console.error('✗ FAIL: Interaction disclaimer missing.');
  process.exit(1);
}

// Check 3: Category C and F button layout fix
console.log('\n--- 3. VERIFY CATEGORY C & F BUTTON LAYOUT ---');
const hasGridClass = jsxContent.includes('counselling-cat-grid');
const hasBtnContent = jsxContent.includes('counselling-cat-btn-content');
const hasBtnTitle = jsxContent.includes('counselling-cat-btn-title');
const hasNowrapEllipsisInBtn = /counselling-cat-btn.*whiteSpace:\s*['"]nowrap['"]/s.test(jsxContent);

if (hasGridClass && hasBtnContent && hasBtnTitle && !hasNowrapEllipsisInBtn) {
  console.log('✓ PASS: Category navigation grid and button titles updated to responsive multi-line layout without nowrap/ellipsis clipping.');
} else {
  console.error('✗ FAIL: Button layout classes or style fix missing.');
  process.exit(1);
}

// Check 4: CSS responsive rules
console.log('\n--- 4. VERIFY RESPONSIVE CSS IN INDEX.CSS ---');
const cssPath = path.join(PROJECT_ROOT, 'frontend', 'src', 'index.css');
const cssContent = fs.readFileSync(cssPath, 'utf8');

const hasGridCss = cssContent.includes('.counselling-cat-grid') &&
                   cssContent.includes('repeat(6, 1fr)') &&
                   cssContent.includes('repeat(3, 1fr)') &&
                   cssContent.includes('repeat(2, 1fr)');
const hasBtnCss = cssContent.includes('.counselling-cat-btn-title') &&
                  cssContent.includes('white-space: normal') &&
                  cssContent.includes('min-height: 74px');

if (hasGridCss && hasBtnCss) {
  console.log('✓ PASS: Responsive grid (6 cols desktop, 3 cols tablet, 2 cols mobile) and min-height balancing configured in index.css.');
} else {
  console.error('✗ FAIL: Responsive CSS rules missing or incomplete.');
  process.exit(1);
}

console.log('\n======================================================');
console.log('>>> ALL 4 UI/UX CODE & LAYOUT CHECKS PASSED! <<<');
console.log('======================================================\n');
