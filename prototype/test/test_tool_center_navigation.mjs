import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';

const appSource=readFileSync(new URL('../app.js',import.meta.url),'utf8');
const portalSource=readFileSync(new URL('../frontend/public-portal.js',import.meta.url),'utf8');

test('门户导航保留能力服务名称及原路由和别名',()=>{
  const navigation=JSON.parse(appSource.match(/const portalNav = (\[[^;]+\]);/)[1]);
  assert.deepEqual(navigation.filter(([route])=>route==='capabilities'),[['capabilities','能力服务']]);
  assert.equal(navigation.some(([,label])=>label==='工具中心'),false);
  assert.match(appSource,/tools:"capabilities"/);
  assert.match(appSource,/工具中心提供坐标转换/);
});

test('首页快捷入口与推荐区保留原有名称',()=>{
  assert.ok(portalSource.includes("['capabilities','常用工具','在线分析与量算','tool']"));
  assert.match(portalSource,/section\('常用能力','[^']*','capabilities'\)/);
  assert.equal(portalSource.includes("['capabilities','工具中心'"),false);
});

test('工具目录内部使用工具中心标题且不改变申请入口',async context=>{
  const previous=Object.getOwnPropertyDescriptor(globalThis,'location');
  const previousDocument=Object.getOwnPropertyDescriptor(globalThis,'document');
  Object.defineProperty(globalThis,'location',{configurable:true,value:{hash:'#/front/capabilities'}});
  Object.defineProperty(globalThis,'document',{configurable:true,value:{addEventListener:()=>{}}});
  context.after(()=>{
    if(previous)Object.defineProperty(globalThis,'location',previous);
    else delete globalThis.location;
    if(previousDocument)Object.defineProperty(globalThis,'document',previousDocument);
    else delete globalThis.document;
  });
  const {createToolCenter}=await import('../frontend/tool-center.js');
  const tools=createToolCenter({
    esc:String,
    btn:label=>`<button>${label}</button>`,
    state:()=>({D:{resources:[],portalManagement:{tools:[]}}}),
    cart:()=>[],
  });
  const html=tools.catalog();
  assert.match(html,/<h1>工具中心<\/h1>/);
  assert.equal(html.includes('<h1>能力服务</h1>'),false);
  assert.match(html,/href="#\/front\/applications"/);
  assert.match(html,/href="#\/front\/capabilities"/);
});
