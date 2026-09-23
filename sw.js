/* 維運拍照 — 離線快取
   App 本體與模型存進手機，案場沒訊號也能開、能拍。
   NAS 上傳一律走網路，永不快取。 */
"use strict";

var VERSION = "2026-09-23b";
var SHELL = "pvshoot-shell-" + VERSION;
var RUNTIME = "pvshoot-runtime-" + VERSION;

var CORE = "./photo-checklist.html";
var EXTRA = ["./manifest-shoot.webmanifest","./icon-192.png","./icon-512.png"];

self.addEventListener("install",function(e){
  e.waitUntil(
    caches.open(SHELL).then(function(cache){
      return cache.add(CORE).then(function(){
        return Promise.all(EXTRA.map(function(u){
          return cache.add(u).catch(function(){});
        }));
      });
    }).then(function(){ return self.skipWaiting(); })
  );
});

self.addEventListener("activate",function(e){
  e.waitUntil(
    caches.keys().then(function(keys){
      return Promise.all(keys.map(function(k){
        if(k!==SHELL&&k!==RUNTIME) return caches.delete(k);
      }));
    }).then(function(){ return self.clients.claim(); })
  );
});

self.addEventListener("message",function(e){
  if(e.data&&e.data.type==="VERSION"&&e.source)
    e.source.postMessage({type:"VERSION",version:VERSION});
});

function swr(req){
  return caches.open(SHELL).then(function(cache){
    return cache.match(req).then(function(hit){
      var net=fetch(req).then(function(res){
        if(res&&res.ok) cache.put(req,res.clone());
        return res;
      }).catch(function(){ return hit; });
      return hit||net;
    });
  });
}

// 頁面本身走 network-first：有網路一定拿到最新版，逾時或離線才退回快取。
// 之前用 stale-while-revalidate 會讓使用者停在舊版一次載入，容易誤判功能沒更新。
function networkFirst(req,timeoutMs){
  return caches.open(SHELL).then(function(cache){
    return new Promise(function(resolve){
      var done=false;
      var finish=function(res){ if(!done){ done=true; resolve(res); } };
      var timer=setTimeout(function(){
        cache.match(req).then(function(hit){ if(hit) finish(hit); });
      },timeoutMs);
      fetch(req).then(function(res){
        clearTimeout(timer);
        if(res&&res.ok) cache.put(req,res.clone());
        finish(res);
      }).catch(function(){
        clearTimeout(timer);
        cache.match(req).then(function(hit){
          finish(hit||new Response("目前離線，且這個頁面還沒存進手機。",
            {status:503,headers:{"Content-Type":"text/plain; charset=utf-8"}}));
        });
      });
    });
  });
}

function cacheFirst(req){
  return caches.open(RUNTIME).then(function(cache){
    return cache.match(req).then(function(hit){
      if(hit) return hit;
      return fetch(req).then(function(res){
        if(res&&(res.ok||res.type==="opaque")) cache.put(req,res.clone());
        return res;
      });
    });
  });
}

self.addEventListener("fetch",function(e){
  var req=e.request;
  if(req.method!=="GET") return;

  var url;
  try{ url=new URL(req.url); }catch(err){ return; }
  if(url.protocol!=="http:"&&url.protocol!=="https:") return;
  // NAS 的 API 一律不碰。直連 DSM 是 /webapi/；走同源轉發程式時則是
  // proxy.php?_cgi=…，長得像一般同源網頁，漏掉會把查檔案、下載樣本的結果
  // 快取起來，下次讀到的是上一次的狀態。
  if(url.pathname.indexOf("/webapi/")>=0) return;
  if(url.searchParams.has("_cgi")||/\.php$/i.test(url.pathname)) return;

  if(url.origin===self.location.origin){
    if(req.mode==="navigate"||/\.html$/.test(url.pathname)) e.respondWith(networkFirst(req,4000));
    else e.respondWith(swr(req));
  }
  else e.respondWith(cacheFirst(req));
});
