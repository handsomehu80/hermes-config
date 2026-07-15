// Playwright browser evidence capture — generalized template.
// Captures 3 deterministic screenshots of a web PoC by mutating its state
// directly (no keypress timing fight). Customize the GLOBAL_OBJECT, the
// state fields, and the 3 snapshot descriptions for your PoC.
//
// Usage: node browser-play.js <worktree-root> <output-dir>
//   worktree-root: path to the org repo worktree containing the PoC
//   output-dir:    where to write screenshot-0{1,2,3}-*.png + browser-play.json
//
// Customization points (search for "TODO" in this file):
//   1. POC_SUBDIR      — the subdir under <worktree> that contains index.html
//   2. GLOBAL_OBJECT   — the window.* object that exposes PoC state (e.g. window.__SNAKE__)
//   3. SNAPSHOT_FIELDS — the state fields you want to log for each snapshot
//   4. The 3 evaluate() blocks — the state setup for initial / mid-play / gameover

const path = require('path');
const fs = require('fs');
const http = require('http');

// TODO: set this to the subdir under <worktree> that contains index.html
const POC_SUBDIR = 'poc-snake';
// TODO: set this to the window.* global the PoC exposes (e.g. window.__SNAKE__)
const GLOBAL_OBJECT = 'window.__SNAKE__';
// TODO: list the state fields you want to log per snapshot (used for audit trail)
const SNAPSHOT_FIELDS = ['phase', 'score', 'snake.length', 'snake[0]', 'food'];

const { chromium } = require('C:/Users/Administrator/AppData/Roaming/npm/node_modules/playwright');

const WT = process.argv[2] || path.resolve(__dirname, '../../workspaces/issue-N/pr-M');
const OUT = process.argv[3] || path.resolve(__dirname);
const POC = path.join(WT, POC_SUBDIR);

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

function startServer(root, port) {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split('?')[0]);
      if (p === '/') p = '/index.html';
      const full = path.join(root, p);
      if (!full.startsWith(root)) { res.statusCode = 403; res.end('forbidden'); return; }
      fs.readFile(full, (err, data) => {
        if (err) { res.statusCode = 404; res.end('not found: ' + p); return; }
        const ext = path.extname(p).toLowerCase();
        res.setHeader('Content-Type', MIME[ext] || 'application/octet-stream');
        res.setHeader('Cache-Control', 'no-store');
        res.end(data);
      });
    });
    srv.listen(port, '127.0.0.1', () => resolve(srv));
  });
}

(async () => {
  const PORT = 8765;
  const server = await startServer(POC, PORT);
  const URL = `http://127.0.0.1:${PORT}/index.html`;
  console.log(`[srv] ${URL} (root=${POC})`);

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const ctx = await browser.newContext({ viewport: { width: 720, height: 720 } });
  const page = await ctx.newPage();
  page.on('console', (msg) => console.log(`[page.${msg.type()}]`, msg.text()));
  page.on('pageerror', (err) => console.log('[page.error]', err.message));

  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  // Wait for the PoC's global to be ready
  const READY_EXPR = `!!(${GLOBAL_OBJECT} && ${GLOBAL_OBJECT}.state)`;
  await page.waitForFunction(READY_EXPR, null, { timeout: 5000 });

  // ---- Snapshot 1: initial state ----
  // TODO: customize the state setup for your PoC's "initial" condition
  await page.evaluate((g) => {
    const G = eval(g);
    G.reset();
    G.state.phase = 'paused';
  }, GLOBAL_OBJECT);
  await page.waitForTimeout(80);
  const s1 = path.join(OUT, 'screenshot-01-initial.png');
  await page.screenshot({ path: s1, fullPage: true });
  const st1 = await page.evaluate((g) => {
    const s = eval(g).state;
    return { phase: s.phase, score: s.score, length: s.snake.length, head: s.snake[0], food: s.food };
  }, GLOBAL_OBJECT);
  console.log('[snap1] initial', JSON.stringify(st1));

  // ---- Snapshot 2: mid-play state ----
  // TODO: customize — build the state that represents "user has played for a while"
  await page.evaluate((g) => {
    const G = eval(g);
    // Example: length-6 snake facing right, ready to take 2 ticks
    G.state.snake = [
      { x: 5, y: 10 }, { x: 4, y: 10 }, { x: 3, y: 10 },
      { x: 2, y: 10 }, { x: 1, y: 10 }, { x: 0, y: 10 },
    ];
    G.state.score = 5;
    G.state.food = { x: 7, y: 10 };
    G.state.phase = 'playing';
    G.state.interval_ms = 60;
    G.state.dir = { x: 1, y: 0 };
    G.state.pending_dir = { x: 1, y: 0 };
  }, GLOBAL_OBJECT);
  await page.waitForTimeout(160);  // let 2 ticks fire
  const s2 = path.join(OUT, 'screenshot-02-mid-play.png');
  await page.screenshot({ path: s2, fullPage: true });
  const st2 = await page.evaluate((g) => {
    const s = eval(g).state;
    return { phase: s.phase, score: s.score, length: s.snake.length, head: s.snake[0] };
  }, GLOBAL_OBJECT);
  console.log('[snap2] mid-play', JSON.stringify(st2));

  // ---- Snapshot 3: terminal state (game over / completion) ----
  // TODO: customize — set up the state that triggers the PoC's terminal condition
  await page.evaluate((g) => {
    const G = eval(g);
    G.state.phase = 'paused';
    G.state.snake = [
      { x: 2, y: 10 }, { x: 3, y: 10 }, { x: 4, y: 10 },
      { x: 5, y: 10 }, { x: 6, y: 10 }, { x: 7, y: 10 },
    ];
    G.state.score = 5;
    G.state.food = { x: 0, y: 0 };
    G.state.dir = { x: -1, y: 0 };
    G.state.pending_dir = { x: -1, y: 0 };
    G.state.phase = 'playing';
  }, GLOBAL_OBJECT);
  for (let i = 0; i < 12; i++) {
    await page.waitForTimeout(50);
    const p = await page.evaluate((g) => eval(g).state.phase, GLOBAL_OBJECT);
    if (p === 'gameover') break;
  }
  const s3 = path.join(OUT, 'screenshot-03-gameover.png');
  await page.screenshot({ path: s3, fullPage: true });
  const st3 = await page.evaluate((g) => {
    const s = eval(g).state;
    return { phase: s.phase, score: s.score, length: s.snake.length, head: s.snake[0] };
  }, GLOBAL_OBJECT);
  console.log('[snap3] gameover', JSON.stringify(st3));

  await browser.close();
  server.close();

  const summary = {
    captured_at: new Date().toISOString(),
    url: URL,
    worktree: WT,
    poc_root: POC,
    screenshots: [
      { name: 'initial', file: s1, state: st1 },
      { name: 'mid-play', file: s2, state: st2 },
      { name: 'gameover', file: s3, state: st3 },
    ],
    // TODO: describe what each snapshot is supposed to show
    verification_notes: [
      'initial: <describe>',
      'mid-play: <describe>',
      'gameover: <describe>',
    ],
  };
  fs.writeFileSync(path.join(OUT, 'browser-play.json'), JSON.stringify(summary, null, 2));
  console.log('[done]', path.join(OUT, 'browser-play.json'));
})().catch((err) => {
  console.error('[fatal]', err);
  process.exit(1);
});
