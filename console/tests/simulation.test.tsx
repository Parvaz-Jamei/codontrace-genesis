import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {Scene} from '../src/simulation/scene';
import {nextIndex,project,validatePage,genomeColor,type Frame} from '../src/simulation/model';
const frame:Frame={schema:'genesis_simulation_frame_v1',run_id:'run',seed:7,generation:2,tick:2,world:{width:10,height:10},agents:[{id:'A',position:[1,2],energy:4,genome_digest:'abc'}],links:[],born_ids:['A'],deaths:[],metrics:{population:1,births:1,deaths:0,two_parent_births:0},lineage_recorded:true};
test('playback never invents frames and stops or loops at recorded boundary',()=>{assert.equal(nextIndex(2,3,false),2);assert.equal(nextIndex(2,3,true),0);assert.equal(nextIndex(0,3,false),1);assert.equal(nextIndex(0,0,false),0)});
test('valid data preserves all recorded coordinates and rejects NaN/count mismatch',()=>{const p={run_id:'run',available:true,seeds:[7],total_frames:1,frames:[structuredClone(frame)]};assert.equal(validatePage(p).frames[0].agents[0].position[1],2);p.frames[0].agents[0].position[0]=NaN;assert.throws(()=>validatePage(p));p.frames[0]=structuredClone(frame);p.frames[0].metrics.population=2;assert.throws(()=>validatePage(p))});
test('isometric layer displacement encodes time only, with stable genome colors',()=>{const a=project(1,2,10,10),b=project(1,2,10,10,40);assert.equal(b[0],a[0]);assert.equal(b[1]-a[1],40);assert.equal(genomeColor('abc'),genomeColor('abc'))});
test('SVG contains actual selectable organism, birth marker and no fake event counts',()=>{const svg=renderToStaticMarkup(<Scene frames={[frame]} mode="slice" spread={40} links cap={1000} selected={null} onSelect={()=>{}}/>);assert.match(svg,/Organism A/);assert.match(svg,/GEN 2/);assert.match(svg,/position 1,2/);assert.doesNotMatch(svg,/Recorded death/)});
test('empty recording has explicit empty state',()=>{const svg=renderToStaticMarkup(<Scene frames={[]} mode="stack" spread={40} links cap={1000} selected={null} onSelect={()=>{}}/>);assert.match(svg,/Waiting for recorded spatial frames/);assert.doesNotMatch(svg,/Organism A/)});

test('image sequence snapshot remains scoped when cache changes during asynchronous export',async()=>{
 const {captureSequence}=await import('../src/simulation/export');
 const cache=new Map([[0,structuredClone(frame)]]);
 const snapshot=captureSequence(cache,0,'campaign',7,1000);
 cache.get(0)!.agents[0].energy=99;
 cache.clear();cache.set(0,{...structuredClone(frame),seed:8,run_id:'other'});
 assert.equal(snapshot.frames[0].seed,7);assert.equal(snapshot.frames[0].agents[0].energy,4);
 assert.equal(snapshot.manifest.engine_run_id,'run');assert.deepEqual(snapshot.manifest.population_counts,[1]);
 cache.set(1,structuredClone(frame));assert.throws(()=>captureSequence(cache,0,'campaign',8,1000));
});
test('invalid lifecycle identities and fractional cells are rejected before rendering',()=>{
 const page=(f:Frame)=>({run_id:'run',available:true,seeds:[7],seed:7,total_frames:1,frames:[f]});
 const a=structuredClone(frame);a.born_ids=['A','A'];assert.throws(()=>validatePage(page(a)));
 const b=structuredClone(frame);b.deaths=[{id:'A',position:[1,2]}];assert.throws(()=>validatePage(page(b)));
 const c=structuredClone(frame);c.agents[0].position=[1.5,2];assert.throws(()=>validatePage(page(c)));
 const d=structuredClone(frame);d.metrics.two_parent_births=2;assert.throws(()=>validatePage(page(d)));
});
