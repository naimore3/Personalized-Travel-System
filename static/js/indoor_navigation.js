// static/js/indoor_navigation.js

const FACILITIES = [
    {name: "楼梯", key: "stair"},
    {name: "电梯", key: "elevator"},
    {name: "厕所", key: "toilet"},
    {name: "饮水间", key: "water"},
    {name: "办公室", key: "office"},
    {name: "阳台", key: "balcony"},
    {name: "食堂", key: "canteen"},
    {name: "健身房", key: "gym"},
    {name: "娱乐室", key: "entertainment"}
];
const ICONS = [
    "白猫.png","边牧.png","布偶猫.png","仓鼠.png","藏獒.png","柴犬.png","法斗.png","更多猫宠.png","更多萌宠.png","更多犬种.png","哈士奇.png","荷兰猪.png","黑猫.png","金毛.png","橘猫.png","柯基.png","可达鸭.png","腊肠犬.png","蓝猫.png","奶牛猫.png","三花猫.png","田园犬.png","无毛猫.png","暹罗猫.png","羊.png"
];

let totalFloors = 0;
let floorData = {}; // {1: [设施列表], 2: [设施列表], ...}
let currentFloor = 1;
let currentPath = null; // 保存当前路径
const mapWidth = 0, mapHeight = 0; // 占位，后面动态获取

function randomInt(a, b) { return Math.floor(Math.random() * (b - a + 1)) + a; }
function randomIcon() { return ICONS[randomInt(0, ICONS.length-1)]; }

function getMapAreaSize() {
    // 获取map-area的实际大小（包括padding），如为0则用窗口宽高减去侧边栏
    const map = document.getElementById("map-area");
    let width = map.offsetWidth;
    let height = map.offsetHeight;
    // 若页面初次渲染时宽高为0，尝试用window宽高估算
    if (!width || !height) {
        width = window.innerWidth - 320; // 侧边栏宽度+边距
        height = window.innerHeight - 80; // 预留顶部导航和边距
    }
    return { width, height };
}

function ensureGraphConnected(facilities, graph) {
    // 用BFS找连通分量
    const n = facilities.length;
    let visited = new Array(n).fill(false);
    let components = [];
    for (let i = 0; i < n; i++) {
        if (!visited[i]) {
            let queue = [i];
            let comp = [];
            visited[i] = true;
            while (queue.length) {
                let u = queue.shift();
                comp.push(u);
                (graph[u]||[]).forEach(v => {
                    if (!visited[v]) {
                        visited[v] = true;
                        queue.push(v);
                    }
                });
            }
            components.push(comp);
        }
    }
    // 如果只有一个分量，已连通
    if (components.length <= 1) return graph;
    // 否则补边：每次把前一个分量和下一个分量最近的点连起来
    for (let k = 1; k < components.length; k++) {
        let minDist = Infinity, a = -1, b = -1;
        for (let i of components[k-1]) {
            for (let j of components[k]) {
                let dx = facilities[i].x - facilities[j].x;
                let dy = facilities[i].y - facilities[j].y;
                let dist = Math.sqrt(dx*dx + dy*dy);
                if (dist < minDist) {
                    minDist = dist; a = i; b = j;
                }
            }
        }
        // 补边（无向图）
        if (!graph[a].includes(b)) graph[a].push(b);
        if (!graph[b].includes(a)) graph[b].push(a);
        // 合并分量
        components[k] = components[k-1].concat(components[k]);
    }
    return graph;
}

function buildGraphForFloor(facilities) {
    // 以设施索引为节点，返回邻接表 {0: [1,2], 1: [0,3], ...}
    const graph = {};
    const threshold = 180; // 距离阈值，单位像素，可调整
    for (let i = 0; i < facilities.length; i++) {
        graph[i] = [];
        for (let j = 0; j < facilities.length; j++) {
            if (i === j) continue;
            // 楼梯、电梯、厕所等特殊点可全部互连
            if (["stair","elevator","toilet"].includes(facilities[i].key) && ["stair","elevator","toilet"].includes(facilities[j].key)) {
                graph[i].push(j);
            } else {
                // 其他点距离小于阈值则连边
                const dx = facilities[i].x - facilities[j].x;
                const dy = facilities[i].y - facilities[j].y;
                const dist = Math.sqrt(dx*dx + dy*dy);
                if (dist < threshold) {
                    graph[i].push(j);
                }
            }
        }
    }
    // 新增：补边确保全连通
    return ensureGraphConnected(facilities, graph);
}

