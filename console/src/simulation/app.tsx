import {useEffect,useRef,useState} from 'react';
import {Activity,ArrowLeft,ChevronLeft,ChevronRight,Download,Layers,Link2,Pause,Play,RefreshCw,Skull,Sparkles,Users,ZoomIn,ZoomOut} from 'lucide-react';
import {authorizedFetch} from '../lib/genesis/api-access';
import {zipStore} from '../lib/genesis/zip';
import type {Frame,Page} from './model';
import {nextIndex,validatePage} from './model';
import {Scene} from './scene';
import {captureSequence} from './export';
import './style.css';

function save(blob:Blob,name:string){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
export function SimulationApp({initialRunId='',embedded=false}:{initialRunId?:string;embedded?:boolean}){
 const [draft,setDraft]=useState(initialRunId),[run,setRun]=useState(initialRunId),[seed,setSeed]=useState<number|null>(null),[token,setToken]=useState('');
 const [page,setPage]=useState<Page|null>(null),[index,setIndex]=useState(0),[frame,setFrame]=useState<Frame|null>(null),[history,setHistory]=useState<Frame[]>([]);
 const [playing,setPlaying]=useState(false),[fps,setFps]=useState(2),[loop,setLoop]=useState(false),[mode,setMode]=useState<'slice'|'stack'>('stack');
 const [depth,setDepth]=useState(4),[spread,setSpread]=useState(40),[showLinks,setShowLinks]=useState(true),[cap,setCap]=useState(1000),[selected,setSelected]=useState<string|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[epoch,setEpoch]=useState(0),[follow,setFollow]=useState(false),[zoom,setZoom]=useState(1),[runs,setRuns]=useState<{id:string;title:string}[]>([]);
 const cache=useRef(new Map<number,Frame>()),request=useRef(0),sceneWrap=useRef<HTMLDivElement>(null);
 const [exporting,setExporting]=useState(false),exportLock=useRef(false);
 useEffect(()=>{if(initialRunId){setDraft(initialRunId);setRun(initialRunId);setSeed(null);setIndex(0);setPlaying(false)}},[initialRunId]);
 useEffect(()=>{
  const c=new AbortController();setRuns([]);
  authorizedFetch('/api/runs',{signal:c.signal,headers:token?{Authorization:`Bearer ${token}`}:{}})
   .then(r=>{if(!r.ok)throw Error('Run list unavailable');return r.json()})
   .then(d=>{if(!c.signal.aborted)setRuns((Array.isArray(d)?d:d.runs||[]).map((x:{id?:string;runId?:string;title?:string})=>({id:x.id||x.runId||'',title:x.title||x.id||x.runId||''})).filter((x:{id:string})=>x.id))})
   .catch(()=>{});
  return()=>c.abort();
 },[token]);
 useEffect(()=>{cache.current.clear();setFrame(null);setHistory([]);setPage(null);setSelected(null)},[run,seed]);
 useEffect(()=>{
  if(!run){setBusy(false);return}const c=new AbortController(),id=++request.current;setBusy(true);setError('');
  const cursor=Math.max(0,index-depth+1),q=new URLSearchParams({cursor:String(cursor),limit:String(Math.min(32,depth+8))});if(seed!==null)q.set('seed',String(seed));
  authorizedFetch(`/api/runs/${encodeURIComponent(run)}/simulation?${q}`,{signal:c.signal,headers:token?{Authorization:`Bearer ${token}`}:{}}).then(async r=>{const d=await r.json();if(!r.ok)throw Error(d.error||`HTTP ${r.status}`);return validatePage(d)}).then(async d=>{
   if(id!==request.current)return;if(d.run_id!==run)throw Error('Wrong run response');
   if(seed!==null&&d.seed!==undefined&&d.seed!==seed)throw Error('Wrong seed response');
   if(seed===null&&d.seed!==undefined){setSeed(d.seed);return}
   setPage(d);d.frames.forEach((f,j)=>cache.current.set(cursor+j,f));
   // Large frame pages can hit the byte budget before reaching the selected index.
   // Fetch that exact frame rather than leaving a heavy population unplayable.
   if(d.available&&!cache.current.has(index)){
    const exact=new URLSearchParams({cursor:String(index),limit:'1',seed:String(seed)});
    const response=await authorizedFetch(`/api/runs/${encodeURIComponent(run)}/simulation?${exact}`,{signal:c.signal,headers:token?{Authorization:`Bearer ${token}`}:{}});
    if(!response.ok)throw Error('Selected frame unavailable');const target=validatePage(await response.json());
    if(id!==request.current)return;if(target.run_id!==run||target.seed!==seed)throw Error('Wrong selected-frame scope');
    if(target.frames[0])cache.current.set(index,target.frames[0]);
   }
   if(cache.current.size>96)for(const key of cache.current.keys())if(Math.abs(key-index)>32)cache.current.delete(key);
   setFrame(cache.current.get(index)||null);setHistory(Array.from({length:depth},(_,j)=>cache.current.get(index-depth+1+j)).filter((f):f is Frame=>!!f));
   if(d.reason)setError(d.reason);if(d.total_frames&&index>=d.total_frames)setIndex(d.total_frames-1);
  }).catch(e=>{if(!c.signal.aborted&&id===request.current){setError(e.message);setPlaying(false);setFrame(null);setHistory([])}}).finally(()=>{if(id===request.current)setBusy(false)});
  return()=>{c.abort();request.current++};
 },[run,seed,index,depth,epoch,token]);
 useEffect(()=>{if(!playing||busy||!frame||!page)return;const timer=setTimeout(()=>{const next=nextIndex(index,page.total_frames,loop);if(next===index)setPlaying(false);else setIndex(next)},1000/fps);return()=>clearTimeout(timer)},[playing,busy,frame,page,index,fps,loop]);
 useEffect(()=>{if(!follow||!run)return;const timer=setInterval(()=>setEpoch(x=>x+1),5000);return()=>clearInterval(timer)},[follow,run]);
 useEffect(()=>{if(follow&&page?.total_frames)setIndex(page.total_frames-1)},[follow,page?.total_frames]);
 useEffect(()=>{const onKey=(e:KeyboardEvent)=>{if((e.target as HTMLElement).closest('input,select,textarea,button')||!page?.total_frames)return;if(e.code==='Space'){e.preventDefault();setPlaying(x=>!x)}if(e.key==='ArrowRight')setIndex(x=>Math.min(page.total_frames-1,x+1));if(e.key==='ArrowLeft')setIndex(x=>Math.max(0,x-1))};window.addEventListener('keydown',onKey);return()=>window.removeEventListener('keydown',onKey)},[page]);
 const load=()=>{setPlaying(false);setSeed(null);setIndex(0);setRun(draft.trim());setEpoch(x=>x+1)};
 const agent=frame?.agents.find(a=>a.id===selected),metrics=frame?.metrics;
 const sceneProps={frames:history,mode,spread,links:showLinks,cap,selected,onSelect:setSelected};
 const image=()=>{const svg=sceneWrap.current?.querySelector('svg');if(svg)save(new Blob([new XMLSerializer().serializeToString(svg)],{type:'image/svg+xml'}),`genesis-seed-${seed}-gen-${frame?.generation}.svg`)};
 const film=async()=>{
  if(exportLock.current)return;exportLock.current=true;setExporting(true);
  try{
   const snapshot=captureSequence(cache.current,index,run,seed,cap),display={...sceneProps};
   const {renderToStaticMarkup}=await import('react-dom/server');
   const files=snapshot.frames.map(f=>({name:`frame_${String(f.generation).padStart(12,'0')}.svg`,text:renderToStaticMarkup(<Scene {...display} frames={[f]} mode="slice"/>)}));
   files.push({name:'manifest.json',text:JSON.stringify(snapshot.manifest,null,2)});
   save(zipStore(files),`genesis-seed-${snapshot.manifest.seed}-frames.zip`);
  }catch(e){setError(e instanceof Error?e.message:'Image sequence export failed')}
  finally{exportLock.current=false;setExporting(false)}
 };
 return <div className={`sim-app ${embedded?'sim-embedded':''}`} dir="ltr">
 <header className="sim-top"><div className="sim-brand"><span className="sim-mark"><Layers size={22}/></span><div><span className="sim-eyebrow">GENESIS / EVOLUTION OBSERVATORY</span><h1>Simulation <span>Atlas</span></h1></div></div><div className="sim-top-actions">{!embedded?<a href="/"><ArrowLeft size={16}/> Console</a>:null}<span className="sim-badge"><span/> Recorded data</span></div></header>
 <section className="sim-source" aria-label="Data source"><label>Experiment / run<input value={draft} onChange={e=>setDraft(e.target.value)} list="sim-run-list" placeholder="run_…" onKeyDown={e=>{if(e.key==='Enter')load()}}/><datalist id="sim-run-list">{runs.map(r=><option key={r.id} value={r.id}>{r.title}</option>)}</datalist></label><label>API token · session only<input type="password" value={token} onChange={e=>setToken(e.target.value)} autoComplete="off" placeholder={embedded?'Uses console token if left empty':'Optional on localhost'}/></label><button onClick={load} className="sim-primary"><Activity size={16}/> Open run</button><button onClick={()=>setEpoch(x=>x+1)} disabled={!run} aria-label="Refresh frames"><RefreshCw size={16}/></button></section>
 <div className="sim-workspace"><main className="sim-main">
 <div className="sim-toolbar"><label>Seed<select value={seed??''} onChange={e=>{setPlaying(false);setIndex(0);setSeed(Number(e.target.value))}} disabled={!page?.seeds.length}>{!page?.seeds.length?<option>No recorded seeds</option>:page.seeds.map(s=><option key={s} value={s}>{s}</option>)}</select></label><div className="sim-segment"><button aria-pressed={mode==='stack'} onClick={()=>setMode('stack')}><Layers size={15}/> Layers</button><button aria-pressed={mode==='slice'} onClick={()=>setMode('slice')}>Single slice</button></div><span className="sim-spacer"/><button onClick={()=>setZoom(x=>Math.max(.5,x-.1))} aria-label="Zoom out"><ZoomOut size={17}/></button><button onClick={()=>setZoom(x=>Math.min(2,x+.1))} aria-label="Zoom in"><ZoomIn size={17}/></button><button onClick={image} disabled={!frame} aria-label="Export current SVG"><Download size={16}/></button></div>
 <div className="sim-viewport" ref={sceneWrap}><div className="sim-scene-wrap" style={{transform:`scale(${zoom})`}}><Scene {...sceneProps}/></div><div className="sim-hud"><span className="sim-eyebrow">GENERATION</span><strong>{frame?.generation??'—'}</strong><span>SEED {seed??'—'} / TICK {frame?.tick??'—'}</span></div><div className="sim-status">{busy?'Loading recorded frame…':frame?`${Math.min(cap,frame.agents.length)} / ${frame.agents.length} glyphs shown`:'No spatial recording loaded'}</div></div>
 <div className="sim-playback"><div className="sim-play-row"><button disabled={!frame||busy} onClick={()=>setIndex(x=>Math.max(0,x-1))} aria-label="Previous frame"><ChevronLeft size={20}/></button><button className="sim-play" disabled={!frame} onClick={()=>{setFollow(false);setPlaying(x=>!x)}} aria-label={playing?'Pause replay':'Play replay'}>{playing?<Pause size={20}/>:<Play size={20}/>}</button><button disabled={!page?.total_frames||busy} onClick={()=>setIndex(x=>Math.min((page?.total_frames||1)-1,x+1))} aria-label="Next frame"><ChevronRight size={20}/></button><span className="sim-time">{page?.total_frames?`${index+1} / ${page.total_frames} recorded frames`:'No frames'}</span><span className="sim-spacer"/><label>Speed<select value={fps} onChange={e=>setFps(Number(e.target.value))}>{[.5,1,2,4,8].map(n=><option key={n} value={n}>{n} fps</option>)}</select></label><label className="sim-check"><input type="checkbox" checked={loop} onChange={e=>setLoop(e.target.checked)}/> Loop</label></div><input className="sim-scrubber" aria-label="Recorded frame" type="range" min="0" max={Math.max(0,(page?.total_frames||1)-1)} value={index} disabled={!frame} onChange={e=>{setPlaying(false);setFollow(false);setIndex(Number(e.target.value))}}/><div className="sim-timeline-label"><span>GEN {page?.generations?.[0]??'—'}</span><span>Space: play/pause · ← →: frame · no interpolated generations</span><span>GEN {page?.generations?.at(-1)??'—'}</span></div></div>
 <div className="sim-alert" role="status">{error||'Time layers encode recorded generations. Parentage lines and death marks come from explicit records.'}</div>
 </main><aside className="sim-inspector"><div className="sim-panel-title"><Activity size={17}/><h2>Population telemetry</h2></div><div className="sim-metrics">{[[Users,'Population',metrics?.population],[Sparkles,'Births',metrics?.births],[Skull,'Deaths',metrics?.deaths],[Link2,'Two-parent births',metrics?.two_parent_births]].map(([Icon,label,value])=>{const I=Icon as typeof Users;return <div className="sim-metric" key={String(label)}><I size={17}/><span>{String(label)}</span><strong>{typeof value==='number'?value:'—'}</strong></div>})}</div><small>Counts cover the recorded interval. Two-parent births are not all mating attempts. “—” means unrecorded.</small>
 <div className="sim-panel-title"><Layers size={17}/><h2>Display layers</h2></div><label>History depth <b>{depth}</b><input type="range" min="1" max="8" value={depth} onChange={e=>setDepth(Number(e.target.value))}/></label><label>Layer separation <b>{spread}</b><input type="range" min="15" max="80" value={spread} onChange={e=>setSpread(Number(e.target.value))}/></label><label>Visible organism budget<select value={cap} onChange={e=>setCap(Number(e.target.value))}>{[200,500,1000,2000].map(n=><option key={n}>{n}</option>)}</select></label><label className="sim-check"><input type="checkbox" checked={showLinks} onChange={e=>setShowLinks(e.target.checked)}/> Show parentage / two-parent links</label><label className="sim-check"><input type="checkbox" checked={follow} onChange={e=>{setPlaying(false);setFollow(e.target.checked)}}/> Follow newest recorded frame</label>
 <div className="sim-panel-title"><Users size={17}/><h2>Organism inspector</h2></div>{agent?<dl><dt>ID</dt><dd>{agent.id}</dd><dt>Cell</dt><dd>{agent.position.join(', ')}</dd><dt>Runtime ATP</dt><dd>{agent.energy??'Not recorded'}</dd><dt>Genome digest</dt><dd>{agent.genome_digest}</dd></dl>:<p className="sim-muted">Select an organism on the layer to inspect its actual recorded state.</p>}
 <div className="sim-legend"><span><i className="sim-life"/> Living organism</span><span><i className="sim-born"/> Recorded birth</span><span><i className="sim-dead"/> Recorded death · last position</span><span><i className="sim-parent"/> Parentage</span><span><i className="sim-pair"/> Two-parent birth linkage</span></div><small>Colors distinguish genome digests; they do not imply host/parasite classes. Overlapping cell positions are preserved.</small><button className="sim-film" onClick={film} disabled={!frame||exporting} aria-busy={exporting}><Download size={16}/> {exporting?'Exporting recorded frames…':'Export cached image sequence'}</button><small>SVG + manifest ZIP. Up to 16 loaded frames around the selection; no invented generations.</small>
 </aside></div></div>
}
