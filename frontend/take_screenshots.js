import puppeteer from 'puppeteer';
import path from 'path';
import fs from 'fs';

const ARTIFACTS_DIR = 'C:\\Users\\1234r\\.gemini\\antigravity\\brain\\0c49bca2-9802-44cc-9fce-a73ada9bbee9\\artifacts';

const pages = [
  { name: 'dashboard', url: 'http://localhost:5173/' },
  { name: 'search', url: 'http://localhost:5173/search' },
  { name: 'students', url: 'http://localhost:5173/students' },
  { name: 'graph', url: 'http://localhost:5173/graph' },
  { name: 'upload', url: 'http://localhost:5173/upload' }
];

async function captureScreenshots() {
  if (!fs.existsSync(ARTIFACTS_DIR)) {
    fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
  }

  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  await page.setViewport({ width: 1366, height: 768 });

  for (const p of pages) {
    console.log(`Capturing ${p.name}...`);
    try {
      await page.goto(p.url, { waitUntil: 'networkidle2' });
      // Wait an extra 2 seconds for any animations/data fetching to complete
      await new Promise(r => setTimeout(r, 2000));
      await page.screenshot({ path: path.join(ARTIFACTS_DIR, `${p.name}.png`), fullPage: true });
    } catch (e) {
      console.error(`Failed to capture ${p.name}:`, e);
    }
  }

  await browser.close();
  console.log('Done!');
}

captureScreenshots();
