#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, '..', 'src', 'nodes');
const destDir = path.join(__dirname, '..', 'dist', 'nodes');

function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function copyHtmlFiles() {
  ensureDir(destDir);
  const entries = fs.readdirSync(srcDir, { withFileTypes: true });
  entries
    .filter((entry) => entry.isFile() && entry.name.endsWith('.html'))
    .forEach((entry) => {
      const source = path.join(srcDir, entry.name);
      const target = path.join(destDir, entry.name);
      fs.copyFileSync(source, target);
    });
}

copyHtmlFiles();
