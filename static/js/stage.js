/* ==========================================================================
   stage.js —— 下盒按 X 轴比例等比缩放
   --------------------------------------------------------------------------
   设计宽度 = --mv-content-max（与内容列宽一致，默认 760px）。
     · 缩放系数 k = 可用宽 ÷ 设计宽  → 宽度永远铺满，不存在横向留白
     · 高度 = 当前内容自然高 × k      → 多出来的竖直空间即留白
     · 内容始终按设计宽度排版：只改缩放系数，绝不触发响应式重排
   依赖结构（见 template/index.html、template/user_index.html）：
     <body class="mv-shell">
       <header class="nav">…</header>
       <div class="mv-stage">
         <div class="mv-frame">
           <main class="wrap">…</main>
         </div>
       </div>
   ========================================================================== */
(function () {
  'use strict';

  function init() {
    var stage = document.querySelector('.mv-stage');
    if (!stage) return;
    var frame = stage.querySelector('.mv-frame');
    var wrap = frame && frame.querySelector('.wrap');
    if (!frame || !wrap) return;

    var DW = parseFloat(getComputedStyle(stage).getPropertyValue('--mv-content-max')) ||
             parseFloat(stage.getAttribute('data-canvas')) || 760;
    var timer = 0;

    function fit() {
      wrap.style.width = DW + 'px';                     /* 先按设计宽度排版，量出自然高 */
      var contentH = Math.max(1, Math.ceil(wrap.scrollHeight));
      var cs = getComputedStyle(stage);
      var padX = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
      var availW = Math.max(1, stage.clientWidth - padX);
      var k = availW / DW;                              /* 只按 X 轴比例 */
      var fw = (DW * k).toFixed(2) + 'px';
      var fh = (contentH * k).toFixed(2) + 'px';
      var tf = 'scale(' + k + ')';
      if (frame.style.width !== fw) frame.style.width = fw;
      if (frame.style.height !== fh) frame.style.height = fh;
      if (wrap.style.transform !== tf) wrap.style.transform = tf;
    }

    /* 去抖：窗口连拖时只算最后一次 */
    function apply() {
      clearTimeout(timer);
      timer = setTimeout(fit, 24);
    }

    window.addEventListener('resize', apply);
    window.addEventListener('orientationchange', apply);
    /* 页面从隐藏变可见时复测一次（面板先窄后宽的情形） */
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) apply();
    });
    if (window.ResizeObserver) {
      new ResizeObserver(apply).observe(stage);   /* 舞台尺寸变 */
      new ResizeObserver(apply).observe(wrap);    /* 内容高变（图片加载、数据渲染等） */
    }
    /* 切换页签后内容高会变，重新量一次 */
    Array.prototype.forEach.call(document.querySelectorAll('.menu button'), function (b) {
      b.addEventListener('click', function () { setTimeout(apply, 30); });
    });
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(apply).catch(function () {});
    }

    fit();
    /* 首次加载后多复测几次，兜住字体 / 图片 / 表格等后到的布局变化 */
    [120, 400, 900, 1800, 3000].forEach(function (ms) { setTimeout(fit, ms); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
