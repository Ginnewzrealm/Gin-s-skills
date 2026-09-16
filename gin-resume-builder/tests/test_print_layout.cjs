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
      const label = `${theme || 'minimal'}-contact-and-style`;
      const page = await browser.newPage();
      try {
        const body = '<header class="header"><h1 class="name">版式检查</h1>' +
          '<div class="contact-row"><span class="contact-item">13800000000</span><span class="contact-item">liming@example.com</span><span class="contact-item">杭州</span><span class="contact-item">高级销售经理</span><span class="contact-item">32岁</span><span class="contact-item">浙江大学｜本科</span></div></header>' +
          '<section class="section" data-section="work"><h2 class="section-title">工作经历<span class="en">WORK EXPERIENCE</span></h2><div class="entry"><p class="field-line"><span class="field-label">核心职责</span><span class="field-content">负责重点客户拓展。</span></p></div></section>';
        await page.setContent(template.replace('{{TITLE}}', label).replace('{{BODY}}', body));
        await page.evaluate(theme => {setTheme(theme);}, theme);
        const items = await page.locator('.contact-item').evaluateAll(nodes => nodes.map(n => n.textContent.trim()));
        assert.deepEqual(items, ['13800000000', 'liming@example.com', '杭州', '高级销售经理', '32岁', '浙江大学｜本科']);
        if (theme === 'editorial') {
          const styles = await page.evaluate(() => {
            const labelStyle = getComputedStyle(document.querySelector('.field-label'));
            const titleBefore = getComputedStyle(document.querySelector('.section-title'), '::before');
            return {
              labelColor: labelStyle.color,
              labelBg: labelStyle.backgroundColor,
              beforeDisplay: titleBefore.display,
              beforeContent: titleBefore.content,
            };
          });
          assert.notEqual(styles.labelColor, 'rgb(255, 255, 255)');
          assert.notEqual(styles.labelBg, 'rgb(49, 93, 120)');
          assert.equal(styles.beforeDisplay, 'none');
          assert.equal(styles.beforeContent, 'none');
        }
        console.log(`PASS ${label}`);
      } catch (error) {errors.push(`${label}: ${error.message}`);}
      finally {await page.close();}
    }
    for (const theme of ['', 'bank', 'editorial']) {
      for (const editing of [true, false]) {
        for (const count of [1, 35]) {
          const label = `${theme || 'minimal'}-${editing ? 'edit' : 'saved'}-${count}`;
          const page = await browser.newPage();
          try {
            const body = '<header class="header"><h1 class="name">打印回归样本</h1></header>' +
              Array.from({length:count}, (_, i) => `<section class="section" data-section="work"><h2 class="section-title">工作经历 ${i + 1}</h2><div class="entry"><p class="field-line">模拟内容：验证背景、阴影及长文分页。</p></div></section>`).join('');
            const printableBody = body + '<section class="section" data-section="skills"><h2 class="section-title">专业技能</h2><div class="skills-grid"><div class="skill-row"><div class="skill-label">长内容</div><div class="skill-content">用于验证专业能力可以自然跨页。</div></div></div></section>';
            await page.setContent(template.replace('{{TITLE}}', label).replace('{{BODY}}', printableBody));
            await page.evaluate(({theme,editing}) => {setTheme(theme); document.getElementById('page').contentEditable = String(editing);}, {theme,editing});
            await page.emulateMedia({media:'print'});
            const styles = await page.evaluate(() => {
              const p = getComputedStyle(document.getElementById('page'));
              const b = getComputedStyle(document.body);
              const skills = getComputedStyle(document.querySelector('.skills-grid'));
              return {shadow:p.boxShadow, minHeight:p.minHeight, paddingTop:p.paddingTop,
                paddingRight:p.paddingRight, margin:p.margin, maxWidth:p.maxWidth,
                boxSizing:p.boxSizing, overflow:p.overflow, overflowWrap:p.overflowWrap,
                skillsBreakInside:skills.breakInside, background:b.backgroundColor, bodyPadding:b.padding,
                toolbar:getComputedStyle(document.querySelector('.toolbar')).display};
            });
            assert.equal(styles.shadow, 'none');
            assert.equal(styles.minHeight, '0px');
            assert.ok(parseFloat(styles.paddingTop) >= 18, styles.paddingTop);
            assert.ok(parseFloat(styles.paddingRight) >= 22, styles.paddingRight);
            assert.equal(styles.margin, '0px');
            assert.equal(styles.maxWidth, '100%');
            assert.equal(styles.boxSizing, 'border-box');
            assert.equal(styles.overflow, 'visible');
            assert.equal(styles.overflowWrap, 'anywhere');
            assert.equal(styles.skillsBreakInside, 'auto');
            assert.equal(styles.background, 'rgb(255, 255, 255)');
            assert.equal(styles.bodyPadding, '0px');
            assert.equal(styles.toolbar, 'none');
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
