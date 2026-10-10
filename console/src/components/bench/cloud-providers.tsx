import { setApiAccessToken } from "../../lib/genesis/api-access";
import React, { useEffect, useRef, useState } from "react";
import { useBench } from "@/lib/genesis/store";
export type CloudModel = { id: string; name: string; provider: string; chat_candidate: boolean };
export type CloudProvider = { id: string; title: string; configured: boolean; enabled: boolean; credential_source: string; models: CloudModel[]; error?: string | null; updated_at?: number | null };
export function useCloudProviders() {
  const [providers,setProviders]=useState<CloudProvider[]>([]), [error,setError]=useState("");
  useEffect(()=>{
    let alive=true;
    const refresh=async()=>{
      try {
        const response=await fetch("/api/providers",{cache:"no-store"});const body=await response.json();
        if(!response.ok || !body.ok || !Array.isArray(body.providers)) throw Error(body.error??"Provider registry unavailable");
        if(alive){setProviders(body.providers);setError("");}
      } catch(e){if(alive)setError(String(e));}
    };
    void refresh();window.addEventListener("cloud-providers-changed",refresh);
    return ()=>{alive=false;window.removeEventListener("cloud-providers-changed",refresh);};
  },[]);
  return {providers,error};
}
export function CloudModelOptions({ providers }: { providers: CloudProvider[] }) {
  return <>{providers.map(p=><optgroup key={p.id} label={`${p.title} · API`}>
    {p.models.filter(m=>m.chat_candidate).map(m=><option key={m.id} value={m.id} disabled={!p.configured}>{m.name}{p.error?" · catalog error":""}</option>)}
    {!p.models.some(m=>m.chat_candidate) && <option disabled>{p.configured?"Refresh models in Settings":"Configure API in Settings"}</option>}
  </optgroup>)}</>;
}
export function CloudProviderSettings() {
  const lang=useBench(s=>s.settings.lang), model=useBench(s=>s.settings.model), setSettings=useBench(s=>s.setSettings);
  const {providers,error:registryError}=useCloudProviders();
  const [keys,setKeys]=useState<Record<string,string>>({}), [token,setToken]=useState(""), [usageToken,setUsageToken]=useState("");
  const [pending,setPending]=useState<string|null>(null),[errors,setErrors]=useState<Record<string,string>>({});
  const actionLock=useRef(false);
  const act=async(provider:string,action:string)=>{
    if(actionLock.current) return;actionLock.current=true;setPending(provider);setErrors(e=>({...e,[provider]:""}));
    const key=keys[provider];setKeys(k=>({...k,[provider]:""}));
    try {
      const response=await fetch("/api/providers",{method:"POST",headers:{"Content-Type":"application/json",...(token?{Authorization:`Bearer ${token}`}:{})},body:JSON.stringify({provider,action,...(action==="save"&&key?{api_key:key}:{})})});
      const body=await response.json();if(!response.ok||!body.ok)throw Error(body.error??`HTTP ${response.status}`);
      const own=body.providers?.find((p:CloudProvider)=>p.id===provider);
      if(own?.error)setErrors(e=>({...e,[provider]:own.error}));
      if(action==="disconnect"&&model?.startsWith(provider+"::"))setSettings({model:"local-analyst"});
      window.dispatchEvent(new Event("cloud-providers-changed"));
    }catch(e){setErrors(v=>({...v,[provider]:String(e)}));}finally{actionLock.current=false;setPending(null);}
  };
  return <div className="space-y-4">
    <p className="text-sm text-muted">{lang==="fa"?"مدل‌های حساب از API رسمی دریافت می‌شوند. کلید فقط روی سرور ذخیره می‌شود. با انتخاب مدل ابری، پیام و زمینهٔ اجرای انتخابی برای همان ارائه‌دهنده ارسال می‌شود؛ هزینهٔ API متعلق به حساب شماست.":"Models are discovered from the official account API. Keys stay on the server. Choosing a cloud model sends the message and selected-run context to that provider; API usage is billed to your account."}</p>
    {registryError&&<p role="alert" className="text-sm text-red-300">{registryError}</p>}
    {providers.map(p=><section key={p.id} className="rounded-xl border border-white/10 p-3">
      <h4 className="font-medium">{p.title}</h4>
      <p className="my-2 text-xs text-muted">{p.configured?(lang==="fa"?"کلید تنظیم شده":"Key configured"):(lang==="fa"?"متصل نیست":"Not connected")} · {p.credential_source} · {p.models.length} {lang==="fa"?"مدل دریافت‌شده":"discovered models"}</p>
      <label className="block text-xs text-muted">{lang==="fa"?"توکن دسترسی چت، ابزارها و کنترل اجراها (CODONTRACE_API_TOKEN؛ فقط حافظهٔ این صفحه)":"Chat, tools and run-control access token (CODONTRACE_API_TOKEN; page memory only)"}<input type="password" autoComplete="off" value={usageToken} onChange={e=>{setUsageToken(e.target.value);setApiAccessToken(e.target.value);}} className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3"/></label>
    <label className="block text-sm">API key<input type="password" autoComplete="off" spellCheck={false} value={keys[p.id]??""} onChange={e=>setKeys(k=>({...k,[p.id]:e.target.value}))} placeholder={p.configured?"Leave blank to keep server key":"API key"} className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3"/></label>
      {p.credential_source==="environment"&&p.configured&&<p className="mt-1 text-xs text-muted">{lang==="fa"?"کلید محیط سرور اولویت دارد؛ جایگزینی آن باید در محیط سرور انجام شود.":"Server environment key takes priority; replace it in the server environment."}</p>}
      <div className="mt-2 flex flex-wrap gap-2">
        <button disabled={pending!==null} onClick={()=>void act(p.id,"save")} className="min-h-11 rounded-lg bg-teal-500/20 px-3 disabled:opacity-40">{pending===p.id?"…":lang==="fa"?"ذخیره و دریافت مدل‌ها":"Save & discover"}</button>
        <button disabled={pending!==null||!p.configured} onClick={()=>void act(p.id,"refresh")} className="min-h-11 rounded-lg bg-white/10 px-3 disabled:opacity-40">{lang==="fa"?"تازه‌سازی مدل‌ها":"Refresh models"}</button>
        <button disabled={pending!==null||!p.enabled} onClick={()=>void act(p.id,"disconnect")} className="min-h-11 rounded-lg bg-white/10 px-3 disabled:opacity-40">{lang==="fa"?"قطع اتصال و حذف کلید ذخیره‌شده":"Disconnect & remove stored key"}</button>
      </div>
      {(errors[p.id]||p.error)&&<p role="alert" className="mt-2 text-sm text-red-300">{errors[p.id]||p.error}</p>}
      {p.updated_at&&<p className="mt-2 text-xs text-muted">{new Date(p.updated_at*1000).toLocaleString()}</p>}
    </section>)}
    <label className="block text-xs text-muted">{lang==="fa"?"توکن تنظیمات برای اتصال از راه دور (اختیاری؛ CODONTRACE_SETTINGS_TOKEN)":"Remote settings token (optional; CODONTRACE_SETTINGS_TOKEN)"}<input type="password" autoComplete="off" value={token} onChange={e=>setToken(e.target.value)} className="mt-1 min-h-11 w-full rounded-lg bg-white/5 px-3"/></label>
    <label className="block text-sm">{lang==="fa"?"مدل انتخابی":"Selected model"}<select value={model} onChange={e=>setSettings({model:e.target.value})} className="mt-1 min-h-11 w-full rounded-lg bg-[#181a20] px-3"><option value="local-analyst">Local analyst</option><option value="board-model">Local board model</option>{model&&!model.includes("::")&&!["local-analyst","board-model"].includes(model)&&<option value={model}>{model}</option>}<CloudModelOptions providers={providers}/>{model?.includes("::")&&!providers.some(p=>p.models.some(m=>m.id===model))&&<option value={model}>{model} · refresh catalog</option>}</select></label>
    <p className="text-xs text-muted">{lang==="fa"?"فهرست API تضمین سازگاری ابزار یا Chat Completions نیست؛ مدل‌های تخصصی تصویر/صدا در انتخاب چت نمایش داده نمی‌شوند. مدل محلی و ابزار دستی همچنان قابل استفاده‌اند.":"API listing is not a Chat Completions/tool compatibility guarantee. Image/audio-specific models are excluded from chat choices. Local models and manual tools remain available."}</p>
  </div>;
}
