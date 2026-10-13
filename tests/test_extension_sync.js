const assert=require("node:assert/strict");
const {performScan,testConnection,TELEMETRY_PROTOCOL_VERSION}=require("../chrome_extension/background.js");

function fakeApi(initial={},tabs=[]){
  const state={...initial},alarms=[];
  return {state,scheduled:alarms,storage:{local:{async get(keys){const out={};for(const key of keys)if(key in state)out[key]=state[key];return out;},async set(values){Object.assign(state,values);}}},
    tabs:{async query(){return tabs;},async sendMessage(_id,message){if(message.type==="IGA_READ_IO_AUTOMATION_AUDIT")return {route:"app",farm_state:"unknown",controls:{surrender:{selector:"#eco-desistir",present:true,enabled:true,policy:"permanently_blocked"}}};return {source:"dom",reader_version:"trainer-xp-scoped-v1",available:true,stats:{level:10,xp_current:100,xp_max:200},diagnostic:{canvas:0,iframes:0,candidates:4,xp_candidates:1,xp_ambiguous:false,xp_trainer_scoped:true,xp_reason:"trainer_xp_scoped"}};}},
    alarms:{create(name,detail){alarms.push({name,detail});}}};
}
const ioTab={id:7,windowId:3,url:"https://pokeidle.io/app",title:"Pokeidle",active:false};
const worldTab={id:8,windowId:3,url:"https://poke.idleworld.online/play",title:"World",active:true};

(async()=>{
  let api=fakeApi({profile_id:"12345678-1234-1234-1234-123456789012"},[ioTab]);
  let calls=0;
  let result=await performScan({api,fetchFn:async()=>{calls++;},now:()=>1000});
  assert.equal(result.code,"pairing_missing");assert.equal(calls,0);assert.equal(api.state.connection_code,"pairing_missing");

  api=fakeApi({profile_id:"12345678-1234-1234-1234-123456789012",pairing_token:"x".repeat(32)},[ioTab,worldTab]);
  let sent;
  result=await performScan({api,fetchFn:async(_url,options)=>{sent=JSON.parse(options.body);return{ok:true,status:200,json:async()=>({ok:true,tab_count:2})};},now:()=>2000});
  assert.equal(result.code,"sync_confirmed");assert.equal(api.state.connection_code,"sync_confirmed");assert.equal(sent.tabs.length,2);assert.equal(sent.tabs[0].observation.telemetry_protocol,TELEMETRY_PROTOCOL_VERSION);assert.equal(sent.tabs[0].observation.xp_trainer_scoped,true);
  assert.equal(sent.tabs[0].io_audit.controls.surrender.policy,"permanently_blocked");
  assert.equal(api.state.last_audit_status,"audit_received");
  assert.equal(api.state.last_audit_received,1);
  const normalReader=api.tabs.sendMessage;
  api.tabs.sendMessage=async (id,message)=>message.type==="IGA_READ_IO_AUTOMATION_AUDIT"
    ? undefined : normalReader(id,message);
  result=await performScan({api,fetchFn:async(_url,options)=>{
    sent=JSON.parse(options.body);
    return {ok:true,status:200,json:async()=>({ok:true,tab_count:2})};
  },now:()=>2500});
  assert.equal(result.code,"sync_confirmed");
  assert.equal(sent.tabs[0].observation.content_state,"responded");
  assert.equal(sent.tabs[0].io_audit,undefined);
  assert.equal(api.state.last_audit_status,"reader_ok_audit_missing");
  assert.equal(api.state.last_audit_missing,1);


  api=fakeApi({profile_id:"12345678-1234-1234-1234-123456789012",pairing_token:"x".repeat(32)},[ioTab]);
  result=await performScan({api,fetchFn:async()=>({ok:false,status:401,json:async()=>null}),now:()=>3000});
  assert.equal(result.code,"pairing_rejected");assert.equal(api.state.retry_count,0);assert.equal(api.scheduled.length,0);

  api=fakeApi({profile_id:"12345678-1234-1234-1234-123456789012",pairing_token:"x".repeat(32)},[ioTab]);
  result=await performScan({api,fetchFn:async()=>({ok:false,status:500,json:async()=>null}),now:()=>3500});
  assert.equal(result.code,"sync_failed");assert.equal(api.state.last_http_status,500);assert.equal(api.scheduled.length,1);

  api=fakeApi({profile_id:"12345678-1234-1234-1234-123456789012",pairing_token:"x".repeat(32)},[ioTab]);
  result=await performScan({api,fetchFn:async()=>({ok:true,status:200,json:async()=>({ok:true})}),now:()=>3750});
  assert.equal(result.code,"sync_failed");assert.equal(api.state.last_error,"Resposta local inválida.");

  api=fakeApi({profile_id:"12345678-1234-1234-1234-123456789012",pairing_token:"x".repeat(32)},[ioTab]);
  result=await performScan({api,fetchFn:async()=>{throw new Error("Failed to fetch");},now:()=>4000});
  assert.equal(result.code,"server_unreachable");assert.equal(api.scheduled[0].name,"tab-sync-retry");

  api=fakeApi({profile_id:"12345678-1234-1234-1234-123456789012",pairing_token:"x".repeat(32)},[]);
  result=await performScan({api,fetchFn:async()=>({ok:true,status:200,json:async()=>({ok:true,tab_count:0})}),now:()=>4500});
  assert.equal(result.code,"no_matching_tabs");assert.equal(api.state.last_server_tab_count,0);

  api=fakeApi();
  result=await testConnection({api,fetchFn:async()=>({ok:true,json:async()=>({app:"idle-game-agent",mode:"unified"})})});
  assert.deepEqual(result,{ok:true,code:"server_reachable"});
  console.log("Extensão: sincronização, emparelhamento e recuperação aprovados.");
})().catch(error=>{console.error(error);process.exitCode=1;});
