"""웹 대시보드 페이지.

- GET /dashboard             : PC 목록 중심의 관리자 화면 HTML 반환
                               (요약 /api/v1/admin/summary, 목록 /api/v1/admin/machines)
- GET /dashboard/{machine_id}: PC 상세 화면 HTML 반환
                               (/api/v1/admin/machines/{machine_id})
"""

import html as html_lib

from fastapi import APIRouter, Depends, Path
from fastapi.responses import HTMLResponse

from routers.auth_web import require_admin_session

router = APIRouter()


# 대시보드 페이지 (PC 목록 중심) — 세션 인증 필요
@router.get(
    "/dashboard",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin_session)],
)
async def dashboard():
    html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UPM 관리자 - PC 목록</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #4f46e5;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --offline: #94a3b8;
        }
        * { box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 0;
        }
        .navbar {
            background: var(--card-bg);
            padding: 1rem 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        #brand { font-size: 1.25rem; font-weight: 700; color: var(--primary); }
        .navbar .actions { display: flex; align-items: center; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .card {
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
        }
        .card-title { font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.5rem; font-weight: 600; }
        .card-value { font-size: 1.875rem; font-weight: 700; color: var(--text-main); }
        .section-title { font-size: 1rem; font-weight: 600; color: var(--text-main); margin-bottom: 1rem; }
        .machine-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.5rem;
        }
        .machine-card {
            background: var(--card-bg);
            padding: 1.25rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            cursor: pointer;
            transition: transform 0.15s, box-shadow 0.15s;
        }
        .machine-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        }
        .machine-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .machine-id { font-size: 1rem; font-weight: 700; word-break: break-all; }
        .status-badge {
            padding: 0.25rem 0.625rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            color: white;
            white-space: nowrap;
            flex-shrink: 0;
            margin-left: 0.5rem;
        }
        .status-online { background: var(--success); }
        .status-offline { background: var(--offline); }
        .metric { margin-bottom: 0.75rem; }
        .metric-label {
            display: flex;
            justify-content: space-between;
            font-size: 0.8125rem;
            color: var(--text-muted);
            margin-bottom: 0.25rem;
            font-weight: 600;
        }
        .bar-track {
            height: 8px;
            background: #e2e8f0;
            border-radius: 9999px;
            overflow: hidden;
        }
        .bar-fill { height: 100%; border-radius: 9999px; transition: width 0.3s; }
        .bar-cpu { background: var(--danger); }
        .bar-ram { background: #3b82f6; }
        .bar-gpu { background: var(--warning); }
        .last-seen {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 1rem;
            padding-top: 0.75rem;
            border-top: 1px solid #e2e8f0;
        }
        .empty {
            grid-column: 1 / -1;
            text-align: center;
            color: var(--text-muted);
            padding: 3rem 1rem;
        }
        .refresh-btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-weight: 600;
            font-family: inherit;
            font-size: 0.875rem;
            transition: opacity 0.2s;
        }
        .refresh-btn:hover { opacity: 0.9; }
        .logout-btn {
            background: transparent;
            color: var(--text-muted);
            border: 1px solid #e2e8f0;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-weight: 600;
            font-family: inherit;
            font-size: 0.875rem;
            margin-left: 0.5rem;
            transition: background 0.2s;
        }
        .logout-btn:hover { background: #f1f5f9; }
    </style>
</head>
<body>
    <div class="navbar">
        <div id="brand">UPM 관리자</div>
        <div class="actions">
            <span id="lastUpdate" style="font-size: 0.875rem; color: var(--text-muted); margin-right: 1rem;"></span>
            <button class="refresh-btn" onclick="fetchData()">새로고침</button>
            <form method="post" action="/logout" style="display: inline;">
                <button type="submit" class="logout-btn">로그아웃</button>
            </form>
        </div>
    </div>

    <div class="container">
        <div class="summary-grid">
            <div class="card">
                <div class="card-title">총 PC 수</div>
                <div class="card-value" id="sumTotal">-</div>
            </div>
            <div class="card">
                <div class="card-title">온라인 PC 수</div>
                <div class="card-value" id="sumOnline">-</div>
            </div>
            <div class="card">
                <div class="card-title">평균 CPU 사용률</div>
                <div class="card-value" id="sumCpu">-</div>
            </div>
            <div class="card">
                <div class="card-title">평균 RAM 사용률</div>
                <div class="card-value" id="sumRam">-</div>
            </div>
        </div>

        <div class="section-title">PC 목록</div>
        <div class="machine-grid" id="machineGrid"></div>
    </div>

    <script>
        // admin API는 세션 인증이 필요하다. 세션이 만료되면 서버가 /login으로 리다이렉트하므로,
        // fetch가 리다이렉트를 따라간 경우(response.redirected) 로그인 페이지로 이동시킨다.
        async function apiGet(url) {
            const res = await fetch(url);
            if (res.redirected || res.status === 401 || res.status === 403) {
                window.location.href = '/login';
                return null;
            }
            if (!res.ok) throw new Error('요청 실패: ' + res.status);
            return res.json();
        }

        function clamp(v) {
            const n = Number(v) || 0;
            return Math.max(0, Math.min(100, n));
        }

        function updateSummary(s) {
            document.getElementById('sumTotal').textContent = s.totalMachines;
            document.getElementById('sumOnline').textContent = s.onlineMachines;
            document.getElementById('sumCpu').textContent = s.avgCpuUsage.toFixed(1) + '%';
            document.getElementById('sumRam').textContent = s.avgRamUsage.toFixed(1) + '%';
        }

        // 라벨 + 사용률 막대 한 줄을 DOM으로 생성 (innerHTML 조립 금지)
        function buildMetric(name, value, fillClass) {
            const pct = clamp(value);

            const metric = document.createElement('div');
            metric.className = 'metric';

            const label = document.createElement('div');
            label.className = 'metric-label';
            const nameSpan = document.createElement('span');
            nameSpan.textContent = name;
            const valSpan = document.createElement('span');
            valSpan.textContent = pct.toFixed(1) + '%';
            label.appendChild(nameSpan);
            label.appendChild(valSpan);

            const track = document.createElement('div');
            track.className = 'bar-track';
            const fill = document.createElement('div');
            fill.className = 'bar-fill ' + fillClass;
            fill.style.width = pct + '%';
            track.appendChild(fill);

            metric.appendChild(label);
            metric.appendChild(track);
            return metric;
        }

        function buildMachineCard(m) {
            const card = document.createElement('div');
            card.className = 'machine-card';
            card.addEventListener('click', function () {
                window.location.href = '/dashboard/' + encodeURIComponent(m.machineId);
            });

            const head = document.createElement('div');
            head.className = 'machine-head';

            const idEl = document.createElement('div');
            idEl.className = 'machine-id';
            idEl.textContent = m.machineId;

            const badge = document.createElement('span');
            badge.className = 'status-badge ' + (m.online ? 'status-online' : 'status-offline');
            badge.textContent = m.online ? '온라인' : '오프라인';

            head.appendChild(idEl);
            head.appendChild(badge);
            card.appendChild(head);

            card.appendChild(buildMetric('CPU', m.cpuUsage, 'bar-cpu'));
            card.appendChild(buildMetric('RAM', m.ramUsage, 'bar-ram'));
            card.appendChild(buildMetric('GPU', m.gpuUsage, 'bar-gpu'));

            const seen = document.createElement('div');
            seen.className = 'last-seen';
            seen.textContent = '마지막 수신: ' + (m.lastSeen ? new Date(m.lastSeen).toLocaleString() : '-');
            card.appendChild(seen);

            return card;
        }

        function updateMachines(machines) {
            const grid = document.getElementById('machineGrid');
            grid.textContent = '';  // 기존 카드 비우기

            if (!machines || machines.length === 0) {
                const empty = document.createElement('div');
                empty.className = 'empty';
                empty.textContent = '등록된 PC가 없습니다.';
                grid.appendChild(empty);
                return;
            }
            machines.forEach(function (m) {
                grid.appendChild(buildMachineCard(m));
            });
        }

        async function fetchData() {
            try {
                const [summary, machines] = await Promise.all([
                    apiGet('/api/v1/admin/summary'),
                    apiGet('/api/v1/admin/machines'),
                ]);
                if (!summary || !machines) return;  // 인증 만료 → 리다이렉트 처리됨
                updateSummary(summary);
                updateMachines(machines);
                document.getElementById('lastUpdate').textContent =
                    '마지막 갱신: ' + new Date().toLocaleTimeString();
            } catch (e) {
                console.error('데이터 로드 실패:', e);
            }
        }

        fetchData();
        setInterval(fetchData, 10000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


# PC 상세 화면 — 세션 인증 필요
@router.get(
    "/dashboard/{machine_id}",
    response_class=HTMLResponse,
    dependencies=[Depends(require_admin_session)],
)
async def machine_detail(
    machine_id: str = Path(..., max_length=50, pattern=r"^[A-Za-z0-9_-]+$"),
):
    # 탭 제목에만 서버측 값 삽입(패턴 검증됨). 만약을 위해 HTML 이스케이프.
    # 그 외 machineId는 JS에서 URL 경로로부터 읽어 fetch에 사용한다(주입 방지).
    safe_id = html_lib.escape(machine_id)
    html_content = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UPM 관리자 - __MACHINE_ID__</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #4f46e5;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --offline: #94a3b8;
        }
        * { box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 0;
        }
        .navbar {
            background: var(--card-bg);
            padding: 1rem 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        #brand { font-size: 1.25rem; font-weight: 700; color: var(--primary); }
        .navbar .actions { display: flex; align-items: center; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
        .back-link {
            display: inline-block;
            color: var(--text-muted);
            text-decoration: none;
            font-size: 0.875rem;
            font-weight: 600;
            margin-bottom: 1.25rem;
        }
        .back-link:hover { color: var(--primary); }
        .detail-head {
            display: flex;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        .detail-title { font-size: 1.5rem; font-weight: 700; word-break: break-all; }
        .status-badge {
            padding: 0.25rem 0.625rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            color: white;
            white-space: nowrap;
            margin-left: 0.75rem;
        }
        .status-online { background: var(--success); }
        .status-offline { background: var(--offline); }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .bottom-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }
        @media (max-width: 768px) {
            .charts-grid, .bottom-grid { grid-template-columns: 1fr; }
        }
        .card {
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
        }
        .card-title { font-size: 0.875rem; color: var(--text-muted); margin-bottom: 0.5rem; font-weight: 600; }
        .card-value { font-size: 1.875rem; font-weight: 700; color: var(--text-main); }
        table { width: 100%; border-collapse: collapse; text-align: left; }
        th { background: #f1f5f9; padding: 0.75rem 1rem; font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); }
        td { padding: 0.75rem 1rem; border-top: 1px solid #e2e8f0; font-size: 0.875rem; }
        .exc-list { list-style: none; margin: 0; padding: 0; }
        .exc-list li {
            padding: 0.625rem 0.25rem;
            border-top: 1px solid #e2e8f0;
            font-size: 0.875rem;
        }
        .exc-list li:first-child { border-top: none; }
        .empty {
            text-align: center;
            color: var(--text-muted);
            padding: 2rem 1rem;
            font-size: 0.875rem;
        }
        .refresh-btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-weight: 600;
            font-family: inherit;
            font-size: 0.875rem;
            transition: opacity 0.2s;
        }
        .refresh-btn:hover { opacity: 0.9; }
        .logout-btn {
            background: transparent;
            color: var(--text-muted);
            border: 1px solid #e2e8f0;
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-weight: 600;
            font-family: inherit;
            font-size: 0.875rem;
            margin-left: 0.5rem;
            transition: background 0.2s;
        }
        .logout-btn:hover { background: #f1f5f9; }
    </style>
</head>
<body>
    <div class="navbar">
        <div id="brand">UPM 관리자</div>
        <div class="actions">
            <span id="lastUpdate" style="font-size: 0.875rem; color: var(--text-muted); margin-right: 1rem;"></span>
            <button class="refresh-btn" onclick="fetchData()">새로고침</button>
            <form method="post" action="/logout" style="display: inline;">
                <button type="submit" class="logout-btn">로그아웃</button>
            </form>
        </div>
    </div>

    <div class="container">
        <a class="back-link" href="/dashboard">← PC 목록으로</a>

        <div class="detail-head">
            <span class="detail-title" id="detailId">-</span>
            <span class="status-badge status-offline" id="statusBadge">-</span>
        </div>

        <div class="summary-grid">
            <div class="card">
                <div class="card-title">현재 CPU 사용률</div>
                <div class="card-value" id="curCpu">-</div>
            </div>
            <div class="card">
                <div class="card-title">현재 RAM 사용률</div>
                <div class="card-value" id="curRam">-</div>
            </div>
            <div class="card">
                <div class="card-title">현재 GPU 사용률</div>
                <div class="card-value" id="curGpu">-</div>
            </div>
        </div>

        <div class="charts-grid">
            <div class="card">
                <div class="card-title">RESOURCE TRENDS (CPU & RAM)</div>
                <canvas id="mainChart" height="200"></canvas>
            </div>
            <div class="card">
                <div class="card-title">GPU USAGE TREND (%)</div>
                <canvas id="gpuChart" height="200"></canvas>
            </div>
        </div>

        <div class="bottom-grid">
            <div class="card">
                <div class="card-title">최근 종료된 프로세스</div>
                <table>
                    <thead>
                        <tr><th>프로세스명</th><th>시각</th></tr>
                    </thead>
                    <tbody id="historyBody"></tbody>
                </table>
                <div class="empty" id="historyEmpty" style="display: none;">종료 기록 없음</div>
            </div>
            <div class="card">
                <div class="card-title">등록된 예외 프로세스</div>
                <ul class="exc-list" id="excList"></ul>
                <div class="empty" id="excEmpty" style="display: none;">등록된 예외 없음</div>
            </div>
        </div>
    </div>

    <script>
        // machineId는 URL 경로에서 읽는다(서버측 값 주입 방지).
        const machineId = decodeURIComponent(
            window.location.pathname.split('/').filter(Boolean).pop()
        );
        const ONLINE_WINDOW_MS = 5 * 60 * 1000;  // 5분(목록 화면의 온라인 판정과 동일 기준)
        let mainChart, gpuChart;

        // admin API 세션 인증 대응 + 404(존재하지 않는 PC) 구분
        async function apiGet(url) {
            const res = await fetch(url);
            if (res.redirected || res.status === 401 || res.status === 403) {
                window.location.href = '/login';
                return null;
            }
            if (res.status === 404) return { __notfound: true };
            if (!res.ok) throw new Error('요청 실패: ' + res.status);
            return res.json();
        }

        function clamp(v) {
            const n = Number(v) || 0;
            return Math.max(0, Math.min(100, n));
        }

        function showNotFound() {
            document.getElementById('detailId').textContent = machineId;
            const badge = document.getElementById('statusBadge');
            badge.textContent = '없음';
            document.getElementById('curCpu').textContent = '-';
            document.getElementById('curRam').textContent = '-';
            document.getElementById('curGpu').textContent = '-';
            document.getElementById('historyBody').textContent = '';
            document.getElementById('historyEmpty').textContent = 'PC를 찾을 수 없습니다.';
            document.getElementById('historyEmpty').style.display = 'block';
            document.getElementById('excList').textContent = '';
            document.getElementById('excEmpty').textContent = 'PC를 찾을 수 없습니다.';
            document.getElementById('excEmpty').style.display = 'block';
        }

        function updateHead(data) {
            document.getElementById('detailId').textContent = data.machineId;

            // telemetry는 최신순(DESC). 최신 1건으로 현재 수치/온라인 판정.
            const latest = data.telemetry[0];
            const badge = document.getElementById('statusBadge');
            let online = false;
            if (latest && latest.timestamp) {
                online = (Date.now() - new Date(latest.timestamp).getTime()) < ONLINE_WINDOW_MS;
            }
            badge.textContent = online ? '온라인' : '오프라인';
            badge.className = 'status-badge ' + (online ? 'status-online' : 'status-offline');

            document.getElementById('curCpu').textContent =
                latest ? clamp(latest.cpuUsage).toFixed(1) + '%' : '-';
            document.getElementById('curRam').textContent =
                latest ? clamp(latest.ramUsage).toFixed(1) + '%' : '-';
            document.getElementById('curGpu').textContent =
                latest ? clamp(latest.gpuUsage).toFixed(1) + '%' : '-';
        }

        function updateCharts(telemetry) {
            // DESC → 시간순(오래된→최신)으로 뒤집어 라벨/데이터 구성
            const rev = [...telemetry].reverse();
            const labels = rev.map(t => new Date(t.timestamp).toLocaleTimeString());

            if (mainChart) mainChart.destroy();
            if (gpuChart) gpuChart.destroy();

            const ctxMain = document.getElementById('mainChart').getContext('2d');
            mainChart = new Chart(ctxMain, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        { label: 'CPU (%)', data: rev.map(t => t.cpuUsage), borderColor: '#ef4444', tension: 0.3, fill: false },
                        { label: 'RAM (%)', data: rev.map(t => t.ramUsage), borderColor: '#3b82f6', tension: 0.3, fill: false }
                    ]
                },
                options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
            });

            const ctxGpu = document.getElementById('gpuChart').getContext('2d');
            gpuChart = new Chart(ctxGpu, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{ label: 'GPU Usage (%)', data: rev.map(t => t.gpuUsage), borderColor: '#f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.1)', tension: 0.3, fill: true }]
                },
                options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
            });
        }

        function updateHistory(history) {
            const body = document.getElementById('historyBody');
            const empty = document.getElementById('historyEmpty');
            body.textContent = '';

            if (!history || history.length === 0) {
                empty.textContent = '종료 기록 없음';
                empty.style.display = 'block';
                return;
            }
            empty.style.display = 'none';
            history.forEach(function (h) {
                const tr = document.createElement('tr');
                const tdName = document.createElement('td');
                tdName.textContent = h.processName;
                const tdTime = document.createElement('td');
                tdTime.textContent = h.timestamp ? new Date(h.timestamp).toLocaleString() : '-';
                tr.appendChild(tdName);
                tr.appendChild(tdTime);
                body.appendChild(tr);
            });
        }

        function updateExceptions(exceptions) {
            const list = document.getElementById('excList');
            const empty = document.getElementById('excEmpty');
            list.textContent = '';

            if (!exceptions || exceptions.length === 0) {
                empty.textContent = '등록된 예외 없음';
                empty.style.display = 'block';
                return;
            }
            empty.style.display = 'none';
            exceptions.forEach(function (name) {
                const li = document.createElement('li');
                li.textContent = name;
                list.appendChild(li);
            });
        }

        async function fetchData() {
            try {
                const data = await apiGet('/api/v1/admin/machines/' + encodeURIComponent(machineId));
                if (!data) return;  // 인증 만료 → 리다이렉트 처리됨
                if (data.__notfound) { showNotFound(); return; }
                updateHead(data);
                updateCharts(data.telemetry);
                updateHistory(data.optimizationHistory);
                updateExceptions(data.exceptions);
                document.getElementById('lastUpdate').textContent =
                    '마지막 갱신: ' + new Date().toLocaleTimeString();
            } catch (e) {
                console.error('데이터 로드 실패:', e);
            }
        }

        fetchData();
        setInterval(fetchData, 10000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content.replace("__MACHINE_ID__", safe_id))
