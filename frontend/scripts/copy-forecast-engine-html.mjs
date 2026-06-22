import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";

import { dirname, join } from "node:path";

import { fileURLToPath } from "node:url";



const HYDRATION_PATCH = `

<script src="/shared/smpl-outlook.js"></script>

<script>

/* SMPL warehouse hydration + draft/promote API wiring */

(function(){

  async function smplOrgId(){

    return window.SMPLOutlook.resolveOrgId({ waitForParent: true });

  }

  async function smplHydrate(){

    await window.SMPLOutlook.hydrate({

      endpoint: 'reporting/outlook',

      hooks: { SRC: SRC },

      onApplied: function () {

        if (typeof refresh === 'function') refresh();

      },

    });

  }

  window.saveVersion=async function(status){

    const orgId=await smplOrgId();

    if(!orgId){alert('Sign in to save forecast versions.');return;}

    const res=getResults();

    const lv=getLevers();

    const name=prompt('Name this '+(status==='final'?'FINAL':'draft')+' version:','Forecast '+new Date().toLocaleDateString());

    if(!name) return;

    const vid='V'+Date.now();

    const asOf=window.SMPL_CLOSE_MONTH||CLOSE_MONTH;

    const tables=typeof buildForecastTableRows==='function'?buildForecastTableRows(res,lv,vid,orgId,asOf):{};

    const body={

      version_name:name,

      as_of_period:asOf,

      levers:lv,

      req_active:reqActive,

      results:{engine:res},

      tables:tables

    };

    const draftRes=await fetch('/api/v1/forecast/versions/draft?organization_id='+encodeURIComponent(orgId),{

      method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)

    });

    if(!draftRes.ok){alert('Draft save failed: '+await draftRes.text());return;}

    const draft=await draftRes.json();

    if(status==='final'){

      const promoteRes=await fetch('/api/v1/forecast/versions/'+draft.id+'/promote?organization_id='+encodeURIComponent(orgId),{

        method:'POST',credentials:'include'

      });

      if(!promoteRes.ok){alert('Promote failed: '+await promoteRes.text());return;}

      alert('Promoted to FINAL and loaded into warehouse.');

      await smplHydrate();

    } else {

      alert('Draft saved server-side.');

    }

    if(typeof showTab==='function') showTab('versions',null);

  };

  window.SMPL_ON_ORG_READY=function(){void smplHydrate();};

  window.addEventListener('load',()=>{void smplHydrate();});

})();

</script>

`;

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const src =
  process.env.SMPL_FORECAST_ENGINE_HTML_SRC?.trim() ??
  "C:\\Users\\mattj\\Downloads\\SMPL_Forecast_Engine_June2026 (16).html";
const dst = join(root, "public", "forecast-engine", "index.html");

mkdirSync(dirname(dst), { recursive: true });

if (!existsSync(src)) {
  if (existsSync(dst)) {
    console.log(`Forecast engine HTML already at ${dst} (${statSync(dst).size} bytes)`);
    process.exit(0);
  }
  console.warn(`Forecast engine HTML source not found: ${src}`);
  process.exit(0);
}

let html = readFileSync(src, "utf8");
if (!html.includes("function leversAtDefault(")) {
  html = html.replace(
    "function getResults(){return compute();}",
    `function leversAtDefault(){
  const nb=+(document.getElementById('l-nb')?.value||100);
  const exp=+(document.getElementById('l-exp')?.value||100);
  const churn=+(document.getElementById('l-churn')?.value||100);
  const ren=+(document.getElementById('l-ren')?.value||0);
  const cogs=+(document.getElementById('l-cogs')?.value||29);
  const sm=+(document.getElementById('l-sm')?.value||34);
  const rd=+(document.getElementById('l-rd')?.value||16);
  const ga=+(document.getElementById('l-ga')?.value||11);
  const dso=+(document.getElementById('l-dso')?.value||45);
  const dpo=+(document.getElementById('l-dpo')?.value||30);
  const capex=+(document.getElementById('l-capex')?.value||220);
  return nb===100&&exp===100&&churn===100&&ren===0&&cogs===29&&sm===34&&rd===16&&ga===11&&dso===45&&dpo===30&&capex===220;
}

function getResults(){
  var baseline=window.SMPL_BASELINE_ENGINE;
  if(baseline&&Object.keys(baseline).length&&leversAtDefault()) return baseline;
  return compute();
}`
  );
}
if (!html.includes("function buildForecastTableRows(")) {
  html = html.replace(
    /return csvs;\s*\}\s*\nfunction toCSV/,
    "return csvs;\n}\n\nfunction buildForecastTableRows(res, lv, vid, orgId, asOf){\n  /* injected by copy-forecast-engine-html.mjs — see public/forecast-engine/index.html */\n  return {};\n}\n\nfunction toCSV"
  );
}
if (html.includes("SMPL warehouse hydration")) {
  html = html.replace(/<script src="\/shared\/smpl-outlook.js"><\/script>\s*<script>\s*\/\* SMPL warehouse hydration[\s\S]*?<\/script>\s*(?=<\/body>)/, HYDRATION_PATCH.trim());
  html = html.replace(/<script>\s*\/\* SMPL warehouse hydration[\s\S]*?<\/script>\s*(?=<\/body>)/, HYDRATION_PATCH.trim());
} else {
  html = html.replace("</body>", `${HYDRATION_PATCH}\n</body>`);
}
writeFileSync(dst, html, "utf8");
console.log(`Copied and patched ${statSync(dst).size} bytes to ${dst}`);

