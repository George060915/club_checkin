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

  /* 活动管理:新增活动表单的展开/收起 */
  var addBtn = document.getElementById('add-activity-btn');
  var addForm = document.getElementById('add-activity-form');
  addBtn.onclick = function () {
    addBtn.style.display = 'none';
    addForm.style.display = 'block';
  };
  document.getElementById('add-activity-cancel').onclick = function () {
    addForm.style.display = 'none';
    addBtn.style.display = '';
  };

  /* 图文发布:发布表单的展开/收起(和其他管理页签同一个套路) */
  var addPostBtn = document.getElementById('add-post-btn');
  var addPostForm = document.getElementById('add-post-form');
  addPostBtn.onclick = function () {
    addPostBtn.style.display = 'none';
    addPostForm.style.display = 'block';
  };
  document.getElementById('add-post-cancel').onclick = function () {
    addPostForm.style.display = 'none';
    addPostBtn.style.display = '';
  };

  /* 账号管理:新增账号表单的展开/收起(和活动管理同一个套路) */
  var addAccBtn = document.getElementById('add-account-btn');
  var addAccForm = document.getElementById('add-account-form');
  addAccBtn.onclick = function () {
    addAccBtn.style.display = 'none';
    addAccForm.style.display = 'block';
  };
  document.getElementById('add-account-cancel').onclick = function () {
    addAccForm.style.display = 'none';
    addAccBtn.style.display = '';
  };

  /* 账号管理:每行"修改权限"按钮 -> 权限标签和下拉框表单来回切换 */
  var permBtns = document.querySelectorAll('.perm-edit-btn');
  for (var p = 0; p < permBtns.length; p++) {
    permBtns[p].onclick = function () {
      var tr = this.closest('tr');
      var tag = tr.querySelector('.perm-tag');
      var form = tr.querySelector('.perm-form');
      var editing = form.style.display === 'flex';
      tag.style.display = editing ? '' : 'none';
      form.style.display = editing ? 'none' : 'flex';
      this.textContent = editing ? '修改权限' : '取消';
    };
  }

  /* 删除按钮(活动管理/图文发布共用):点垃圾桶 -> 弹确认框 -> 提交这一行的隐藏表单 */
  var delBtns = document.querySelectorAll('.del-btn');
  for (var d = 0; d < delBtns.length; d++) {
    delBtns[d].onclick = function () {
      var word = this.dataset.word || '这条记录';
      // data-word 是"删的是什么"(活动/图文),确认框文案跟着变
      if (confirm('确定删除' + word + '「' + this.dataset.title + '」吗?删除后无法恢复')) {
        this.closest('form').submit();
      }
    };
  }

  /* 网址带 #manage 时自动切到对应页签(发布活动后后端跳转 /index#manage) */
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
