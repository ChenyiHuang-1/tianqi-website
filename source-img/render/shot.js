const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1600,height:1200}});
for(const sc of process.argv.slice(2)){await p.goto('file:///tmp/claude-0/r/scene.html?scene='+sc);await p.waitForTimeout(400);await p.screenshot({path:`/tmp/claude-0/r/${sc}.png`});}
await b.close();})();
