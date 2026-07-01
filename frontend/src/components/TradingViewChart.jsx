import React, { useEffect, useRef } from 'react';
import { createChart, CandlestickSeries, LineSeries, HistogramSeries } from 'lightweight-charts';

export default function TradingViewChart({ data, showBands = false, showSMA = false }) {
  const chartContainerRef = useRef();
  const rsiContainerRef = useRef();

  useEffect(() => {
    if (!chartContainerRef.current || !rsiContainerRef.current || !data || data.length === 0) return;

    // 1. Initialize Main Price Chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      layout: {
        background: { color: '#161c28' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.03)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.03)' },
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.06)',
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.06)',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // 2. Initialize Linked RSI Chart
    const rsiChart = createChart(rsiContainerRef.current, {
      width: rsiContainerRef.current.clientWidth,
      height: rsiContainerRef.current.clientHeight,
      layout: {
        background: { color: '#161c28' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.03)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.03)' },
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.06)',
        visible: true,
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.06)',
        visible: false, // hide time scale on sub-chart since they align
      },
    });

    // Link timescales for synchronous zooming/scrolling
    chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      rsiChart.timeScale().setVisibleLogicalRange(range);
    });
    rsiChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      chart.timeScale().setVisibleLogicalRange(range);
    });

    // 3. Setup Series
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#10b981',
      priceFormat: { type: 'volume' },
      priceScaleId: '', 
    });

    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    // Default Trend EMAs
    const ema200Series = chart.addSeries(LineSeries, {
      color: '#00e5ff',
      lineWidth: 1.5,
      priceLineVisible: false,
    });

    const ema50Series = chart.addSeries(LineSeries, {
      color: '#ef5350',
      lineWidth: 1.5,
      priceLineVisible: false,
    });

    // Optional Indicator Lines
    let smaSeries = null;
    if (showSMA) {
      smaSeries = chart.addSeries(LineSeries, {
        color: '#eab308', // yellow
        lineWidth: 1.5,
        priceLineVisible: false,
      });
    }

    let bbUpperSeries = null;
    let bbLowerSeries = null;
    if (showBands) {
      bbUpperSeries = chart.addSeries(LineSeries, {
        color: 'rgba(16, 185, 129, 0.4)',
        lineWidth: 1.0,
        priceLineVisible: false,
      });
      bbLowerSeries = chart.addSeries(LineSeries, {
        color: 'rgba(239, 68, 68, 0.4)',
        lineWidth: 1.0,
        priceLineVisible: false,
      });
    }

    // 4. RSI Indicators & Guides
    const rsiSeries = rsiChart.addSeries(LineSeries, {
      color: '#a855f7', // purple
      lineWidth: 1.5,
      priceLineVisible: false,
    });

    const rsiOverboughtLine = rsiChart.addSeries(LineSeries, {
      color: 'rgba(239, 68, 68, 0.25)',
      lineWidth: 1.0,
      priceLineVisible: false,
    });

    const rsiOversoldLine = rsiChart.addSeries(LineSeries, {
      color: 'rgba(16, 185, 129, 0.25)',
      lineWidth: 1.0,
      priceLineVisible: false,
    });

    // 5. Calculations
    const candles = [];
    const volumes = [];
    const ema200Line = [];
    const ema50Line = [];
    
    // SMA 50 calculation parameters
    const k50 = 2 / (50 + 1);
    let prevEma50 = null;

    // SMA 20
    const sma20Values = [];
    // Bollinger Bands
    const bbUpperValues = [];
    const bbLowerValues = [];
    // RSI 14
    const rsiValues = [];
    let avgGain = 0;
    let avgLoss = 0;

    data.forEach((d, idx) => {
      candles.push({
        time: d.time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      });

      volumes.push({
        time: d.time,
        value: d.volume,
        color: d.close >= d.open ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)',
      });

      ema200Line.push({
        time: d.time,
        value: d.ema200 || d.close,
      });

      // EMA 50
      const closeVal = d.close;
      let curEma50 = closeVal;
      if (idx > 0) {
        curEma50 = closeVal * k50 + prevEma50 * (1 - k50);
      }
      prevEma50 = curEma50;
      ema50Line.push({
        time: d.time,
        value: Number(curEma50.toFixed(2)),
      });

      // Calculate SMA 20 locally
      if (idx < 19) {
        sma20Values.push({ time: d.time, value: d.close });
        bbUpperValues.push({ time: d.time, value: d.close });
        bbLowerValues.push({ time: d.time, value: d.close });
      } else {
        let sum = 0;
        for (let j = 0; j < 20; j++) {
          sum += data[idx - j].close;
        }
        const mean = sum / 20;
        sma20Values.push({ time: d.time, value: Number(mean.toFixed(2)) });

        // BB Bands
        let varianceSum = 0;
        for (let j = 0; j < 20; j++) {
          varianceSum += Math.pow(data[idx - j].close - mean, 2);
        }
        const stdDev = Math.sqrt(varianceSum / 20);
        bbUpperValues.push({ time: d.time, value: Number((mean + stdDev * 2).toFixed(2)) });
        bbLowerValues.push({ time: d.time, value: Number((mean - stdDev * 2).toFixed(2)) });
      }

      // Calculate RSI 14 locally
      if (idx === 0) {
        rsiValues.push({ time: d.time, value: 50.0 });
      } else {
        const diff = data[idx].close - data[idx - 1].close;
        const gain = diff > 0 ? diff : 0.0;
        const loss = diff < 0 ? -diff : 0.0;

        if (idx < 14) {
          avgGain += gain;
          avgLoss += loss;
          rsiValues.push({ time: d.time, value: 50.0 });
          if (idx === 13) {
            avgGain /= 14.0;
            avgLoss /= 14.0;
          }
        } else {
          avgGain = (avgGain * 13.0 + gain) / 14.0;
          avgLoss = (avgLoss * 13.0 + loss) / 14.0;
          const rs = avgLoss === 0.0 ? 100.0 : avgGain / avgLoss;
          const rsi = avgLoss === 0.0 ? 100.0 : 100.0 - (100.0 / (1.0 + rs));
          rsiValues.push({ time: d.time, value: Number(rsi.toFixed(2)) });
        }
      }
    });

    // Guides
    const overboughtGuide = data.map(d => ({ time: d.time, value: 70 }));
    const oversoldGuide = data.map(d => ({ time: d.time, value: 30 }));

    // Populate data
    candlestickSeries.setData(candles);
    volumeSeries.setData(volumes);
    ema200Series.setData(ema200Line);
    ema50Series.setData(ema50Line);
    
    if (showSMA && smaSeries) {
      smaSeries.setData(sma20Values);
    }
    if (showBands && bbUpperSeries && bbLowerSeries) {
      bbUpperSeries.setData(bbUpperValues);
      bbLowerSeries.setData(bbLowerValues);
    }

    rsiSeries.setData(rsiValues);
    rsiOverboughtLine.setData(overboughtGuide);
    rsiOversoldLine.setData(oversoldGuide);

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current && rsiContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
        rsiChart.applyOptions({
          width: rsiContainerRef.current.clientWidth,
          height: rsiContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      rsiChart.remove();
    };
  }, [data, showBands, showSMA]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', gap: '4px' }}>
      <div ref={chartContainerRef} style={{ flex: 3, width: '100%', position: 'relative' }} />
      <div ref={rsiContainerRef} style={{ flex: 1, width: '100%', position: 'relative', borderTop: '1px solid rgba(255,255,255,0.04)' }} />
    </div>
  );
}
