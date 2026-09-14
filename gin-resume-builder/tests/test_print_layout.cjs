/* Run with playwright-core on NODE_PATH and CHROME_PATH set to a Chrome binary.
 * Optional PDF_OUT writes diagnostic PDFs; no personal resume data is used.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright-core');
const root = path.resolve(__dirname, '..');
const template = fs.readFileSync(path.join(root, 'assets/resume_template.html'), 'utf8');
(async () => {
  const browser = await chromium.launch({executablePath: process.env.CHROME_PATH, headless: true});
  const errors = [];
  try {
    for (const theme of ['', 'bank', 'editorial']) {
      for (const editing of [true, false]) {
        for (const count of [1, 35]) {
          const label = `${theme || 'minimal'}-${editing ? 'edit' : 'saved'}-${count}`;
          const page = await browser.newPage();
          try {
            const body = '<header class="header"><h1 class="name">打印回归样本</h1></header>' +
              Array.from({length:count}, (_, i) => `<section class="section"><h2 class="section-title">工作经历 ${i + 1}</h2><div class="entry"><p class="field-line">模拟内容：验证背景、阴影及长文分页。</p></div></section>`).join('');
            await page.setContent(template.replace('{{TITLE}}', label).replace('{{BODY}}', body));
            await page.evaluate(({theme,editing}) => {setTheme(theme); document.getElementById('page').contentEditable = String(editing);}, {theme,editing});
            await page.emulateMedia({media:'print'});
            const styles = await page.evaluate(() => {
              const p = getComputedStyle(document.getElementById('page'));
              const b = getComputedStyle(document.body);
              return {shadow:p.boxShadow, minHeight:p.minHeight, padding:p.padding, margin:p.margin,
                overflow:p.overflow, background:b.backgroundColor, bodyPadding:b.padding,
                toolbar:getComputedStyle(document.querySelector('.toolbar')).display};
            });
            assert.deepEqual(styles, {shadow:'none', minHeight:'0px', padding:'0px', margin:'0px',
              overflow:'visible', background:'rgb(255, 255, 255)', bodyPadding:'0px', toolbar:'none'});
            if (process.env.PDF_OUT) {
              fs.mkdirSync(process.env.PDF_OUT, {recursive:true});
              await page.pdf({path:path.join(process.env.PDF_OUT, `${label}.pdf`), preferCSSPageSize:true, printBackground:true});
            }
            console.log(`PASS ${label}`);
          } catch (error) {errors.push(`${label}: ${error.message}`);}
          finally {await page.close();}
        }
      }
    }
  } finally {await browser.close();}
  if (errors.length) {console.error(errors.join('\n'));process.exitCode=1;}
})().catch(error => {console.error(error);process.exitCode=1;});