function generateFloors() {
    totalFloors = randomInt(3, 100);
    // 先渲染一次以确保map-area有尺寸
    setTimeout(() => {
        const size = getMapAreaSize();
        for (let f = 1; f <= totalFloors; f++) {
            let used = [];
            let facilities = [];
            // 必须设施
            ["楼梯", "电梯", "厕所"].forEach(name => {
                facilities.push({
                    name, key: FACILITIES.find(x=>x.name===name).key,
                    icon: randomIcon(),
                    x: randomInt(30, size.width-50),
                    y: randomInt(30, size.height-70)
                });
                used.push(name);
            });
            // 阳台
            let balconyPos = [
                {x: 10, y: randomInt(10, size.height-60)},
                {x: size.width-50, y: randomInt(10, size.height-60)},
                {x: randomInt(10, size.width-50), y: 10},
                {x: randomInt(10, size.width-50), y: size.height-60}
            ][randomInt(0,3)];
            facilities.push({
                name: "阳台", key: "balcony", icon: randomIcon(),
                x: balconyPos.x, y: balconyPos.y
            });
            used.push("阳台");
            // 其他设施
            FACILITIES.forEach(fac => {
                if (!used.includes(fac.name)) {
                    let n = randomInt(0, 3);
                    for (let i = 0; i < n; i++) {
                        facilities.push({
                            name: fac.name, key: fac.key, icon: randomIcon(),
                            x: randomInt(30, size.width-50),
                            y: randomInt(30, size.height-70)
                        });
                    }
                }
            });
            // 新增：为本层设施建立图关系
            const graph = buildGraphForFloor(facilities);
            floorData[f] = { facilities, graph };
        }
        // 保存到本地
        localStorage.setItem("indoor_floors", JSON.stringify({totalFloors, floorData}));
        renderFloor(currentFloor);
    }, 100);
}

function loadFloors() {
    let data = localStorage.getItem("indoor_floors");
    if (data) {
        let obj = JSON.parse(data);
        totalFloors = obj.totalFloors;
        floorData = obj.floorData;
    } else {
        generateFloors();
    }
}

function renderFloor(floor) {
    const map = document.getElementById("map-area");
    // 清除旧设施
    map.querySelectorAll(".facility").forEach(e=>e.remove());
    // 清除旧连线
    let oldSvg = document.getElementById("floor-graph-svg");
    if (oldSvg) oldSvg.remove();
    // 渲染设施
    const facilities = (floorData[floor]?.facilities)||[];
    facilities.forEach((item, idx) => {
        let div = document.createElement("div");
        div.className = "facility";
        div.style.left = (item.x-20) + "px";
        div.style.top = (item.y-20) + "px";
        div.innerHTML = `<img src="/static/icons/${item.icon}" alt="${item.name}">
            <div class="facility-label">${item.name}</div>`;
        map.appendChild(div);
    });
    // 新增：渲染连接线
    const graph = (floorData[floor]?.graph)||{};
    if (facilities.length > 0) {
        let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("id", "floor-graph-svg");
        svg.style.position = "absolute";
        svg.style.left = "0";
        svg.style.top = "0";
        svg.style.width = "100%";
        svg.style.height = "100%";
        svg.style.pointerEvents = "none";
        svg.style.zIndex = "2";
        // 画线
        for (let i in graph) {
            let from = facilities[i];
            if (!from) continue;
            graph[i].forEach(j => {
                // 只画一次（i<j）避免重复
                if (parseInt(i) < j) {
                    let to = facilities[j];
                    if (!to) return;
                    let line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                    line.setAttribute("x1", from.x);
                    line.setAttribute("y1", from.y);
                    line.setAttribute("x2", to.x);
                    line.setAttribute("y2", to.y);
                    line.setAttribute("stroke", "#007bff");
                    line.setAttribute("stroke-width", "2");
                    line.setAttribute("opacity", "0.5");
                    svg.appendChild(line);
                }
            });
        }
        map.appendChild(svg);
    }
    document.getElementById("current-floor").innerText = floor;
    document.getElementById("total-floors").innerText = totalFloors;
    document.getElementById("floor-input").value = floor;
    updateFloorControls();
    // 新增：渲染路径高亮
    highlightPathOnMap(window.currentPath);
}

// 只在初始化和生成楼层后调用，刷新所有下拉框
function updateAllPlaceSelectors() {
    // 地点下拉初始显示“请先选择楼层”
    document.getElementById("start-place").innerHTML = '<option value="">请先选择楼层</option>';
    document.getElementById("end-place").innerHTML = '<option value="">请先选择楼层</option>';
    // 楼层下拉
    let floorOpts = '<option value="">请选择楼层</option>';
    for (let i=1; i<=totalFloors; i++) floorOpts += `<option value="${i}">${i}</option>`;
    document.getElementById("start-floor").innerHTML = floorOpts;
    document.getElementById("end-floor").innerHTML = floorOpts;
    document.getElementById("start-floor").value = "";
    document.getElementById("end-floor").value = "";
}

