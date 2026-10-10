import test from "node:test";
import assert from "node:assert/strict";
import {useBench,mapServerStatus,seedSlots} from "../src/lib/genesis/store";
import {pauseJob,restartJob,removeJob,startJob,stopJob} from "../src/lib/genesis/clock";
import {runActionAvailable} from "../src/lib/genesis/run-actions";
import type {Job} from "../src/lib/genesis/types";
const job=(id:string,status:Job['status']="running"):Job=>({id,title:id,kind:"engine",preset:"custom",seeds:[id==="A"?42:43],generations:100,previewGenerations:2,workers:1,cores:[0],status,cursor:0,totalSteps:100,logs:[],createdAt:0,note:"REFERENCE",serverManaged:true,isDemo:false,capabilities:{pause:true,resume:true,checkpoint_continue:false}});
const snap=(id:string,rev:number,done:number,state="RUNNING")=>({schema_version:"run_snapshot_v2",run_id:id,session_id:id,revision:rev,state,capabilities:{pause:true,resume:true,checkpoint_continue:false},workers_expected:1,workers_paused:0,progress:{kind:"generation",stage:"simulation",done,total:100,pct:done},active_elapsed_seconds:0,paused_seconds:0,wall_elapsed_seconds:0,heartbeat_at:"2026-10-10"});
function mockRuns(ids:string[], extra?: (url:string,body:any)=>Response|Promise<Response>|undefined){
  globalThis.fetch=(async(input:any,init:any)=>{
    const url=String(input),body=init?.body?JSON.parse(init.body):{};
    const special=await extra?.(url,body);if(special)return special;
    if(url==="/api/runs")return Response.json(ids.map((id,index)=>({id,title:id,status:"RUNNING",pct:index?75:25,completedSeeds:0,totalSeeds:1,recentLogs:[id],snapshot:snap(id,2,index?75:25)})));
    const id=url.split('/').at(-1)!;
    if(ids.includes(id))return Response.json({id,title:id,status:"RUNNING",manifest:{params:{seeds:[id==="A"?42:43],generations:100,workers:1,scriptName:"genesis_long_board_campaign.py",experiment:id==="A"?"T01":"T02",track:"REFERENCE"}},liveLogs:[id],consoleLogs:[],snapshot:snap(id,2,id==="A"?25:75),execution:{summary:{scientific_assessment:"UNASSESSED",summary_metrics:{unique:id}}},telemetry:[{seed:id==="A"?42:43,generation:9,primary_metric_value:id==="A"?1:99}],executionBoundary:{engineBackend:"reference",isFrontierReference:true,modelScope:id,modelBoundaryNotice:id}});
    return Response.json({error:url},{status:404});
  }) as typeof fetch;
}
const originalFetch=globalThis.fetch;
test.afterEach(()=>{globalThis.fetch=originalFetch;useBench.setState({jobs:[],threads:[],selectedJobId:null});});
test("each card receives only its own metric/details despite selection",async()=>{
  useBench.setState({jobs:[job("A"),job("B")],threads:[],selectedJobId:"A"});mockRuns(["A","B"]);await useBench.getState().syncServerRuns();
  const [a,b]=useBench.getState().jobs;
  assert.equal((a.execution!.summary as any).summary_metrics.unique,"A");assert.equal((b.execution!.summary as any).summary_metrics.unique,"B");assert.equal(b.telemetry![0].primary_metric_value,99);
  assert.equal(a.cursor,25);assert.equal(b.cursor,75);assert.equal(a.totalSteps,100);assert.equal(b.totalSteps,100);assert.equal(b.launchParams!.experiment,"T02");
});
test("pause request is ID-bound and remains running until actual acknowledgement; double click sends once",async()=>{
  useBench.setState({jobs:[job("A"),job("B")],threads:[],selectedJobId:"B"});let release!:()=>void;const pending=new Promise<void>(r=>release=r);const calls:any[]=[];
  mockRuns(["A","B"],async(url,body)=>{if(url==="/api/runs/action"){calls.push(body);await pending;return Response.json({ok:true});}});
  const action=pauseJob("A");assert.equal(useBench.getState().jobs[0].status,"running");assert.equal(useBench.getState().jobs[0].pendingAction,"pause");await pauseJob("A");assert.equal(calls.length,1);assert.deepEqual({runId:calls[0].runId,action:calls[0].action},{runId:"A",action:"pause"});assert.equal(typeof calls[0].requestId,"string");assert.equal(useBench.getState().jobs[1].pendingAction,undefined);release();await action;await new Promise(r=>setTimeout(r,30));
});
test("native restart creates new selected card, preserves original card and errors surface on correct card",async()=>{
  useBench.setState({jobs:[job("A","archived"),job("B","archived")],threads:[],selectedJobId:"B"});let payload:any;
  mockRuns(["A","B","C"],(url,body)=>{if(url==="/api/runs/action"){payload=body;return Response.json({ok:true,runId:"C"});}});await restartJob("A");assert.deepEqual({runId:payload.runId,action:payload.action},{runId:"A",action:"restart"});assert.equal(typeof payload.requestId,"string");assert.equal(useBench.getState().selectedJobId,"C");assert.ok(useBench.getState().jobs.some(j=>j.id==="A"));
  useBench.getState().patchJob("B",{status:"archived"});mockRuns(["A","B","C"],(url)=>url==="/api/runs/action"?Response.json({ok:false,error:"Cannot delete evidence"},{status:409}):undefined);await removeJob("B");assert.match(useBench.getState().jobs.find(j=>j.id==="B")!.actionError!,/Cannot delete evidence/);assert.equal(useBench.getState().jobs.find(j=>j.id==="A")!.actionError,null);
});
test("capabilities and transitions stay honest; real seed rows never invent demo arms",()=>{
  const a=job("A");a.capabilities={pause:false,resume:false,checkpoint_continue:false};assert.equal(runActionAvailable(a,"pause"),false);assert.equal(runActionAvailable(a,"restart"),false);assert.equal(runActionAvailable(a,"delete"),false);
  assert.equal(mapServerStatus("PAUSING"),"running");assert.equal(mapServerStatus("RESUMING"),"paused");assert.equal(mapServerStatus("STARTING"),"queued");
  assert.equal(seedSlots(a)[0].state,"unknown");assert.equal(seedSlots(a)[0].arm,"—");a.telemetry=[{seed:42,generation:21,arm:"NO_QD"}];assert.equal(seedSlots(a)[0].done,21);assert.equal(seedSlots(a)[0].arm,"NO_QD");
});

