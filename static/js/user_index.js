  /* 导航切换 */
  var tabs = document.querySelectorAll('.menu button');
  for (var i = 0; i < tabs.length; i++) {
    tabs[i].onclick = function () {
      for (var j = 0; j < tabs.length; j++) tabs[j].className = '';
      this.className = 'on';
      var views = document.querySelectorAll('.view');
      for (var k = 0; k < views.length; k++) views[k].className = 'view';
      document.getElementById('view-' + this.dataset.view).className = 'view on';
    };
  }

  /* 首页快捷入口:点击卡片切到对应页签(复用导航按钮的切换逻辑) */
  var quicks = document.querySelectorAll('.quick__item');
  for (var qi = 0; qi < quicks.length; qi++) {
    quicks[qi].onclick = function () {
      var btn = document.querySelector('.menu button[data-view="' + this.dataset.goto + '"]');
      if (btn) btn.onclick();
    };
  }

  /* 记录筛选 */
  var chips = document.querySelectorAll('.chips button');
  for (var c = 0; c < chips.length; c++) {
    chips[c].onclick = function () {
      for (var m = 0; m < chips.length; m++) chips[m].className = '';
      this.className = 'on';
      var type = this.dataset.type;
      var rows = document.querySelectorAll('tbody tr[data-type]');
      for (var n = 0; n < rows.length; n++) {
        rows[n].style.display = (type === 'all' || rows[n].dataset.type === type) ? '' : 'none';
      }
    };
  }

  /* 网址带 #xxx 时自动切到对应页签(比如后端跳 /user_index#records) */
  if (location.hash) {
    var hb = document.querySelector('.menu button[data-view="' + location.hash.slice(1) + '"]');
    if (hb) hb.onclick();
  }

  /* 提示条:4 秒后淡出,动画结束(0.4 秒)再彻底移除 */
  var toasts = document.querySelectorAll('.toast');
  if (toasts.length) {
    setTimeout(function () {
      for (var t = 0; t < toasts.length; t++) toasts[t].style.opacity = '0';
    }, 4000);
    setTimeout(function () {
      for (var t = 0; t < toasts.length; t++) toasts[t].style.display = 'none';
    }, 4400);

    /* 顺手把网址里的 ?ok=/?error= 清掉:
       提示是后端放在网址参数里传过来的,不清理的话用户一刷新又会弹出来 */
    var url = new URL(location.href);
    url.searchParams.delete('ok');
    url.searchParams.delete('error');
    history.replaceState(null, '', url);
  }