// 仅在用户手动切换楼层时调用，刷新对应下拉框
function updateCurrentFloorPlaceSelector(floorId, placeId) {
    let val = parseInt(document.getElementById(floorId).value);
    if (val>=1 && val<=totalFloors) {
        let places = '<option value="">请选择地点</option>';
        const facilities = (floorData[val]?.facilities)||[];
        places += facilities.map((item, idx) => `<option value="${idx}">${item.name}</option>`).join("");
        document.getElementById(placeId).innerHTML = places;
    } else {
        document.getElementById(placeId).innerHTML = '<option value="">请先选择楼层</option>';
    }
}

function updateFloorControls() {
    // 底楼（1层）只显示上一层，顶楼只显示下一层，其余都显示
    if (currentFloor === 1) {
        document.getElementById("prev-floor").style.display = "";
        document.getElementById("next-floor").style.display = "none";
    } else if (currentFloor === totalFloors) {
        document.getElementById("prev-floor").style.display = "none";
        document.getElementById("next-floor").style.display = "";
    } else {
        document.getElementById("prev-floor").style.display = "";
        document.getElementById("next-floor").style.display = "";
    }
    document.getElementById("floor-input").min = 1;
    document.getElementById("floor-input").max = totalFloors;
}

function highlightPathOnMap(path) {
    // 清除旧路径高亮
    const map = document.getElementById("map-area");
    let oldSvg = document.getElementById("path-highlight-svg");
    if (oldSvg) oldSvg.remove();
    if (!path || !Array.isArray(path) || path.length === 0) return;
    // 判断当前楼层
    const floor = currentFloor;
    // 过滤出本层需要绘制的路径点
    let segs = [];
    // 判断是否为同层路径
    const allSameFloor = path.every(pt => pt.floor === floor);
    if (allSameFloor) {
        // 全部点都在本层，直接连线
        segs = path.map(pt => pt.index);
    } else {
        // 跨层：找本层相关段
        // 找到本层的所有连续片段
        let temp = [];
        for (let i = 0; i < path.length; i++) {
            if (path[i].floor === floor) {
                temp.push(path[i].index);
            } else if (temp.length > 0) {
                segs.push([...temp]);
                temp = [];
            }
        }
        if (temp.length > 0) segs.push([...temp]);
        // 只绘制本层的段
        if (segs.length > 0) segs = segs[0];
        else segs = [];
    }
    if (!segs || segs.length < 2) return;
    // 获取设施坐标
    const facilities = (floorData[floor]?.facilities)||[];
    // 绘制SVG路径
    let svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("id", "path-highlight-svg");
    svg.style.position = "absolute";
    svg.style.left = "0";
    svg.style.top = "0";
    svg.style.width = "100%";
    svg.style.height = "100%";
    svg.style.pointerEvents = "none";
    svg.style.zIndex = "10";
    // 画线
    for (let i = 0; i < segs.length - 1; i++) {
        let a = facilities[segs[i]], b = facilities[segs[i+1]];
        if (!a || !b) continue;
        let line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", a.x);
        line.setAttribute("y1", a.y);
        line.setAttribute("x2", b.x);
        line.setAttribute("y2", b.y);
        line.setAttribute("stroke", "#e53935");
        line.setAttribute("stroke-width", "6");
        line.setAttribute("stroke-linecap", "round");
        line.setAttribute("opacity", "0.85");
        svg.appendChild(line);
    }
    map.appendChild(svg);
}

