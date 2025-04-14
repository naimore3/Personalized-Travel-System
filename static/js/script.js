function navigate() {
    const start = document.getElementById('start').value;
    const end = document.getElementById('end').value;

    // 创建一个路径规划实例
    AMap.service('AMap.Driving', function() {
        var driving = new AMap.Driving({
            map: map,
            panel: 'panel'
        });
        // 根据起点和终点进行路径规划
        driving.search([{keyword: start}], {keyword: end}, function(status, result) {
            if (status === 'complete') {
                console.log('路径规划成功');
            } else {
                console.log('路径规划失败');
            }
        });
    });
}