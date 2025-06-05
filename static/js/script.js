function navigate() {
    const start = document.getElementById('start').value;
    const end = document.getElementById('end').value;

    if (start && end) {
        // 初始化地图
        const map = new AMap.Map('map', {
            zoom: 10,
            center: [116.397428, 39.90923]
        });

        // 创建驾车导航实例
        const driving = new AMap.Driving({
            map: map,
            panel: 'panel'
        });

        // 发起导航请求
        driving.search(start, end, function(status, result) {
            if (status === 'complete') {
                console.log('导航路线获取成功');
            } else {
                console.log('导航路线获取失败：', result);
            }
        });
    } else {
        alert('请输入起点和终点');
    }
}