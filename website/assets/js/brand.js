/*
 * 全站品牌单一数据源 (P0 · 品牌配置化)
 * ------------------------------------------------------------------
 * 修改站名 / 印章 / 页脚 / 版权 / OG 只需改这里，无需逐个页面改字符串。
 * HTML 中带 data-brand="<key>" 的节点会在 DOMContentLoaded 后被自动填充；
 * JS 页面（page-poem / page-poet / page-sources）直接读取 window.BRAND。
 *
 * 注意：页脚中描述「经典库底本」的那一行是内容性文字（各页不同），
 *       不属于品牌，保留在各页 HTML 中，不在此集中。
 */
window.BRAND = {
  // 站点名
  name: "石湖诗社",
  nameEn: "Shihu Poetry Society",

  // 首页主视觉
  heroTitle: "石湖诗社",
  heroSubtitle: "诗 集 珍 赏",
  heroEn: "Shihu Poetry Society · Classical & Contemporary Verse",
  heroSealChar: "石",
  heroSealLabel: "Seal of Shihu",

  // 顶部导航 Logo
  navName: "石湖诗社",
  navEn: "Shihu Poetry Society",

  // 印章行（页脚左右小印）
  sealLeft: "石",
  sealRight: "社",

  // 页脚 / 版权 / OG
  footerName: "石湖诗社",
  copyright: "© 2026 石湖诗社 · 仅用于学习与赏析",
  ogSiteName: "石湖诗社",

  // 典籍页标题后缀（描述经典库本体；内容性，可保留「全唐诗」）
  sourceSuffix: "全唐诗"
};

/* 自动把 BRAND 应用到带 data-brand 标记的 DOM 节点 */
(function () {
  function applyBrand() {
    var B = window.BRAND || {};
    var map = {
      "hero-title": B.heroTitle,
      "hero-subtitle": B.heroSubtitle,
      "hero-en": B.heroEn,
      "hero-seal": B.heroSealChar,
      "hero-seal-label": B.heroSealLabel,
      "nav-name": B.navName,
      "nav-en": B.navEn,
      "seal-left": B.sealLeft,
      "seal-right": B.sealRight,
      "footer-name": B.footerName,
      "copyright": B.copyright
    };
    Object.keys(map).forEach(function (key) {
      var nodes = document.querySelectorAll('[data-brand="' + key + '"]');
      for (var i = 0; i < nodes.length; i++) {
        if (map[key] != null) nodes[i].textContent = map[key];
      }
    });
    // 同步 og:site_name
    if (B.ogSiteName) {
      var og = document.querySelector('meta[property="og:site_name"]');
      if (!og) {
        og = document.createElement("meta");
        og.setAttribute("property", "og:site_name");
        document.head.appendChild(og);
      }
      og.setAttribute("content", B.ogSiteName);
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", applyBrand);
  } else {
    applyBrand();
  }
})();