test("resume and stop requests target their card and preserve acknowledged execution state",async()=>{
  useBench.setState({jobs:[job("A","paused"),job("B")],threads:[]});const calls:any[]=[];
  mockRuns(["A","B"],(url,body)=>{if(url==="/api/runs/action"){calls.push(body);return Response.json({ok:true});}});
  await startJob("A");await new Promise(r=>setTimeout(r,30));await stopJob("B");await new Promise(r=>setTimeout(r,30));
  assert.deepEqual(calls.map(({runId,action})=>({runId,action})),[{runId:"A",action:"resume"},{runId:"B",action:"stop"}]);assert.equal(useBench.getState().jobs.find(j=>j.id==="B")!.status,"running");assert.equal(useBench.getState().jobs.find(j=>j.id==="B")!.pendingAction,"stop");
});
test("equal-title cards reject stale revisions and wrongly addressed details independently",async()=>{
  const a=job("A"),b=job("B");a.title=b.title="Same title";a.snapshot=snap("A",10,80) as any;b.snapshot=snap("B",11,90) as any;a.execution={summary:{unique:"fresh-A"}};b.execution={summary:{unique:"fresh-B"}};
  useBench.setState({jobs:[a,b],threads:[],selectedJobId:"B"});mockRuns(["A","B"]);await useBench.getState().syncServerRuns();
  assert.equal((useBench.getState().jobs[0].execution!.summary as any).unique,"fresh-A");assert.equal((useBench.getState().jobs[1].execution!.summary as any).unique,"fresh-B");
  assert.equal(useBench.getState().jobs[0].cursor,0);assert.equal(useBench.getState().jobs[1].title,"Same title");
});
test("zero counts stay zero and missing capability blocks command before network",async()=>{
  const a=job("A");a.capabilities={pause:false,resume:false,checkpoint_continue:false};useBench.setState({jobs:[a],threads:[]});let calls=0;
  mockRuns(["A"],(url)=>{if(url==="/api/runs/action"){calls++;return Response.json({ok:true});}if(url==="/api/runs")return Response.json([{id:"A",title:"A",status:"RUNNING",pct:0,totalSeeds:0,completedSeeds:0,snapshot:{...snap("A",3,0),progress:{kind:"generation",stage:"starting",done:0,total:0,pct:null},capabilities:{pause:false,resume:false,checkpoint_continue:false}}}]);if(url==="/api/runs/A")return Response.json({id:"not-A",status:"RUNNING"});});
  await pauseJob("A");assert.equal(calls,0);await useBench.getState().syncServerRuns();assert.equal(useBench.getState().jobs[0].totalSteps,0);assert.equal(useBench.getState().jobs[0].cursor,0);
});

test("successful empty inventory prunes deleted real cards but network failure preserves them", async()=>{
  const real=job("A"), demo={...job("preview"),isDemo:true,serverManaged:false};
  useBench.setState({jobs:[real,demo],threads:[],selectedJobId:"A"});
  globalThis.fetch=async()=>Response.json({error:"temporary"},{status:503});
  await useBench.getState().syncServerRuns();assert.equal(useBench.getState().jobs.length,2);
  globalThis.fetch=async()=>Response.json([]);
  await useBench.getState().syncServerRuns();assert.deepEqual(useBench.getState().jobs.map(j=>j.id),["preview"]);assert.equal(useBench.getState().selectedJobId,null);
});

test("a sync requested during an older poll waits and refreshes the new card inventory",async()=>{
  useBench.setState({jobs:[job("A")],threads:[],selectedJobId:"A"});
  let release!:()=>void;const gate=new Promise<void>(resolve=>release=resolve);let inventory=0;
  globalThis.fetch=(async(input:any)=>{const url=String(input);if(url==="/api/runs"){inventory++;if(inventory===1){await gate;return Response.json([{id:"A",status:"RUNNING",title:"A"}]);}return Response.json([{id:"A",status:"RUNNING",title:"A"},{id:"B",status:"RUNNING",title:"B"}]);}const id=url.split('/').at(-1);return Response.json({id,status:"RUNNING",manifest:{params:{seeds:[1]}}});}) as typeof fetch;
  const first=useBench.getState().syncServerRuns();const second=useBench.getState().syncServerRuns();release();await Promise.all([first,second]);
  assert.equal(inventory,2);assert.ok(useBench.getState().jobs.some(j=>j.id==="B"));
});

test("play on a stopped real run starts a fresh replay instead of pretending to resume",async()=>{
  useBench.setState({jobs:[job("A","stopped")],threads:[],selectedJobId:"A"});let action:string|undefined;
  mockRuns(["A","B"],(url,body)=>{if(url==="/api/runs/action"){action=body.action;return Response.json({ok:true,runId:"B"});}});
  await startJob("A");assert.equal(action,"restart");assert.equal(useBench.getState().selectedJobId,"B");assert.ok(useBench.getState().jobs.some(j=>j.id==="A"));
});
