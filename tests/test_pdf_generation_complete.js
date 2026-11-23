/**
 * test_pdf_generation_complete.js
 * Validates the PDF generator against the actual categories in HeartHealthCounsellingPage.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');

// Read categories from HeartHealthCounsellingPage.jsx
const jsxPath = path.join(PROJECT_ROOT, 'frontend', 'src', 'pages', 'HeartHealthCounsellingPage.jsx');
const jsx = fs.readFileSync(jsxPath, 'utf8');

// Extract categories array
const match = jsx.match(/const categories = (\[[\s\S]*?\n  \])\n\n  const activeData/);
if (!match) {
  console.error('Failed to match categories array in JSX');
  process.exit(1);
}

// Evaluate categories array safely
const categories = eval(match[1]);
console.log(`Loaded ${categories.length} categories from HeartHealthCounsellingPage.jsx:`);
let totalPoints = 0;
categories.forEach(c => {
  console.log(` - Category ${c.code}: ${c.title} (${c.counsellingPoints.length} points)`);
  totalPoints += c.counsellingPoints.length;
});
console.log(`Total clinical counselling points across all categories: ${totalPoints}`);

// Import PDF generator
import { generateCounsellingGuidePdf } from '../frontend/src/utils/generateCounsellingPdf.js';

// Polyfill browser globals for testing in Node
let downloadedBlob = null;
global.Blob = class MockBlob {
  constructor(parts, options) {
    this.buffer = Buffer.concat(parts.map(p => Buffer.from(p)));
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

generateCounsellingGuidePdf(categories);

if (!downloadedBlob) {
  console.error('Blob generation failed');
  process.exit(1);
}

const outPath = path.join(__dirname, 'generated_counselling_guide.pdf');
fs.writeFileSync(outPath, downloadedBlob.buffer);
console.log(`✓ PDF successfully generated and saved to: ${outPath} (${downloadedBlob.buffer.length} bytes)`);
