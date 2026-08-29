/* agent-hive 官网 Service Worker
 * 策略：同源 GET 请求 cache-first；跨域请求（如 shields.io 徽章）直接走网络、不缓存。
 * 离线时：已缓存资源直接可用；未缓存的页面导航回退到首页。
 * 升级：修改 CACHE_VERSION 即可触发全量缓存重建（activate 时清理旧缓存）。
 */
'use strict';

const CACHE_VERSION = 'v1';
const CACHE_NAME = 'agent-hive-' + CACHE_VERSION;

// 安装阶段预缓存的核心资源（离线首屏可用）
const PRECACHE_URLS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png',
  './icons/favicon-32.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.startsWith('agent-hive-') && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;

  // 只处理同源的 GET 请求；跨域（徽章等）不接管
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // 页面导航离线回退到首页
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() => caches.match('./index.html'))
    );
    return;
  }

  // 其余同源资源：cache-first，miss 时回源并写入缓存
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (response && response.status === 200 && response.type === 'basic') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      });
    })
  );
});
