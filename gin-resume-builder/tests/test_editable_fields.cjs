/* NODE_PATH: playwright-core installation; CHROME_PATH: Chrome binary. */
const {chromium} = require('playwright-core');
const {execFileSync} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const scriptDir = path.resolve(__dirname, '../scripts');
const fixtures = JSON.parse(execFileSync(process.env.PYTHON || 'python3', ['-B', '-c', `
import sys,json
sys.path.insert(0,sys.argv[1])
from html_renderer import render
samples=[{'basic':{'姓名':'测试','教育背景':'测试大学 本科'}},
 {'basic':{'姓名':'测试'},'education':[{'school':'测试大学','degree':'本科','major':'计算机','period':'2018-2022'}]}]
for s in samples:
    s['basic'].update({'电话':'13900000000','邮箱':'test@example.com','城市':'上海','求职意向':'经理','年龄':'32岁'})
    s['sections']=[{'title':'岗位匹配','items':[{'tag':'协同能力','text':'基于已确认的协作经历。'}]}]
print(json.dumps([render(s,editable=True) for s in samples]))
`, scriptDir], {encoding:'utf8'}));
(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
  try {
    for (let i=0;i<fixtures.length;i++) {
      const page=await browser.newPage();
      await page.setContent(fixtures[i]);
      const field=page.locator(i===0?'.contact-item:nth-child(5)':'.entry-company');
      assert(await field.isEditable());
      await field.fill('修改后的大学 硕士');
      if(i===1){
        assert(await page.locator('.entry-position').isEditable());
        assert(await page.locator('.entry-meta').isEditable());
        await page.locator('.entry-meta').fill('2022-2025');
      }
      const downloadPromise=page.waitForEvent('download');
      await page.getByRole('button',{name:'保存修改',exact:true}).click();
      const download=await downloadPromise;
      const html=fs.readFileSync(await download.path(),'utf8');
      await page.setContent(html);
      assert.equal(await field.innerText(),'修改后的大学 硕士');
      assert.equal(await field.isEditable(),false);
      await page.getByRole('button',{name:'预览/编辑',exact:true}).click();
      assert(await field.isEditable());
      if(i===1)assert.equal(await page.locator('.entry-meta').innerText(),'2022-2025');
      await page.close();
      console.log(`PASS education edit/download/reopen ${i}`);
    }
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
