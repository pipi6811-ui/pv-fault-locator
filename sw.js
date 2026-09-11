/* 維運拍照 — 離線快取
   App 本體與模型存進手機，案場沒訊號也能開、能拍。
   NAS 上傳一律走網路，永不快取。 */
"use strict";

var VERSION = "2026-09-11a";
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
  if(url.pathname.indexOf("/webapi/")>=0) return;

  if(url.origin===self.location.origin) e.respondWith(swr(req));
  else e.respondWith(cacheFirst(req));
});
