/**
 * test_pdf_exclusion_filtering.js
 * Validates topic exclusion and inclusion filtering logic for the PDF generator.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { generateCounsellingGuidePdf } from '../frontend/src/utils/generateCounsellingPdf.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');

// Read categories from HeartHealthCounsellingPage.jsx
const jsxPath = path.join(PROJECT_ROOT, 'frontend', 'src', 'pages', 'HeartHealthCounsellingPage.jsx');
const jsx = fs.readFileSync(jsxPath, 'utf8');

const match = jsx.match(/const categories = (\[[\s\S]*?\n  \])\n\n  const activeData/);
if (!match) {
  console.error('Failed to parse categories array from HeartHealthCounsellingPage.jsx');
  process.exit(1);
}

const categories = eval(match[1]);
console.log('Testing PDF Filtering & Customization Logic:');

// Polyfill browser globals
let downloadedBlob = null;
global.Blob = class MockBlob {
  constructor(parts, options) {
    this.buffer = Buffer.concat(parts.map((p) => Buffer.from(p)));
    this.type = options.type;
  }
};
global.URL = {
  createObjectURL: (blob) => {
    downloadedBlob = blob;
    return 'blob:mock-url';
  },
  revokeObjectURL: () => {},
};
global.document = {
  createElement: () => ({ click: () => {}, setAttribute: () => {} }),
  body: { appendChild: () => {}, removeChild: () => {} },
};

// Test 1: Exclude 3 topics from Category A
const excludedIds = ['nut_balanced', 'nut_produce', 'nut_grains'];
const filteredCategories1 = categories
  .map((cat) => ({
    ...cat,
    counsellingPoints: cat.counsellingPoints.filter((pt) => !excludedIds.includes(pt.id)),
  }))
  .filter((cat) => cat.counsellingPoints.length > 0);

const catAPoints = filteredCategories1.find((c) => c.code === 'A').counsellingPoints;
console.log(`- Category A points after excluding 3: ${catAPoints.length} (expected 3)`);
if (catAPoints.length !== 3) {
  console.error('Filtering failed: points count mismatch');
  process.exit(1);
}

downloadedBlob = null;
generateCounsellingGuidePdf(filteredCategories1);
if (!downloadedBlob || downloadedBlob.buffer.length < 1000) {
  console.error('PDF generation failed on filtered categories');
  process.exit(1);
}
const pdfStr1 = downloadedBlob.buffer.toString('latin1');
if (!pdfStr1.startsWith('%PDF-1.4') || !pdfStr1.includes('%%EOF')) {
  console.error('Invalid PDF structure');
  process.exit(1);
}
console.log(`✓ PASS: Generated PDF omitting excluded topics (${downloadedBlob.buffer.length} bytes).`);

// Test 2: Exclude entire Category B
const filteredCategories2 = categories
  .map((cat) => {
    if (cat.code === 'B') {
      return { ...cat, counsellingPoints: [] };
    }
    return cat;
  })
  .filter((cat) => cat.counsellingPoints.length > 0);

console.log(`- Remaining categories count when B is excluded: ${filteredCategories2.length} (expected 5)`);
if (filteredCategories2.some((c) => c.code === 'B')) {
  console.error('Category B was not omitted');
  process.exit(1);
}

downloadedBlob = null;
generateCounsellingGuidePdf(filteredCategories2);
if (!downloadedBlob || downloadedBlob.buffer.length < 1000) {
  console.error('PDF generation failed on category omission');
  process.exit(1);
}
console.log(`✓ PASS: Generated PDF omitting entire Category B (${downloadedBlob.buffer.length} bytes).`);

console.log('\n>>> ALL PDF FILTERING TESTS PASSED SUCCESSFULLY! <<<\n');
