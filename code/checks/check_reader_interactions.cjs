/* Optional browser regression: install Playwright, serve the repository, then run
   node code/checks/check_reader_interactions.cjs http://127.0.0.1:8000/
   Covers the rendered behavior that source/unit checks cannot establish. */
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = new URL(process.argv[2] || 'http://127.0.0.1:8000/');

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--enable-unsafe-swiftshader'] });
  let checked = 0;
  const errors = [];
  try {
    for (const viewport of [{ width: 1280, height: 800 }, { width: 1920, height: 1440 }, { width: 390, height: 844 }, { width: 320, height: 568 }]) {
      const page = await browser.newPage({ viewport });
      page.on('pageerror', error => errors.push(error.message));
      for (const suffix of ['', '.en']) {
        for (const lesson of ['01', '13', '16']) {
          await page.goto(new URL(`course/${lesson}${suffix}.html`, base).href);
          const buttons = page.locator('.image-open');
          for (let i = 0; i < await buttons.count(); i++) {
            const button = buttons.nth(i);
            await button.evaluate(element => {
              for (let parent = element.parentElement; parent; parent = parent.parentElement) {
                if (parent.tagName === 'DETAILS') parent.open = true;
              }
            });
            await button.click();
            await page.waitForFunction(() => {
              const img = document.querySelector('#large-image');
              return !img.hidden && img.naturalWidth > 0 && img.dataset.sizeMode === 'fit';
            });
            const dimensions = await page.evaluate(() => {
              const img = document.querySelector('#large-image'), canvas = document.querySelector('.image-canvas');
              const a = img.getBoundingClientRect(), c = canvas.getBoundingClientRect();
              return { left: a.left - c.left, top: a.top - c.top, right: c.right - a.right, bottom: c.bottom - a.bottom,
                overflow: [canvas.scrollWidth - canvas.clientWidth, canvas.scrollHeight - canvas.clientHeight],
                unused: Math.min(canvas.clientWidth - 24 - a.width, canvas.clientHeight - 24 - a.height),
                width: a.width, natural: img.naturalWidth };
            });
            assert.ok(['left', 'top', 'right', 'bottom'].every(edge => dimensions[edge] >= -1), 'Entire figure must fit on opening');
            assert.ok(dimensions.overflow.every(value => value <= 1), 'Fit mode must not need scrolling');
            assert.ok(dimensions.unused <= 1, 'Fit mode must use the available window, including enlarging small SVGs');
            await page.locator('#image-zoom-in').click();
            const larger = await page.locator('#large-image').evaluate(img => img.getBoundingClientRect().width);
            assert.ok(larger > dimensions.width, 'Zoom in must enlarge the actual figure');
            await page.locator('#image-zoom-out').click();
            await page.locator('#image-size').click(); // Back to fit.
            await page.locator('#image-size').click(); // Actual size.
            assert.ok(await page.locator('#large-image').evaluate(img => Math.abs(img.clientWidth - img.naturalWidth) <= 1));
            await page.locator('#image-size').click(); // Fit again.
            const position = await page.evaluate(() => scrollY);
            await page.keyboard.press('Escape');
            await page.waitForFunction(() => !document.querySelector('#image-viewer').open);
            assert.ok(await button.evaluate(element => document.activeElement === element), 'Closing returns focus to the figure');
            assert.ok(Math.abs(await page.evaluate(() => scrollY) - position) <= 1, 'Closing must not move the reading position');
            checked++;
          }
        }
        await page.goto(new URL(`course/16${suffix}.html`, base).href);
        await page.locator('.image-open img').first().evaluate(img => { img.dataset.fullFigure = 'missing-figure-for-regression.svg'; });
        await page.locator('.image-open').first().click();
        await page.waitForFunction(() => !document.querySelector('#image-status').hidden && document.querySelector('#image-size').disabled && !document.querySelector('#image-status').textContent.includes('…'));
        assert.equal(await page.locator('#large-image').isVisible(), false, 'Failed images must not leave stale image content');
        await page.locator('#close-image').click();
        checked++;
        await page.goto(new URL(`course/01${suffix}.html`, base).href);
        await page.locator('.image-open').filter({ has: page.locator('img[src*="06-"]') }).click();
        for (const size of [{ width: 360, height: 640 }, { width: 1920, height: 1440 }, viewport]) {
          await page.setViewportSize(size);
          await page.waitForFunction(() => {
            const img = document.querySelector('#large-image'), canvas = document.querySelector('.image-canvas');
            if (img.hidden || !img.naturalWidth) return false;
            const expected = Math.min((canvas.clientWidth - 24) / img.naturalWidth, (canvas.clientHeight - 24) / img.naturalHeight);
            return img.dataset.sizeMode === 'fit' && Math.abs(img.getBoundingClientRect().width - img.naturalWidth * expected) < 1
              && canvas.scrollWidth <= canvas.clientWidth + 1 && canvas.scrollHeight <= canvas.clientHeight + 1;
          });
        }
        await page.locator('#close-image').click();
        checked++;
      }
      await page.close();
    }
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    page.on('pageerror', error => errors.push(error.message));
    for (const suffix of ['', '.en']) {
      for (const lesson of ['04', '07', '12', '13', '16', '20']) {
        await page.goto(new URL(`course/${lesson}${suffix}.html`, base).href);
        const panels = page.locator('.inline-experiment');
        for (let i = 0; i < await panels.count(); i++) {
          const panel = panels.nth(i);
          await panel.locator('summary').click();
          const frame = await (await panel.locator('iframe').elementHandle()).contentFrame();
          await frame.waitForSelector('button:visible:not(:disabled)');
          await frame.evaluate(() => { window.readerWorkspaceProbe = 'same-document'; });
          const input = frame.locator('input[type=range]').first();
          if (await input.count()) {
            await input.evaluate(element => {
              element.value = element.max;
              element.dispatchEvent(new Event('input', { bubbles: true }));
            });
          }
          const before = await frame.locator('input,select').evaluateAll(elements => elements.map(element => element.value));
          await panel.locator('.inline-expand').scrollIntoViewIfNeeded();
          const readingY = await page.evaluate(() => scrollY);
          await panel.locator('.inline-expand').click();
          assert.ok(await panel.locator('dialog').evaluate(dialog => dialog.matches(':modal')));
          const header = await panel.locator('dialog>header').boundingBox();
          await page.mouse.move(header.x + 20, header.y + 10);
          await page.mouse.wheel(0, 600);
          await page.waitForTimeout(100);
          assert.equal(await page.evaluate(() => scrollY), readingY, 'Wheel over a dialog must not move the article behind it');
          assert.equal(await frame.evaluate(() => window.readerWorkspaceProbe), 'same-document', 'Expanding must preserve the iframe document');
          assert.deepEqual(await frame.locator('input,select').evaluateAll(elements => elements.map(element => element.value)), before);
          await frame.locator('button:visible:not(:disabled)').first().focus();
          await page.keyboard.press('Escape');
          await page.waitForFunction(() => !document.querySelector('dialog:modal'));
          await page.waitForFunction(() => document.activeElement?.matches('.inline-expand'));
          assert.equal(await page.evaluate(() => scrollY), readingY, 'Returning inline restores the reading position');
          assert.equal(await frame.evaluate(() => window.readerWorkspaceProbe), 'same-document', 'Returning inline must keep the same document');
          assert.deepEqual(await frame.locator('input,select').evaluateAll(elements => elements.map(element => element.value)), before);
          const links = frame.locator('a[href]:visible');
          const returnLink = await links.evaluateAll(links => links.findIndex(link => /\/(?:course\/(?:intro|end|\d{2})(?:\.en)?\.html|(?:阅读|index)(?:\.en)?\.html)$/.test(decodeURIComponent(new URL(link.href).pathname))));
          if (returnLink >= 0) await links.nth(returnLink).click();
          else {
            await frame.locator('button:visible:not(:disabled)').first().focus();
            await page.keyboard.press('Escape');
          }
          await page.waitForFunction(element => !element.open, await panel.elementHandle());
          assert.ok(await panel.locator('summary').evaluate(element => document.activeElement === element), 'Returning from inline collapses the workspace and focuses its summary');
          checked++;
        }
      }
    }
    await page.close();
    assert.deepEqual(errors, [], 'No page exceptions');
    console.log(JSON.stringify({ passed: checked, pageErrors: errors.length }));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
