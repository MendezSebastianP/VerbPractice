import { watch } from 'node:fs';
import { execSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = dirname(fileURLToPath(import.meta.url));
const src = resolve(dir, 'src');
let timer = null;

function build() {
  try {
    execSync('npm run build', { stdio: 'inherit', cwd: dir });
  } catch {}
}

build();

watch(src, { recursive: true }, () => {
  clearTimeout(timer);
  timer = setTimeout(build, 150);
});
