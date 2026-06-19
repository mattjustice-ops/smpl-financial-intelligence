import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HYDRATION_PATCH = `
<script>
/* SMPL warehouse hydration + draft/promote API wiring */
(function(){
  async function smplOrgId(){
    const q=new URLSearchParams(window.location.search);
    if(q.get('organization_id')) return q.get('organization_id');
    try{
      const s=await fetch('/api/auth/session',{credentials:'include'});
      const j=await s.json();
      return j?.user?.activeOrganizationId||null;
    }catch(_){return null;}
  }
  async function smplHydrate(){
    const orgId=await smplOrgId();
    if(!orgId) return;
    const res=await fetch('/api/v1/forecast-engine/payload?organization_id='+encodeURIComponent(orgId),{credentials:'include'});
    if(!res.ok){console.warn('Forecast hydrate failed',await res.text());return;}
    const data=await res.json();
    if(data.meta?.close_month) window.CLOSE_MONTH=data.meta.close_month;
    if(data.SRC?.actuals){
      SRC.actuals={...SRC.actuals,...data.SRC.actuals};
    }
    if(typeof refresh==='function') refresh();
  }
  const _saveVersion=window.saveVersion;
  window.saveVersion=async function(status){
    const orgId=await smplOrgId();
    if(!orgId){alert('Sign in to save forecast versions.');return;}
    const res=getResults();
    const lv=getLevers();
    const name=prompt('Name this '+(status==='final'?'FINAL':'draft')+' version:','Forecast '+new Date().toLocaleDateString());
    if(!name) return;
    const tables=typeof generateAllCSVs==='function'?null:null;
    let tablePayload={};
    try{
      if(typeof generateAllCSVs==='function'){
        const vid='V'+Date.now();
        tablePayload=generateAllCSVs(res,lv,vid);
      }
    }catch(_){}
    const body={
      version_name:name,
      levers:lv,
      req_active:reqActive,
      results:{engine:res},
      tables:Object.fromEntries(Object.entries(tablePayload||{}).map(([k,v])=>[k.replace(/^Forecast_/,'forecast_').toLowerCase(),[]]))
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
    } else {
      alert('Draft saved server-side.');
    }
    if(typeof showTab==='function') showTab('versions',null);
  };
  window.addEventListener('load',()=>{smplHydrate();});
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
    console.log(`Forecast Engine HTML already at ${dst}`);
    process.exit(0);
  }
  console.warn(`Forecast Engine source not found: ${src}`);
  process.exit(0);
}

let raw = readFileSync(src, "utf8");
if (!raw.includes("smplHydrate")) {
  raw = raw.replace("</body>", `${HYDRATION_PATCH}\n</body>`);
}
writeFileSync(dst, raw, "utf8");
console.log(`Copied ${statSync(dst).size} bytes to ${dst}`);
