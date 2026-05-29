// fitness/build.js
import { cpSync, mkdirSync, rmSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const root = process.cwd();
const src = join(root, 'src');
const dist = join(root, 'dist');

rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });

for (const entry of ['index.html', 'logo.png', 'style.css', 'theme.css', 'manifest.json', 'sw.js']) {
  cpSync(join(src, entry), join(dist, entry));
}

for (const dir of ['sections', 'js']) {
  cpSync(join(src, dir), join(dist, dir), { recursive: true });
}

if (existsSync(join(root, 'data'))) {
  cpSync(join(root, 'data'), join(dist, 'data'), { recursive: true });
}

console.log('Built fitness/dist');
