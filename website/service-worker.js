/* ============================================================
   石湖诗社 · Service Worker
   策略：核心页面预缓存 + 同源资源 Stale-While-Revalidate +
         外部字体 Network-First + 文档离线回退首页
   ============================================================ */

"use strict";

var CACHE_NAME = "tang-poetry-v6";
var PRECACHE_PAGES = [
  "./",
  "./index.html",
  "./navigation.html",
  "./poem.html",
  "./poet.html",
  "./poets.html",
  "./members.html",
  "./sources.html",
  "./about.html",
  "./society.html",
  "./lessons.html",
  "./news.html",
  "./periodicals.html"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(PRECACHE_PAGES);
    }).catch(function () {
      // 预缓存失败不阻断安装
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (key) {
          return key !== CACHE_NAME;
        }).map(function (key) {
          return caches.delete(key);
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", function (event) {
  var request = event.request;
  if (request.method !== "GET") return;

  var url;
  try {
    url = new URL(request.url);
  } catch (e) {
    return;
  }

  // 投稿后台（Decap CMS）：始终走网络，避免缓存导致编辑态与仓库内容不一致
  if (url.origin === self.location.origin && url.pathname.indexOf("/admin") >= 0) {
    return;
  }

  // 外部资源（Google Fonts 等）：Network-First，失败回缓存
  if (url.origin !== self.location.origin) {
    event.respondWith(
      fetch(request).then(function (response) {
        if (response && response.status === 200) {
          var copy = response.clone();
          caches.open(CACHE_NAME).then(function (cache) {
            cache.put(request, copy);
          });
        }
        return response;
      }).catch(function () {
        return caches.match(request);
      })
    );
    return;
  }

  // 同源资源：Stale-While-Revalidate（优先返回缓存，同时后台更新）
  event.respondWith(
    caches.match(request).then(function (cached) {
      var network = fetch(request).then(function (response) {
        if (response && response.status === 200) {
          var copy = response.clone();
          caches.open(CACHE_NAME).then(function (cache) {
            cache.put(request, copy);
          });
        }
        return response;
      }).catch(function () {
        if (request.destination === "document") {
          return caches.match("./index.html");
        }
        return cached;
      });
      return cached || network;
    })
  );
});
