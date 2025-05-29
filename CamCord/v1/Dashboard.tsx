<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cyberpunk Dashboard</title>
    <link rel="stylesheet" href="style.css">
    <link rel="stylesheet" href="cyberpunk_styles.css">
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="dashboard-container">
        <header>
            <h1>Real-Time Analytics Dashboard</h1>
            <nav>
                <button data-tab="overview" class="tab-btn active">Overview</button>
                <button data-tab="metrics" class="tab-btn">Metrics</button>
                <button data-tab="logs" class="tab-btn">Logs</button>
            </nav>
        </header>
        <main>
            <section id="overview" class="tab-content active">
                <div class="chart-group">
                    <canvas id="chartA"></canvas>
                    <canvas id="chartB"></canvas>
                </div>
            </section>
            <section id="metrics" class="tab-content">
                <div class="chart-group">
                    <canvas id="chartC"></canvas>
                    <canvas id="chartD"></canvas>
                    <canvas id="chartE"></canvas>
                </div>
            </section>
            <section id="logs" class="tab-content">
                <h2>Log Output</h2>
                <div id="log-output" class="log-box"></div>
            </section>
        </main>
    </div>
    <script src="script.js"></script>
</body>
</html>