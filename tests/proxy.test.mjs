import assert from "node:assert/strict";
import { test } from "node:test";
import { proxyDemo } from "../web/lib/proxy.ts";

const app = "https://steadyday-test.invalid";
const settings = { origin: app, baseURL: process.env.TEST_API_URL, key: process.env.TEST_PROXY_KEY };
const request = (route, method="GET", body, cookie="", origin=app) => new Request(app+"/api/demo/"+route,{
  method,
  headers: { Origin:origin, ...(cookie ? { Cookie:cookie } : {}), ...(body===undefined?{}:{"Content-Type":"application/json"}) },
  ...(body===undefined?{}:{body:JSON.stringify(body)})
});
const NEVER = async () => { throw new Error("Unexpected forwarding"); };

test("rejects unknown routes, unauthorised reads, cross-origin writes, and oversized payloads",async()=>{
  assert.equal((await proxyDemo(request("../etc"),"../etc",settings,NEVER)).status,404);
  assert.equal((await proxyDemo(request("dashboard"),"dashboard",settings,NEVER)).status,401);
  assert.equal((await proxyDemo(request("session","POST",{persona:"arif",consent:true},"","https://other.invalid"),"session",settings,NEVER)).status,403);
  assert.equal((await proxyDemo(request("session","POST",{x:"x".repeat(2100)}),"session",settings,NEVER)).status,413);
});
test("handles an unavailable upstream with a typed 503",async()=>{
  const r=await proxyDemo(request("config"),"config",settings,async()=>{throw new Error("Unreachable");});
  assert.equal(r.status,503);
  assert.equal((await r.json()).error.code,"BACKEND_UNAVAILABLE");
});
test("runs the typed same-origin proxy against real FastAPI, persists edits and keeps the token private",async()=>{
  assert.ok(settings.baseURL && settings.key);
  const create=await proxyDemo(request("session","POST",{persona:"samir",consent:true}),"session",settings);
  assert.equal(create.status,201);
  assert.deepEqual(await create.json(),{created:true});
  const raw=create.headers.get("set-cookie");
  assert.match(raw,/HttpOnly/);
  assert.match(raw,/SameSite=Strict/);
  assert.match(raw,/; Secure/);
  const cookie=raw.split(";")[0];
  const read=await proxyDemo(request("dashboard","GET",undefined,cookie),"dashboard",settings);
  assert.equal((await read.json()).suggestion.id,"restart");
  const write=await proxyDemo(request("check-in","PUT",{sleep_minutes:400,activity_minutes:31,energy:3},cookie),"check-in",settings);
  assert.equal((await write.json()).today_entry.activity_minutes,31);
  const insights = await proxyDemo(request("insights?days=30", "GET", undefined, cookie), "insights", settings);
  assert.equal(insights.status, 200);
  const trend = await insights.json();
  assert.equal(trend.days, 30);
  assert.equal(trend.entries.at(-1).activity_minutes, 31);
  const createdGoal = await proxyDemo(request("goal", "POST", { title: "Take a practice break" }, cookie), "goal", settings);
  assert.equal(createdGoal.status, 201);
  const goal = (await createdGoal.json()).goals.find((item) => item.title === "Take a practice break");
  assert.ok(goal);
  const deletedGoal = await proxyDemo(request("goal?id=" + goal.id, "DELETE", undefined, cookie), "goal", settings);
  assert.equal(deletedGoal.status, 200);
  assert.equal((await deletedGoal.json()).goals.some((item) => item.id === goal.id), false);
  const repeat=await proxyDemo(request("session","POST",{persona:"arif",consent:true},cookie),"session",settings);
  assert.equal(repeat.status,409);
  const exported=await proxyDemo(request("export","GET",undefined,cookie),"export",settings);
  assert.match(exported.headers.get("content-disposition"),/attachment/);
  assert.equal((await exported.json()).entries.at(-1).activity_minutes,31);
  const del=await proxyDemo(request("session","DELETE",undefined,cookie),"session",settings);
  assert.match(del.headers.get("set-cookie"),/Max-Age=0/);
  assert.equal((await proxyDemo(request("dashboard","GET",undefined,cookie),"dashboard",settings)).status,401);
});
