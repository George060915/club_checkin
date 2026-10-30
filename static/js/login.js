  var loginForm = document.getElementById('loginForm');
  var regForm = document.getElementById('regForm');
  /* 修改：删掉 okToast/toastTimer——注册成功提示改为后端渲染，前端不再造假提示 */

  /* 切换登录 / 注册 */
  function switchTo(name) {
    var isLogin = name === 'login';
    loginForm.className = isLogin ? 'on' : '';
    regForm.className = isLogin ? '' : 'on';
    document.getElementById('tabLogin').className = isLogin ? 'tab on' : 'tab';
    document.getElementById('tabReg').className = isLogin ? 'tab' : 'tab on';
  }
  document.getElementById('tabLogin').onclick = function () { switchTo('login'); };
  document.getElementById('tabReg').onclick = function () { switchTo('register'); };

  /* 修改：删掉了原来的 regForm.onsubmit —— 里面的 e.preventDefault() 拦截了表单提交，
     注册请求根本没发到后端，数据库自然不更新；现在表单会正常 POST 到 /register */
  /* 注册失败时后端会重渲染页面,body 的 data-tab 会等于 'register',据此切回注册页签 */
  if (document.body.getAttribute('data-tab') === 'register') {
    switchTo('register');
  }
