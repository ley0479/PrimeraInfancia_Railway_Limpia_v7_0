(function () {
    'use strict';

    function css(name, fallback) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
    }

    function updateCharts() {
        const palette = {
            text: css('--pi-text', '#f8fafc'), grid: css('--pi-border', '#334155'),
            primary: css('--pi-primary', '#2563eb'), success: css('--pi-success', '#10b981'),
            warning: css('--pi-warning', '#f59e0b'), danger: css('--pi-danger', '#ef4444')
        };
        const charts = window.Chart?.instances;
        if (!charts) return;
        const instances = typeof charts.values === 'function' ? [...charts.values()] : Object.values(charts);
        instances.forEach(chart => {
            if (!chart?.options) return;
            chart.options.color = palette.text;
            const scales = chart.options.scales || {};
            Object.values(scales).forEach(scale => {
                if (!scale) return;
                scale.grid = { ...(scale.grid || {}), color: palette.grid };
                scale.ticks = { ...(scale.ticks || {}), color: palette.text };
            });
            chart.update?.('none');
        });
    }

    window.addEventListener('app:theme-changed', updateCharts);
    window.ThemeChartAdapter = Object.freeze({ update: updateCharts });
})();