document.addEventListener("DOMContentLoaded", function() {
    // 新增：每次进入页面时清除本地楼层布局缓存
    localStorage.removeItem("indoor_floors");
    // 新增：等待map-area尺寸有效后再生成楼层数据
    function waitForMapAreaSize(callback, tryCount=0) {
        const map = document.getElementById("map-area");
        if (map && map.offsetWidth > 100 && map.offsetHeight > 100) {
            callback();
        } else if (tryCount < 30) { // 最多等3秒
            setTimeout(() => waitForMapAreaSize(callback, tryCount+1), 100);
        } else {
            // 超时兜底
            callback();
        }
    }

    // 这里不再判断localStorage，直接生成
    waitForMapAreaSize(function() {
        generateFloors();
        updateAllPlaceSelectors();
    });

    document.getElementById("prev-floor").onclick = function() {
        if (currentFloor < totalFloors) { currentFloor++; renderFloor(currentFloor);}
    };
    document.getElementById("next-floor").onclick = function() {
        if (currentFloor > 1) { currentFloor--; renderFloor(currentFloor);}
    };
    document.getElementById("floor-input").onchange = function() {
        let val = parseInt(this.value);
        if (val>=1 && val<=totalFloors) { currentFloor = val; renderFloor(currentFloor);}
    };
    document.getElementById("start-floor").onchange = function() {
        updateCurrentFloorPlaceSelector("start-floor", "start-place");
    };
    document.getElementById("end-floor").onchange = function() {
        updateCurrentFloorPlaceSelector("end-floor", "end-place");
    };
    document.getElementById("search-form").onsubmit = function(e) {
        e.preventDefault();
        // 获取起点终点信息
        const startFloor = document.getElementById("start-floor").value;
        const startIdx = document.getElementById("start-place").value;
        const endFloor = document.getElementById("end-floor").value;
        const endIdx = document.getElementById("end-place").value;
        if (!startFloor || !startIdx || !endFloor || !endIdx) {
            alert("请完整选择起点和终点");
            return;
        }
        // 发送AJAX请求到后端
        fetch("/api/indoor_path", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                start_floor: startFloor,
                start_idx: startIdx,
                end_floor: endFloor,
                end_idx: endIdx,
                floorData: floorData
            })
        })
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                alert(data.message || "未找到可行路径");
                return;
            }
            renderNavigationSteps(data.path);
            window.currentPath = data.path; // 保存路径
            highlightPathOnMap(window.currentPath); // 立即高亮
        })
        .catch(err => {
            alert("导航请求失败");
        });
    };

    // 渲染导航步骤到左侧栏
    function renderNavigationSteps(path) {
        let navBox = document.getElementById("navigation-steps");
        // 插入到搜索框下方
        let searchForm = document.getElementById("search-form");
        if (!navBox) {
            navBox = document.createElement("div");
            navBox.id = "navigation-steps";
            navBox.style.flex = "1 1 auto";
            navBox.style.minHeight = "0";
            navBox.style.margin = "0";
        }
        // 设置滚动条样式和高度，去除maxHeight，改为100%
        navBox.style.height = "100%";
        navBox.style.overflowY = "auto";
        navBox.style.background = "#fff";
        navBox.style.borderRadius = "10px";
        navBox.style.boxShadow = "0 2px 8px #0001";
        navBox.style.padding = "0 0 8px 0";
        navBox.style.width = "100%";
        if (searchForm && searchForm.nextSibling !== navBox) {
            searchForm.parentNode.insertBefore(navBox, searchForm.nextSibling);
        }
        // 颜色映射
        const typeColor = {
            stair:   '#ff9800', // 橙
            elevator:'#4caf50', // 绿
            toilet:  '#2196f3', // 蓝
            office:  '#757575', // 灰
            balcony: '#00bcd4', // 青
            canteen: '#e53935', // 红
            gym:     '#8e24aa', // 紫
            entertainment: '#ffd600', // 黄
            water:   '#009688', // 深青
            default: '#607d8b'  // 默认
        };
        // 步骤渲染（每个地点一行，纵向排列）
        let html = '<div style="font-weight:bold;margin-bottom:8px;">导航步骤：</div>';
        html += '<div class="nav-steps-vertical" style="display:flex;flex-direction:column;gap:10px;">';
        path.forEach((pt, i) => {
            if (pt.floor === '跨层') {
                html += `<div style='border:2px dashed #007bff;padding:8px 16px;border-radius:8px;background:#e3f2fd;color:#007bff;min-width:90px;text-align:center;font-weight:bold;'>${pt.name}</div>`;
            } else {
                let tag = i === 0 ? '起点' : (i === path.length-1 ? '终点' : (['stair','elevator'].includes(pt.type) ? '中转' : '途经'));
                let color = typeColor[pt.type] || typeColor.default;
                let bg = color + '22'; // 透明背景
                html += `<div class="nav-step-box" style="width:100%;max-width:220px;padding:8px 10px;border-radius:10px;border:2px solid ${color};background:${bg};text-align:left;position:relative;">
                    <div style="font-size:16px;font-weight:600;color:${color};">${pt.name}</div>
                    <div style="font-size:12px;color:#888;">${pt.floor}F</div>
                    <div style="font-size:11px;color:#fff;background:${color};border-radius:6px;padding:1px 6px;display:inline-block;margin-top:4px;">${tag}</div>
                </div>`;
            }
        });
        html += '</div>';
        navBox.innerHTML = html;
    }

    // highlightPathOnMap函数已删除，不再绘制路径高亮
    // 添加高亮节点样式
    const style = document.createElement('style');
    style.innerHTML = `.facility.nav-highlight {box-shadow:0 0 0 4px #e5393599,0 0 12px 4px #fff3;z-index:10;position:relative;}`;
    document.head.appendChild(style);
});
