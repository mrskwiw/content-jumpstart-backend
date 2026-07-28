// Clean a Termly HTML export into a semantic fragment our own stylesheet can own.
// Strips: <style> blocks (Termly !important rules), inline style="" attrs, <bdt>
// wrappers, and empty class/data-custom-class hooks. Keeps h1-h4/p/ul/ol/li/a/strong/table.
import fs from 'node:fs';

const SRC = process.argv[2];
const OUT = process.argv[3];

let html = fs.readFileSync(SRC, 'utf8');

// 1. Drop Termly's leading <style> blocks (their !important rules fight our theme).
html = html.replace(/<style[\s\S]*?<\/style>/gi, '');
// 2. Strip all inline style attributes (Arial/colors/mso-* Word cruft).
html = html.replace(/\sstyle=("[^"]*"|'[^']*')/gi, '');
// 3. Unwrap Termly's <bdt> dynamic-value wrappers — keep their text content.
html = html.replace(/<\/?bdt[^>]*>/gi, '');
// 4. Remove now-purposeless styling hooks so nothing leaks Termly styling.
html = html.replace(/\sdata-custom-class=("[^"]*"|'[^']*')/gi, '');
html = html.replace(/\sclass=("[^"]*"|'[^']*')/gi, '');
// 5. Collapse empty inline wrappers left behind (<span></span>, <span> </span>).
let prev;
do {
  prev = html;
  html = html.replace(/<span>\s*<\/span>/gi, '');
} while (html !== prev);
// 6. Tidy whitespace.
html = html.replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();

fs.writeFileSync(OUT, html);
const bytes = Buffer.byteLength(html, 'utf8');
console.log(`${SRC} -> ${OUT}  (${(bytes / 1024).toFixed(1)} KB)`);
