// 动态生成导航栏
function renderNavbar(activePage) {
    // 检查登录状态，假设用localStorage存储用户名（如localStorage.username）
    const username = localStorage.getItem('username');
    let rightNav = '';
    if (username) {
        rightNav = `
        <li class="nav-item dropdown">
            <a class="nav-link dropdown-toggle${activePage==='profile'?' active':''}" href="#" id="userDropdown" role="button" data-bs-toggle="dropdown">${username}</a>
            <ul class="dropdown-menu dropdown-menu-end">
                <li><a class="dropdown-item" href="/profile">个人中心</a></li>
                <li><a class="dropdown-item" href="#" id="logoutBtn">退出登录</a></li>
            </ul>
        </li>
        `;
    } else {
        rightNav = `
        <li class="nav-item">
            <a class="nav-link${activePage==='login'?' active':''}" href="/login">登录</a>
        </li>
        `;
    }
    const navbarHTML = `
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <div class="container">
            <a class="navbar-brand" href="/">环球寻光记</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item">
                        <a class="nav-link${activePage==='index'?' active':''}" href="/">首页</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link${activePage==='recommend'?' active':''}" href="/recommend">推荐</a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle${activePage==='domestic_map'||activePage==='global_map'?' active':''}" href="#" id="mapDropdown" role="button" data-bs-toggle="dropdown">地图</a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="/domestic_map">国内畅游</a></li>
                            <li><a class="dropdown-item" href="/global_map">环球寻光</a></li>
                        </ul>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link${activePage==='punch'?' active':''}" href="/punch">打卡</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link${activePage==='search'?' active':''}" href="/search">搜索</a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle${activePage==='indoor_navigation'||activePage==='food_discovery'?' active':''}" href="#" id="discoveryDropdown" role="button" data-bs-toggle="dropdown">精彩发现</a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="/indoor_navigation">室内导航</a></li>
                            <li><a class="dropdown-item" href="/food_discovery">美食发现</a></li>
                        </ul>
                    </li>
                </ul>
                <ul class="navbar-nav">${rightNav}</ul>
            </div>
        </div>
    </nav>`;
    const navDiv = document.getElementById('navbar');
    if(navDiv) navDiv.innerHTML = navbarHTML;
    // 绑定退出登录事件
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            localStorage.removeItem('username');
            window.location.href = '/login';
        });
    }
}

// 自动判断当前页面高亮
function getActivePage() {
    const path = window.location.pathname;
    if(path==='/') return 'index';
    if(path.startsWith('/recommend')) return 'recommend';
    if(path.startsWith('/domestic_map')) return 'domestic_map';
    if(path.startsWith('/global_map')) return 'global_map';
    if(path.startsWith('/punch')) return 'punch';
    if(path.startsWith('/search')) return 'search';
    if(path.startsWith('/indoor_navigation')) return 'indoor_navigation';
    if(path.startsWith('/food_discovery')) return 'food_discovery';
    if(path.startsWith('/profile')) return 'profile';
    if(path.startsWith('/login')) return 'login';
    return '';
}

document.addEventListener('DOMContentLoaded', function() {
    renderNavbar(getActivePage());
});