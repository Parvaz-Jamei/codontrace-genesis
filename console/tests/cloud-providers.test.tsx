import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {CloudModelOptions, type CloudProvider} from "../src/components/bench/cloud-providers";

test("cloud model choices use provider-qualified live IDs and exclude non-chat candidates",()=>{
  const providers:CloudProvider[]=[{id:"openai",title:"OpenAI / GPT",configured:true,enabled:true,credential_source:"server_file",models:[{id:"openai::gpt-new",name:"gpt-new",provider:"openai",chat_candidate:true},{id:"openai::gpt-image-new",name:"gpt-image-new",provider:"openai",chat_candidate:false}]},{id:"deepseek",title:"DeepSeek",configured:true,enabled:true,credential_source:"server_file",models:[{id:"deepseek::future-model",name:"future-model",provider:"deepseek",chat_candidate:true}]}];
  const html=renderToStaticMarkup(<select><CloudModelOptions providers={providers}/></select>);
  assert.match(html,/openai::gpt-new/);assert.match(html,/deepseek::future-model/);assert.doesNotMatch(html,/gpt-image-new/);
});
test("unconfigured providers provide a settings action hint rather than pretend model availability",()=>{
  const html=renderToStaticMarkup(<select><CloudModelOptions providers={[{id:"openai",title:"OpenAI",configured:false,enabled:true,credential_source:"server_file",models:[]}]}/></select>);
  assert.match(html,/Configure API in Settings/);assert.match(html,/disabled/);
});
