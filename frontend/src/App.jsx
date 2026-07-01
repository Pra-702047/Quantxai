import React, { useState, useEffect, useRef } from 'react';
import TradingViewChart from './components/TradingViewChart';

const API_BASE = 'https://quantxai-b4uh-git-main-prathmesh-uttarwars-projects.vercel.app/api';
const WATCHLIST = [
  'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 
  'BHARTIARTL.NS', 'SBIN.NS', 'LICI.NS', 'ITC.NS', 'HINDUNILVR.NS', 
  'LT.NS', 'BAJFINANCE.NS', 'TATASTEEL.NS', 'MARUTI.NS', 'KOTAKBANK.NS', 
  'AXISBANK.NS', 'M&M.NS', 'SUNPHARMA.NS', 'ADANIENT.NS', 'ADANIPORTS.NS', 
  'HCLTECH.NS', 'NTPC.NS', 'POWERGRID.NS', 'TITAN.NS', 'ULTRACEMCO.NS'
];

export default function App() {
  const [symbol, setSymbol] = useState('RELIANCE.NS');
  const [timeframe, setTimeframe] = useState('5m');
  const [chartData, setChartData] = useState([]);
  const [signalData, setSignalData] = useState(null);
  const [scannerData, setScannerData] = useState(null);
  const [portfolio, setPortfolio] = useState(null);

  // Form Inputs
  const [entryPrice, setEntryPrice] = useState(1450);
  const [stopLoss, setStopLoss] = useState(1430);
  const [target, setTarget] = useState(1490);
  const [quantity, setQuantity] = useState(50);
  const [riskPercent, setRiskPercent] = useState(0.01); // State-driven risk level (1%)
  const [domData, setDomData] = useState(null);
  const [timeSales, setTimeSales] = useState([]);
  const [backtestResults, setBacktestResults] = useState(null);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const [backtestTab, setBacktestTab] = useState("equity");
  const [backtestStrategy, setBacktestStrategy] = useState("AI");
  const [backtestPeriod, setBacktestPeriod] = useState("60d");
  const [backtestInterval, setBacktestInterval] = useState("15m");
  const [compareResults, setCompareResults] = useState(null);
  const [isComparing, setIsComparing] = useState(false);
  const [bypassMarketCheck, setBypassMarketCheck] = useState(false);
  const [newsTab, setNewsTab] = useState("stock");
  const [goldData, setGoldData] = useState(null);
  const [show2FA, setShow2FA] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [otpError, setOtpError] = useState("");

  // User Authentication States
  const [currentUser, setCurrentUser] = useState({ username: "Guest", is_authenticated: false });
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authTab, setAuthTab] = useState("login");
  const [authUsername, setAuthUsername] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authEmail, setAuthEmail] = useState("");
  const [authConfirmPassword, setAuthConfirmPassword] = useState("");
  const [authError, setAuthError] = useState("");

  // Live indices mock values that tick slightly to feel alive
  const [nifty, setNifty] = useState({ price: 24072.10, change: '+68.50', pct: '+0.28%' });
  const [banknifty, setBanknifty] = useState({ price: 52003.35, change: '-95.40', pct: '-0.18%' });

  // Custom fetch function with Authorization header injection
  const fetchWithAuth = async (url, options = {}) => {
    const token = localStorage.getItem("quantx_session_token");
    const headers = {
      ...options.headers,
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return fetch(url, { ...options, headers });
  };

  // Alert Configurations States
  const [telegramToken, setTelegramToken] = useState("");
  const [telegramChatId, setTelegramChatId] = useState("");
  const [alertsEnabled, setAlertsEnabled] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [settingsMessage, setSettingsMessage] = useState("");
  const [settingsTab, setSettingsTab] = useState("alerts");
  const [adminStats, setAdminStats] = useState(null);

  // Chart indicator settings
  const [showSMA, setShowSMA] = useState(false);
  const [showBands, setShowBands] = useState(false);

  const prevLastTradeTimestampRef = useRef(0);

  const speakAlert = (text) => {
    try {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95;
        utterance.pitch = 1.05;
        window.speechSynthesis.speak(utterance);
      }
    } catch (e) {
      console.warn("Speech synthesis failed:", e);
    }
  };

  const playStopLossSound = () => {
    try {
      const audio = new Audio("https://assets.mixkit.co/active_storage/sfx/2869/2869-84.wav");
      audio.volume = 0.8;
      audio.play();
    } catch (e) {
      console.warn("Audio alert blocked by autoplay policies:", e);
    }
  };

  // Broker Configuration States
  const [brokerMode, setBrokerMode] = useState("PAPER");
  const [zerodhaApiKey, setZerodhaApiKey] = useState("");
  const [zerodhaApiSecret, setZerodhaApiSecret] = useState("");

  const fetchCurrentUser = async () => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/auth/me`);
      if (res.ok) {
        const json = await res.json();
        setCurrentUser(json);
        if (json.is_authenticated) {
          fetchAlertsConfig();
          fetchBrokerConfig();
        }
      }
    } catch (e) {
      console.error("Auth state fetch failed:", e);
    }
  };

  const fetchBrokerConfig = async () => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/broker/config`);
      if (res.ok) {
        const json = await res.json();
        setBrokerMode(json.broker_mode);
        setZerodhaApiKey(json.zerodha_api_key);
        setZerodhaApiSecret(json.zerodha_api_secret);
      }
    } catch (e) {
      console.error("Broker config fetch failed:", e);
    }
  };

  const fetchAlertsConfig = async () => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/alerts/config`);
      if (res.ok) {
        const json = await res.json();
        setTelegramToken(json.telegram_token);
        setTelegramChatId(json.telegram_chat_id);
        setAlertsEnabled(json.enabled);
      }
    } catch (e) {
      console.error("Alert config fetch failed:", e);
    }
  };

  useEffect(() => {
    if (portfolio?.trade_history && portfolio.trade_history.length > 0) {
      const latestTrade = portfolio.trade_history[0];
      if (prevLastTradeTimestampRef.current > 0 && latestTrade.timestamp > prevLastTradeTimestampRef.current) {
        if (latestTrade.reason === 'STOP_LOSS') {
          playStopLossSound();
          speakAlert("Stop loss hit, Boss!");
        } else if (latestTrade.reason === 'TAKE_PROFIT') {
          speakAlert("Profit booked, Boss!");
        }
      }
      prevLastTradeTimestampRef.current = latestTrade.timestamp;
    }
  }, [portfolio]);

  const fetchAdminStats = async () => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/admin/stats`);
      if (res.ok) {
        const json = await res.json();
        setAdminStats(json);
      }
    } catch (e) {
      console.error("Admin stats fetch failed:", e);
    }
  };

  useEffect(() => {
    if (backtestTab === 'admin') {
      fetchAdminStats();
    }
  }, [backtestTab]);

  // Fetch chart and signal data
  const fetchSymbolData = async (currentSymbol) => {
    try {
      // Signal
      const sigRes = await fetch(`${API_BASE}/signal?symbol=${currentSymbol}`);
      const sigJson = await sigRes.json();
      setSignalData(sigJson);

      // Pre-fill form from AI suggested values
      setEntryPrice(sigJson.entry);
      setStopLoss(sigJson.stop_loss);
      setTarget(sigJson.target);
      setQuantity(sigJson.quantity);

      // Chart Candles
      const chartRes = await fetch(`${API_BASE}/chart-data?symbol=${currentSymbol}`);
      const chartJson = await chartRes.json();
      setChartData(chartJson);
    } catch (e) {
      console.error("Error fetching symbol details:", e);
    }
  };

  // Fetch scanner and portfolio values
  const fetchGlobals = async () => {
    try {
      const portRes = await fetchWithAuth(`${API_BASE}/portfolio`);
      const portJson = await portRes.json();
      setPortfolio(portJson);

      const scanRes = await fetch(`${API_BASE}/scanner`);
      const scanJson = await scanRes.json();
      setScannerData(scanJson);
    } catch (e) {
      console.error("Globals fetch failed:", e);
    }
  };

  // Re-calculate quantity locally when risk profile or stop loss changes, capped by available cash
  useEffect(() => {
    if (portfolio && signalData && entryPrice > 0) {
      const balance = portfolio.cash;
      const slDistance = Math.abs(entryPrice - stopLoss);
      if (slDistance > 0) {
        let calculatedQty = Math.max(1, Math.round((balance * riskPercent) / slDistance));
        // Cap by maximum available cash (no leverage)
        const maxCashQty = Math.floor(balance / entryPrice);
        if (calculatedQty > maxCashQty) {
          calculatedQty = maxCashQty;
        }
        setQuantity(calculatedQty);
      }
    }
  }, [riskPercent, stopLoss, entryPrice, portfolio, signalData]);

  const fetchGoldData = async () => {
    try {
      const res = await fetch(`${API_BASE}/gold-advisor`);
      const json = await res.json();
      setGoldData(json);
    } catch (e) {
      console.error("Gold advisor fetch failed:", e);
    }
  };

  useEffect(() => {
    if (newsTab === "gold") {
      fetchGoldData();
    }
  }, [newsTab, symbol]);

  useEffect(() => {
    fetchSymbolData(symbol);
  }, [symbol, timeframe]);

  useEffect(() => {
    const wsUrl = API_BASE.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws';
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'TICK') {
          if (payload.portfolio) setPortfolio(payload.portfolio);
          if (payload.dom) setDomData(payload.dom);
          if (payload.time_sales) setTimeSales(payload.time_sales);
        }
      } catch (err) {
        console.error("WS message parse failed:", err);
      }
    };
    
    let pollInterval = null;
    
    ws.onclose = () => {
      console.log("WebSocket connection closed. Falling back to HTTP polling.");
      pollInterval = setInterval(() => {
        fetchGlobals();
      }, 3500);
    };

    ws.onerror = () => {
      console.log("WebSocket connection error. Falling back to HTTP polling.");
      if (!pollInterval) {
        pollInterval = setInterval(() => {
          fetchGlobals();
        }, 3500);
      }
    };
    
    return () => {
      ws.close();
      if (pollInterval) clearInterval(pollInterval);
    };
  }, []);

  useEffect(() => {
    fetchCurrentUser();
    fetchGlobals();
    const interval = setInterval(() => {
      // Tick indices slightly
      setNifty(prev => {
        const change = (Math.random() - 0.5) * 5;
        const newPrice = prev.price + change;
        return {
          price: parseFloat(newPrice.toFixed(2)),
          change: (newPrice - 24000) > 0 ? `+${(newPrice - 24000).toFixed(2)}` : `${(newPrice - 24000).toFixed(2)}`,
          pct: `${(((newPrice - 24000)/24000)*100).toFixed(2)}%`
        };
      });
      setBanknifty(prev => {
        const change = (Math.random() - 0.5) * 10;
        const newPrice = prev.price + change;
        return {
          price: parseFloat(newPrice.toFixed(2)),
          change: (newPrice - 52000) > 0 ? `+${(newPrice - 52000).toFixed(2)}` : `${(newPrice - 52000).toFixed(2)}`,
          pct: `${(((newPrice - 52000)/52000)*100).toFixed(2)}%`
        };
      });
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  // Execute manual trade
  const handleStartTrade = async (actionType) => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/trade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: symbol,
          action: actionType,
          entry_price: parseFloat(entryPrice),
          quantity: parseInt(quantity),
          stop_loss: parseFloat(stopLoss),
          target: parseFloat(target)
        })
      });
      const resJson = await response.json();
      if (!response.ok) {
        alert(resJson.detail || "Trade failed");
        return;
      }
      fetchGlobals();
    } catch (e) {
      console.error(e);
    }
  };

  // Close trade manually
  const handleCloseTrade = async (targetSymbol) => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/trade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: targetSymbol,
          action: 'CLOSE'
        })
      });
      const resJson = await response.json();
      if (!response.ok) {
        alert(resJson.detail || "Close failed");
        return;
      }
      fetchGlobals();
    } catch (e) {
      console.error(e);
    }
  };

  // Check if position is active for current symbol
  const activePosition = portfolio?.open_positions?.find(p => p.symbol === symbol);

  // Render SVG Sparkline Equity Curve
  const drawEquityCurve = () => {
    const curve = portfolio?.equity_curve || [100000, 100000];
    if (curve.length === 0) return null;
    
    const min = Math.min(...curve) * 0.995;
    const max = Math.max(...curve) * 1.005;
    const range = max - min || 1;
    
    const width = 300;
    const height = 100;
    const points = curve.map((val, idx) => {
      const x = (idx / (curve.length - 1 || 1)) * width;
      const y = height - ((val - min) / range) * height;
      return `${x},${y}`;
    });
    
    const pathD = `M ${points.join(' L ')}`;
    const areaD = `${pathD} L ${width},${height} L 0,${height} Z`;
    
    return (
      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.25"/>
            <stop offset="100%" stopColor="#10b981" stopOpacity="0.0"/>
          </linearGradient>
        </defs>
        <path d={areaD} fill="url(#equityGrad)" />
        <path d={pathD} fill="none" stroke="#10b981" strokeWidth="2.5" style={{ filter: 'drop-shadow(0px 0px 4px rgba(16, 185, 129, 0.4))' }} />
      </svg>
    );
  };

  const isMarketActiveTime = () => {
    const now = new Date();
    const day = now.getDay();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    
    if (day === 0 || day === 6) return false;
    
    const timeInMinutes = hours * 60 + minutes;
    const startMinutes = 8 * 60 + 15; // 8:15 AM
    const endMinutes = 18 * 60 + 30;  // 6:30 PM
    
    return timeInMinutes >= startMinutes && timeInMinutes <= endMinutes;
  };

  return (
    <div className="app-container">
      {/* Header Bar */}
      <header className="app-header">
        <div className="header-left">
          <div className="logo-icon">⚡</div>
          <div className="logo-text">QuantX <span>AI Trading Terminal</span></div>
        </div>
        <div className="header-indices">
          {signalData?.global_indices ? (
            <>
              <div className="index-item">
                <span className="index-name">S&P 500</span>
                <span className="index-value" style={{ color: signalData.global_indices.SP500.change >= 0 ? '#10b981' : '#ef4444' }}>
                  {signalData.global_indices.SP500.price}
                </span>
                <span className={`index-change ${signalData.global_indices.SP500.change >= 0 ? 'up' : 'down'}`}>
                  {signalData.global_indices.SP500.change >= 0 ? '▲' : '▼'} {signalData.global_indices.SP500.change}%
                </span>
              </div>
              <div className="index-item">
                <span className="index-name">NASDAQ</span>
                <span className="index-value" style={{ color: signalData.global_indices.NASDAQ.change >= 0 ? '#10b981' : '#ef4444' }}>
                  {signalData.global_indices.NASDAQ.price}
                </span>
                <span className={`index-change ${signalData.global_indices.NASDAQ.change >= 0 ? 'up' : 'down'}`}>
                  {signalData.global_indices.NASDAQ.change >= 0 ? '▲' : '▼'} {signalData.global_indices.NASDAQ.change}%
                </span>
              </div>
            </>
          ) : (
            <>
              <div className="index-item">
                <span className="index-name">NIFTY</span>
                <span className="index-value" style={{ color: nifty.change.startsWith('+') ? '#10b981' : '#ef4444' }}>
                  {nifty.price}
                </span>
                <span className={`index-change ${nifty.change.startsWith('+') ? 'up' : 'down'}`}>
                  ▲ {nifty.change} ({nifty.pct})
                </span>
              </div>
              <div className="index-item">
                <span className="index-name">BANKMIFTY</span>
                <span className="index-value" style={{ color: banknifty.change.startsWith('+') ? '#10b981' : '#ef4444' }}>
                  {banknifty.price}
                </span>
                <span className={`index-change ${banknifty.change.startsWith('+') ? 'up' : 'down'}`}>
                  ▲ {banknifty.change} ({banknifty.pct})
                </span>
              </div>
            </>
          )}
        </div>
        {/* Profile and control icons on right */}
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', color: '#9ca3af' }}>
          <div className="icon-btn" style={{ cursor: 'pointer' }}>🔍</div>
          <div className="icon-btn" style={{ cursor: 'pointer' }}>🔔</div>
          <div className="icon-btn" style={{ cursor: 'pointer' }} onClick={() => { 
            if (currentUser.is_authenticated) { 
              setSettingsMessage(""); 
              setShowSettingsModal(true); 
            } else { 
              alert("Please login first to configure notification alerts."); 
            } 
          }}>⚙️</div>
          {currentUser.is_authenticated ? (
            <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', color: '#00e5ff', fontWeight: 600 }}>👤 {currentUser.username}</span>
              <button 
                onClick={async () => {
                  try {
                    await fetchWithAuth(`${API_BASE}/auth/logout`, { method: 'POST' });
                    localStorage.removeItem("quantx_session_token");
                    setCurrentUser({ username: "Guest", is_authenticated: false });
                    fetchGlobals();
                  } catch (e) {
                    console.error("Logout failed:", e);
                  }
                }}
                style={{
                  background: 'rgba(239,68,68,0.15)',
                  color: '#ef4444',
                  border: '1px solid rgba(239,68,68,0.25)',
                  borderRadius: '4px',
                  padding: '0.2rem 0.5rem',
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                Logout
              </button>
            </div>
          ) : (
            <button 
              onClick={() => {
                setAuthError("");
                setShowAuthModal(true);
              }}
              style={{
                background: 'rgba(0,229,255,0.12)',
                color: '#00e5ff',
                border: '1px solid rgba(0,229,255,0.25)',
                borderRadius: '4px',
                padding: '0.3rem 0.7rem',
                fontSize: '0.7rem',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 0 10px rgba(0,229,255,0.1)'
              }}
            >
              Login / Register
            </button>
          )}
        </div>
      </header>

      {/* Daily Loss Circuit Breaker Warning Banner */}
      {portfolio?.circuit_breaker_active && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          borderRadius: '4px',
          padding: '0.6rem 1rem',
          margin: '0.5rem 1rem 0 1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: '0 0 10px rgba(239, 68, 68, 0.1)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#f87171', fontSize: '0.8rem', fontWeight: 600 }}>
            <span>🚨</span>
            <span>DAILY LOSS CIRCUIT BREAKER ACTIVE (-1.5% limit hit). TRADING IS PAUSED.</span>
          </div>
          <button
            onClick={async () => {
              try {
                const res = await fetchWithAuth(`${API_BASE}/portfolio/reset-circuit`, { method: 'POST' });
                const json = await res.json();
                if (json.status === 'SUCCESS') {
                  fetchGlobals();
                }
              } catch (e) {
                console.error("Reset circuit failed:", e);
              }
            }}
            style={{
              background: '#ef4444',
              color: '#fff',
              border: 'none',
              borderRadius: '3px',
              padding: '0.2rem 0.5rem',
              fontSize: '0.7rem',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            Reset Breaker
          </button>
        </div>
      )}

      {/* Main Grid or Market Closed standby */}
      {!isMarketActiveTime() && !bypassMarketCheck ? (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '65vh',
          margin: '2rem 1.5rem',
          background: 'rgba(22, 28, 40, 0.4)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          borderRadius: '12px',
          padding: '4rem 2rem',
          textAlign: 'center',
          backdropFilter: 'blur(20px)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
        }}>
          {show2FA ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              width: '100%',
              maxWidth: '400px',
              padding: '2rem',
              background: '#0b0f19',
              border: '1px solid rgba(0, 229, 255, 0.25)',
              borderRadius: '10px',
              boxShadow: '0 0 25px rgba(0, 229, 255, 0.15)',
              textAlign: 'center'
            }}>
              <span style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🔐</span>
              <h3 style={{ color: '#fff', fontSize: '1.2rem', fontWeight: 700, marginBottom: '0.4rem', fontFamily: 'Outfit' }}>Developer 2FA Gateway</h3>
              <p style={{ color: '#9ca3af', fontSize: '0.75rem', lineHeight: '1.4', marginBottom: '1.2rem' }}>
                Scan this QR code with Google Authenticator, then enter the 6-digit OTP code below.
              </p>
              
              <div style={{ background: '#fff', padding: '0.5rem', borderRadius: '6px', marginBottom: '0.8rem', display: 'inline-block' }}>
                <img 
                  src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=otpauth://totp/QuantX:Prathmesh%3Fsecret%3DNYNXP43JMXSZXEHB%26issuer%3DQuantX" 
                  alt="2FA QR Code" 
                  style={{ display: 'block', width: '150px', height: '150px' }} 
                />
              </div>
              
              <div style={{ fontSize: '0.65rem', color: '#6b7280', fontFamily: 'monospace', marginBottom: '1rem', background: 'rgba(255,255,255,0.01)', padding: '0.3rem 0.5rem', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.03)' }}>
                Key: NYNXP43JMXSZXEHB
              </div>

              <input 
                type="text" 
                maxLength="6"
                placeholder="0 0 0 0 0 0" 
                value={otpCode}
                onChange={(e) => {
                  setOtpCode(e.target.value.replace(/\D/g, ''));
                  setOtpError("");
                }}
                style={{
                  width: '100%',
                  background: '#111827',
                  border: '1px solid rgba(255,255,255,0.08)',
                  color: '#00e5ff',
                  borderRadius: '6px',
                  padding: '0.5rem',
                  fontSize: '1.2rem',
                  letterSpacing: '0.2rem',
                  textAlign: 'center',
                  fontWeight: 700,
                  marginBottom: '1rem',
                  outline: 'none'
                }}
              />

              {otpError && (
                <div style={{ color: '#ef4444', fontSize: '0.75rem', fontWeight: 600, marginBottom: '1rem' }}>
                  ❌ {otpError}
                </div>
              )}

              <div style={{ display: 'flex', gap: '0.5rem', width: '100%' }}>
                <button
                  onClick={() => {
                    setShow2FA(false);
                    setOtpCode("");
                    setOtpError("");
                  }}
                  style={{
                    flex: 1,
                    background: 'rgba(255,255,255,0.03)',
                    color: '#9ca3af',
                    border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: '4px',
                    padding: '0.5rem',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    if (otpCode.length !== 6) {
                      setOtpError("Code must be 6 digits.");
                      return;
                    }
                    try {
                      const res = await fetch(`${API_BASE}/developer/verify`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ code: otpCode })
                      });
                      const json = await res.json();
                      if (json.status === 'SUCCESS') {
                        setBypassMarketCheck(true);
                        setShow2FA(false);
                        setOtpCode("");
                        setOtpError("");
                      } else {
                        setOtpError(json.message || "Invalid OTP code.");
                      }
                    } catch (e) {
                      setOtpError("Connection error.");
                    }
                  }}
                  style={{
                    flex: 1,
                    background: 'rgba(0, 229, 255, 0.15)',
                    color: '#00e5ff',
                    border: '1px solid rgba(0, 229, 255, 0.25)',
                    borderRadius: '4px',
                    padding: '0.5rem',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  Verify Code
                </button>
              </div>
            </div>
          ) : (
            <>
              <span style={{ fontSize: '4rem', marginBottom: '1.5rem', filter: 'drop-shadow(0 0 10px rgba(0, 229, 255, 0.3))' }}>🔒</span>
              <h2 style={{ fontFamily: 'Outfit', color: '#fff', fontSize: '1.8rem', fontWeight: 700, marginBottom: '0.75rem' }}>QuantX AI Terminal is Standby</h2>
              <p style={{ color: '#9ca3af', fontSize: '0.9rem', maxWidth: '520px', lineHeight: '1.6', marginBottom: '1.8rem' }}>
                Indian stock markets are currently closed. Live WebSocket data feeds and confirmation scanner regimes run from <strong style={{ color: '#00e5ff' }}>08:15 AM to 06:30 PM</strong> (Monday to Friday).
              </p>
              <button 
                onClick={() => setShow2FA(true)}
                style={{
                  background: 'rgba(0, 229, 255, 0.1)',
                  color: '#00e5ff',
                  border: '1px solid rgba(0, 229, 255, 0.25)',
                  borderRadius: '6px',
                  padding: '0.65rem 1.4rem',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 0 10px rgba(0, 229, 255, 0.15)',
                  transition: 'all 0.2s'
                }}
                onMouseOver={(e) => {
                  e.target.style.background = 'rgba(0, 229, 255, 0.2)';
                  e.target.style.boxShadow = '0 0 15px rgba(0, 229, 255, 0.3)';
                }}
                onMouseOut={(e) => {
                  e.target.style.background = 'rgba(0, 229, 255, 0.1)';
                  e.target.style.boxShadow = '0 0 10px rgba(0, 229, 255, 0.15)';
                }}
              >
                🛠️ Developer Mode (Bypass Guard)
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="dashboard-grid">
        <div className="main-column">
          {/* Chart Panel */}
          <div className="panel">
            <div className="chart-controls">
              <div className="stock-selector">
                <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
                  {WATCHLIST.map(w => (
                    <option key={w} value={w}>{w.replace('.NS', '')}</option>
                  ))}
                </select>
              </div>
              <div className="timeframe-buttons">
                {['5m', '15m', '1h'].map(tf => (
                  <button
                    key={tf}
                    className={`timeframe-btn ${timeframe === tf ? 'active' : ''}`}
                    onClick={() => setTimeframe(tf)}
                  >
                    {tf}
                  </button>
                ))}
              </div>
              <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', marginLeft: 'auto' }}>
                <button
                  onClick={() => setShowSMA(!showSMA)}
                  style={{
                    background: showSMA ? 'rgba(234, 179, 8, 0.15)' : 'rgba(255,255,255,0.02)',
                    color: showSMA ? '#eab308' : '#9ca3af',
                    border: '1px solid ' + (showSMA ? 'rgba(234, 179, 8, 0.3)' : 'rgba(255,255,255,0.06)'),
                    borderRadius: '4px',
                    padding: '0.15rem 0.45rem',
                    fontSize: '0.65rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  📈 SMA 20
                </button>
                <button
                  onClick={() => setShowBands(!showBands)}
                  style={{
                    background: showBands ? 'rgba(16, 185, 129, 0.15)' : 'rgba(255,255,255,0.02)',
                    color: showBands ? '#10b981' : '#9ca3af',
                    border: '1px solid ' + (showBands ? 'rgba(16, 185, 129, 0.3)' : 'rgba(255,255,255,0.06)'),
                    borderRadius: '4px',
                    padding: '0.15rem 0.45rem',
                    fontSize: '0.65rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  📊 BB Bands
                </button>
              </div>
            </div>
            <div className="chart-container">
              {chartData.length > 0 ? (
                <TradingViewChart data={chartData} showSMA={showSMA} showBands={showBands} />
              ) : (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  Loading market data...
                </div>
              )}
            </div>
          </div>

          {/* Analytics Panel */}
          <div className="panel" style={{ minHeight: '340px' }}>
            <div className="panel-header">
              <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
                <span className="panel-title" style={{ fontSize: '0.85rem', fontWeight: 700, marginRight: '0.4rem' }}>📊 Analytics</span>
                {['equity', 'backtest', 'compare', 'admin']
                  .filter(tab => tab !== 'admin' || ['prathmesh', 'admin', 'pratham', 'guest'].includes(currentUser.username?.toLowerCase()))
                  .map(tab => (
                  <button 
                    key={tab}
                    onClick={() => setBacktestTab(tab)}
                    style={{
                      background: backtestTab === tab ? 'rgba(0, 229, 255, 0.15)' : 'transparent',
                      color: backtestTab === tab ? '#00e5ff' : '#9ca3af',
                      border: 'none',
                      borderRadius: '3px',
                      padding: '0.15rem 0.4rem',
                      fontSize: '0.65rem',
                      cursor: 'pointer',
                      fontWeight: backtestTab === tab ? 600 : 400,
                      textTransform: 'capitalize'
                    }}
                  >
                    {tab === 'equity' ? 'Equity Curve' : tab === 'backtest' ? 'Backtester' : 'Compare'}
                  </button>
                ))}
              </div>
              
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button 
                  onClick={async () => {
                    if (window.confirm("Are you sure you want to reset your paper trading capital to 1 Lakh and wipe all trade history?")) {
                      try {
                        const res = await fetchWithAuth(`${API_BASE}/portfolio/reset`, { method: 'POST' });
                        const json = await res.json();
                        if (json.status === 'SUCCESS') {
                          fetchGlobals();
                        }
                      } catch (e) {
                        console.error("Reset capital failed:", e);
                      }
                    }
                  }}
                  style={{
                    background: 'rgba(239, 68, 68, 0.08)',
                    color: '#ef4444',
                    border: '1px solid rgba(239, 68, 68, 0.15)',
                    borderRadius: '4px',
                    padding: '0.15rem 0.45rem',
                    fontSize: '0.65rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  🔄 Reset Capital
                </button>
                <button 
                  onClick={async () => {
                    try {
                      const response = await fetchWithAuth(`${API_BASE}/portfolio/export`);
                      const blob = await response.blob();
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = 'trade_history.csv';
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                      window.URL.revokeObjectURL(url);
                    } catch (e) {
                      console.error("Export failed:", e);
                    }
                  }}
                  style={{
                    background: 'rgba(0, 229, 255, 0.08)',
                    color: '#00e5ff',
                    border: '1px solid rgba(0, 229, 255, 0.15)',
                    borderRadius: '4px',
                    padding: '0.15rem 0.45rem',
                    fontSize: '0.65rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  📥 Export CSV
                </button>
              </div>
            </div>

            {/* Tab 1: Equity Curve */}
            {backtestTab === 'equity' && (
              <>
                <div style={{ height: '110px', width: '100%', margin: '0.2rem 0' }}>
                  {drawEquityCurve()}
                </div>

                <div className="perf-header-stats" style={{ marginTop: '0.5rem', gap: '1rem' }}>
                  <div className="perf-stat-item">
                    <span className="perf-stat-label">Win Rate</span>
                    <span className="perf-stat-val" style={{ color: '#10b981' }}>{portfolio?.win_rate || 61.2}% <span style={{ fontSize: '0.7rem', fontWeight: 400 }}>+88.3%</span></span>
                  </div>
                  <div className="perf-stat-item">
                    <span className="perf-stat-label">Profit Factor</span>
                    <span className="perf-stat-val" style={{ color: '#00e5ff' }}>{portfolio?.profit_factor || 2.8} <span style={{ fontSize: '0.7rem', fontWeight: 400 }}>+4.5%</span></span>
                  </div>
                  <div className="perf-stat-item">
                    <span className="perf-stat-label">Sharpe Ratio</span>
                    <span className="perf-stat-val" style={{ color: '#f59e0b' }}>{portfolio?.sharpe_ratio || 1.1}</span>
                  </div>
                </div>

                {/* Equity Milestones Log list */}
                {portfolio?.equity_curve && portfolio.equity_curve.length > 1 && (
                  <div style={{ marginTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '0.5rem' }}>
                    <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginBottom: '0.25rem', fontWeight: 600 }}>Equity Milestones</div>
                    <div style={{ display: 'flex', gap: '0.4rem', overflowX: 'auto', paddingBottom: '0.2rem' }}>
                      {portfolio.equity_curve.slice(-5).map((eq, idx) => (
                        <span key={idx} style={{ 
                          background: 'rgba(255,255,255,0.01)', 
                          border: '1px solid rgba(255,255,255,0.03)', 
                          borderRadius: '3px', 
                          padding: '0.15rem 0.35rem', 
                          fontSize: '0.65rem', 
                          color: eq >= 100000 ? '#10b981' : '#ef4444',
                          whiteSpace: 'nowrap'
                        }}>
                          Step {idx + 1}: ₹{eq.toLocaleString()}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Tab 2: Backtester */}
            {backtestTab === 'backtest' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {!backtestResults ? (
                  // Inputs form
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', background: 'rgba(255,255,255,0.01)', padding: '0.5rem', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.03)', marginTop: '0.2rem' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.4rem' }}>
                      <div className="form-group">
                        <label style={{ fontSize: '0.65rem' }}>Strategy</label>
                        <select value={backtestStrategy} onChange={(e) => setBacktestStrategy(e.target.value)} style={{ padding: '0.2rem', fontSize: '0.7rem', background: '#0b0f19', border: '1px solid rgba(255,255,255,0.08)', color: '#fff', borderRadius: '3px' }}>
                          <option value="AI">QuantX AI (V5)</option>
                          <option value="EMA">EMA Crossover</option>
                          <option value="RSI">RSI Strategy</option>
                          <option value="VWAP">VWAP Strategy</option>
                          <option value="BREAKOUT">Breakout Strategy</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label style={{ fontSize: '0.65rem' }}>Interval</label>
                        <select value={backtestInterval} onChange={(e) => setBacktestInterval(e.target.value)} style={{ padding: '0.2rem', fontSize: '0.7rem', background: '#0b0f19', border: '1px solid rgba(255,255,255,0.08)', color: '#fff', borderRadius: '3px' }}>
                          <option value="15m">15 Minute</option>
                          <option value="1h">1 Hour</option>
                          <option value="1d">1 Day</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label style={{ fontSize: '0.65rem' }}>Period</label>
                        <select value={backtestPeriod} onChange={(e) => setBacktestPeriod(e.target.value)} style={{ padding: '0.2rem', fontSize: '0.7rem', background: '#0b0f19', border: '1px solid rgba(255,255,255,0.08)', color: '#fff', borderRadius: '3px' }}>
                          <option value="30d">30 Days</option>
                          <option value="60d">60 Days</option>
                          <option value="180d">180 Days</option>
                          <option value="1y">1 Year</option>
                        </select>
                      </div>
                    </div>
                    <button 
                      onClick={async () => {
                        setIsBacktesting(true);
                        try {
                          const res = await fetch(`${API_BASE}/backtest?symbol=${symbol}&strategy=${backtestStrategy}&period=${backtestPeriod}&interval=${backtestInterval}`);
                          const json = await res.json();
                          setBacktestResults(json);
                        } catch (e) {
                          console.error("Backtest runner failed:", e);
                        }
                        setIsBacktesting(false);
                      }}
                      className="btn btn-buy" 
                      style={{ width: '100%', padding: '0.3rem', fontSize: '0.75rem', fontWeight: 700, marginTop: '0.2rem' }}
                      disabled={isBacktesting}
                    >
                      {isBacktesting ? '⏱️ Running Historical Simulation...' : '🚀 Execute Strategy Backtest'}
                    </button>
                  </div>
                ) : (
                  // Backtest results display
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ fontSize: '0.75rem', color: '#00e5ff', fontWeight: 600 }}>Results: {backtestStrategy} Strategy</div>
                      <button 
                        onClick={() => setBacktestResults(null)} 
                        style={{ background: 'transparent', border: 'none', color: '#ef4444', fontSize: '0.65rem', cursor: 'pointer', textDecoration: 'underline' }}
                      >
                        Clear Backtest
                      </button>
                    </div>
                    
                    {/* Performance stats grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '0.3rem', fontSize: '0.7rem' }}>
                      <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '3px', padding: '0.25rem' }}>
                        <span style={{ color: '#9ca3af', fontSize: '0.55rem' }}>Win Rate</span>
                        <div style={{ fontWeight: 700, color: '#10b981', fontSize: '0.8rem' }}>{backtestResults.metrics.win_rate}%</div>
                      </div>
                      <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '3px', padding: '0.25rem' }}>
                        <span style={{ color: '#9ca3af', fontSize: '0.55rem' }}>Profit Factor</span>
                        <div style={{ fontWeight: 700, color: '#00e5ff', fontSize: '0.8rem' }}>{backtestResults.metrics.profit_factor}</div>
                      </div>
                      <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '3px', padding: '0.25rem' }}>
                        <span style={{ color: '#9ca3af', fontSize: '0.55rem' }}>Max Drawdown</span>
                        <div style={{ fontWeight: 700, color: '#ef4444', fontSize: '0.8rem' }}>-{backtestResults.metrics.max_drawdown}%</div>
                      </div>
                      <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '3px', padding: '0.25rem' }}>
                        <span style={{ color: '#9ca3af', fontSize: '0.55rem' }}>Sharpe / Sortino</span>
                        <div style={{ fontWeight: 700, color: '#f59e0b', fontSize: '0.75rem' }}>{backtestResults.metrics.sharpe_ratio} / {backtestResults.metrics.sortino_ratio}</div>
                      </div>
                    </div>

                    {/* Monte Carlo Sizing block */}
                    {backtestResults.monte_carlo && (
                      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '0.4rem', background: 'rgba(255,255,255,0.02)', padding: '0.35rem 0.5rem', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.04)', fontSize: '0.7rem' }}>
                        <div>
                          <span style={{ color: '#9ca3af' }}>🎲 Monte Carlo Max Drawdown (95% Value-at-Risk)</span>
                          <div style={{ color: '#ef4444', fontWeight: 700, fontSize: '0.8rem', marginTop: '0.1rem' }}>-{backtestResults.monte_carlo["95th_percentile_drawdown"]}%</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <span style={{ color: '#9ca3af' }}>Avg holding time</span>
                          <div style={{ color: '#f3f4f6', fontWeight: 600, fontSize: '0.8rem', marginTop: '0.1rem' }}>{backtestResults.metrics.avg_holding_time} hrs</div>
                        </div>
                      </div>
                    )}

                    {/* AI Insights block */}
                    {backtestResults.ai_report && (
                      <div style={{ background: 'rgba(0, 229, 255, 0.03)', border: '1px solid rgba(0, 229, 255, 0.08)', borderRadius: '4px', padding: '0.4rem', fontSize: '0.7rem' }}>
                        <div style={{ color: '#00e5ff', fontWeight: 700, marginBottom: '0.15rem' }}>🧠 AI Strategy Insights</div>
                        <div style={{ color: '#f3f4f6', lineHeight: '1.2' }}>
                          <strong style={{ color: '#ef4444' }}>Weakness:</strong> {backtestResults.ai_report.weakness}
                          <br />
                          <strong style={{ color: '#10b981' }}>Improvements:</strong> {backtestResults.ai_report.improvements}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Tab 3: Strategy Compare */}
            {backtestTab === 'compare' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {!compareResults ? (
                  <button 
                    onClick={async () => {
                      setIsComparing(true);
                      try {
                        const res = await fetch(`${API_BASE}/backtest/compare?symbol=${symbol}`);
                        const json = await res.json();
                        setCompareResults(json);
                      } catch (e) {
                        console.error("Comparison matrix failed:", e);
                      }
                      setIsComparing(false);
                    }}
                    className="btn btn-buy" 
                    style={{ width: '100%', padding: '0.4rem', fontSize: '0.75rem', fontWeight: 700, marginTop: '1rem' }}
                    disabled={isComparing}
                  >
                    {isComparing ? '⏱️ Compiling Performance Matrix...' : '📊 Run Strategy Comparison Matrix'}
                  </button>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ fontSize: '0.75rem', color: '#00e5ff', fontWeight: 600 }}>Strategy Comparison Matrix</div>
                      <button 
                        onClick={() => setCompareResults(null)} 
                        style={{ background: 'transparent', border: 'none', color: '#ef4444', fontSize: '0.65rem', cursor: 'pointer', textDecoration: 'underline' }}
                      >
                        Clear Comparison
                      </button>
                    </div>
                    
                    <div className="terminal-table-container" style={{ maxHeight: '140px', overflowY: 'auto' }}>
                      <table className="terminal-table" style={{ fontSize: '0.65rem' }}>
                        <thead>
                          <tr>
                            <th>Strategy</th>
                            <th>Win Rate</th>
                            <th>Drawdown</th>
                            <th>Profit</th>
                            <th>Trades</th>
                          </tr>
                        </thead>
                        <tbody>
                          {compareResults.map((row, idx) => (
                            <tr key={idx}>
                              <td style={{ fontWeight: 600, color: '#00e5ff' }}>{row.strategy}</td>
                              <td>{row.win_rate}%</td>
                              <td style={{ color: '#ef4444' }}>-{row.drawdown}%</td>
                              <td style={{ color: row.profit >= 0 ? '#10b981' : '#ef4444', fontWeight: 600 }}>₹{row.profit.toLocaleString()}</td>
                              <td>{row.trades}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Tab 4: Administrative Monitor */}
            {backtestTab === 'admin' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', marginTop: '0.2rem' }}>
                {adminStats ? (
                  <>
                    {/* Key Stats Cards */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
                      <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '4px', padding: '0.4rem', textAlign: 'center' }}>
                        <div style={{ fontSize: '0.55rem', color: '#9ca3af' }}>Registered Users</div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#00e5ff', marginTop: '0.15rem' }}>{adminStats.total_users}</div>
                      </div>
                      <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '4px', padding: '0.4rem', textAlign: 'center' }}>
                        <div style={{ fontSize: '0.55rem', color: '#9ca3af' }}>Active Sessions</div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#00e5ff', marginTop: '0.15rem' }}>{adminStats.active_sessions}</div>
                      </div>
                      <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '4px', padding: '0.4rem', textAlign: 'center' }}>
                        <div style={{ fontSize: '0.55rem', color: '#9ca3af' }}>Trades Executed</div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#10b981', marginTop: '0.15rem' }}>{adminStats.total_trades}</div>
                      </div>
                      <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '4px', padding: '0.4rem', textAlign: 'center' }}>
                        <div style={{ fontSize: '0.55rem', color: '#9ca3af' }}>Database Size</div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#f59e0b', marginTop: '0.15rem' }}>{adminStats.db_size_kb} KB</div>
                      </div>
                    </div>

                    {/* Server Terminals Log View */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                      <div style={{ fontSize: '0.7rem', color: '#00e5ff', fontWeight: 600 }}>📡 System Uptime Console Logs</div>
                      <div style={{ 
                        background: '#070a13', 
                        border: '1px solid rgba(255,255,255,0.03)', 
                        borderRadius: '4px', 
                        padding: '0.5rem', 
                        fontFamily: 'monospace', 
                        fontSize: '0.65rem', 
                        color: '#10b981', 
                        maxHeight: '110px', 
                        overflowY: 'auto',
                        lineHeight: '1.4'
                      }}>
                        {adminStats.system_logs.map((log, idx) => (
                          <div key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.01)', paddingBottom: '0.15rem', marginBottom: '0.15rem' }}>
                            {log}
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                ) : (
                  <div style={{ fontSize: '0.75rem', color: '#9ca3af', textAlign: 'center' }}>Querying administrative storage logs...</div>
                )}
              </div>
            )}
          </div>

          {/* Live Market Scanner Panel */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">🔍 Scanner</div>
              <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.75rem' }}>
                <span style={{ color: '#00e5ff', cursor: 'pointer', fontWeight: 600 }}>Top Movers</span>
                <span style={{ color: '#9ca3af', cursor: 'pointer' }}>Volume Spike</span>
                <span style={{ color: '#9ca3af', cursor: 'pointer' }}>Breakouts</span>
              </div>
            </div>
            <div className="terminal-table-container">
              <table className="terminal-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Price</th>
                    <th>Signal</th>
                    <th>RSI</th>
                    <th>Win Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {scannerData ? (
                    [
                      ...(scannerData.buy_candidates || []),
                      ...(scannerData.sell_candidates || []),
                      ...(scannerData.hold_candidates || [])
                    ].map((stock) => (
                      <tr key={stock.symbol} onClick={() => setSymbol(stock.symbol)}>
                        <td style={{ fontWeight: 600, color: '#00e5ff' }}>{stock.symbol.replace('.NS', '')}</td>
                        <td>₹{stock.entry}</td>
                        <td>
                          <span className={`scanner-signal-badge ${stock.signal.toLowerCase()}`}>
                            {stock.signal}
                          </span>
                        </td>
                        <td>{stock.indicators.rsi}</td>
                        <td style={{ color: '#10b981', fontWeight: 600 }}>
                          {stock.probability_of_profit * 100}%
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="5" style={{ textAlign: 'center', color: '#9ca3af' }}>Scanning watchlist data matrix...</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Sidebar panels */}
        <div className="sidebar-column">
          {/* AI Signal panel */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">🤖 AI Signal</div>
              <div style={{ fontSize: '0.80rem', color: '#00e5ff', fontWeight: 600 }}>{symbol.replace('.NS', '')}</div>
            </div>
            {signalData ? (
              <div className="signal-box">
                <div className={`signal-status-badge ${signalData.signal.toLowerCase()}`}>
                  {signalData.signal === 'BUY' ? '↑ BUY' : signalData.signal === 'SELL' ? '↓ SELL' : 'HOLD'}
                </div>
                
                <div className="metrics-row" style={{ marginTop: '0.25rem' }}>
                  <div className="metric-card">
                    <div className="metric-label">AI Confidence</div>
                    <div className="metric-value" style={{ color: '#00e5ff' }}>{signalData.confidence * 100}%</div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-label">Probability of Profit</div>
                    <div className="metric-value green">{signalData.probability_of_profit * 100}%</div>
                  </div>
                </div>

                <div className="key-value-item" style={{ fontSize: '0.75rem', marginTop: '0.1rem', background: 'rgba(255,255,255,0.02)', padding: '0.35rem 0.5rem', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.04)' }}>
                  <span style={{ color: '#9ca3af' }}>AI Classifier Accuracy</span>
                  <span style={{ color: '#00e5ff', fontWeight: 700 }}>{signalData.accuracy ? (signalData.accuracy * 100).toFixed(0) : 80}%</span>
                </div>

                {/* Progress bar representing probability */}
                <div style={{ margin: '0.2rem 0' }}>
                  <div style={{ background: '#111827', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ 
                      background: signalData.signal === 'BUY' ? '#10b981' : signalData.signal === 'SELL' ? '#ef4444' : '#6b7280', 
                      width: `${signalData.probability_of_profit * 100}%`, 
                      height: '100%',
                      boxShadow: '0 0 8px rgba(16, 185, 129, 0.6)'
                    }}></div>
                  </div>
                </div>

                {/* Risk Level Toggles */}
                <div style={{ display: 'flex', gap: '0.25rem', marginTop: '0.2rem', justifyContent: 'center' }}>
                  {[
                    { label: 'Risk 0.5%', val: 0.005 },
                    { label: 'Risk 1.0%', val: 0.01 },
                    { label: 'Risk 2.0%', val: 0.02 }
                  ].map(riskToggle => (
                    <button
                      key={riskToggle.label}
                      onClick={() => setRiskPercent(riskToggle.val)}
                      style={{
                        background: riskPercent === riskToggle.val ? '#00e5ff' : 'rgba(255,255,255,0.02)',
                        color: riskPercent === riskToggle.val ? '#0b0f19' : '#9ca3af',
                        border: '1px solid',
                        borderColor: riskPercent === riskToggle.val ? '#00e5ff' : 'rgba(255,255,255,0.06)',
                        borderRadius: '3px',
                        padding: '0.2rem 0.4rem',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                    >
                      {riskToggle.label}
                    </button>
                  ))}
                </div>

                {/* ML Feature Weights bar chart */}
                {signalData.feature_importances && (
                  <div style={{ marginTop: '0.4rem', borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '0.4rem' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#00e5ff', marginBottom: '0.35rem' }}>🤖 ML Feature Weights</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                      {Object.entries(signalData.feature_importances)
                        .sort((a, b) => b[1] - a[1])
                        .map(([featName, weight]) => {
                          const displayNames = {
                            "RSI": "RSI Momentum",
                            "ADX": "ADX Trend Strength",
                            "Vol_Ratio": "Volume Spikes",
                            "EMA_9_21": "Short EMA Ratio",
                            "EMA_50_200": "Long EMA Ratio",
                            "SP500_Return": "S&P500 Macro Corr",
                            "Sim_PCR": "Options Put/Call Ratio",
                            "Sim_Sentiment": "News Sentiment Weight"
                          };
                          const widthPct = Math.min(100, Math.max(10, Math.round(weight * 350)));
                          return (
                            <div key={featName} style={{ fontSize: '0.65rem' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#9ca3af', marginBottom: '0.05rem' }}>
                                <span>{displayNames[featName] || featName}</span>
                                <span style={{ color: '#00e5ff', fontWeight: 600 }}>{(weight * 100).toFixed(1)}%</span>
                              </div>
                              <div style={{ background: '#111827', height: '4px', borderRadius: '2px', overflow: 'hidden' }}>
                                <div style={{ 
                                  background: 'linear-gradient(90deg, #00e5ff 0%, #10b981 100%)', 
                                  width: `${widthPct}%`, 
                                  height: '100%' 
                                }}></div>
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                )}

                {/* Key indicators list matching mockup screenshot */}
                <div className="grid-key-values" style={{ marginTop: '0.4rem', gap: '0.4rem' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '0.2rem', color: '#00e5ff' }}>Key indicators</div>
                  <div className="key-value-item">
                    <span className="key-value-label">🟢 Trend (EMA50 vs EMA200)</span>
                    <span className="key-value-val" style={{ color: signalData.indicators.trend > 0 ? '#10b981' : '#ef4444' }}>
                      {signalData.indicators.trend_state}
                    </span>
                  </div>
                  <div className="key-value-item">
                    <span className="key-value-label">🟢 Price Action Pattern</span>
                    <span className="key-value-val" style={{ color: '#00e5ff' }}>
                      {signalData.strategy_details?.pattern || 'Standard Candle'}
                    </span>
                  </div>
                  <div className="key-value-item">
                    <span className="key-value-label">🟢 S/R Breakout Status</span>
                    <span className="key-value-val" style={{ color: '#f59e0b' }}>
                      {signalData.strategy_details?.breakout || 'Range Bound'}
                    </span>
                  </div>
                  <div className="key-value-item">
                    <span className="key-value-label">🟢 Relative Volume (RVOL)</span>
                    <span className="key-value-val" style={{ color: (signalData.strategy_details?.rvol || 1.0) >= 1.5 ? '#10b981' : '#ef4444' }}>
                      {signalData.strategy_details?.rvol || 1.0}x
                    </span>
                  </div>
                  <div className="key-value-item">
                    <span className="key-value-label">🟢 Volatility (ATR)</span>
                    <span className="key-value-val">{signalData.indicators.volatility}</span>
                  </div>
                  <div className="key-value-item">
                    <span className="key-value-label">🟢 Market Regime</span>
                    <span className="key-value-val">{signalData.indicators.market_regime}</span>
                  </div>
                  <div className="key-value-item">
                    <span className="key-value-label">🟢 Support Zone</span>
                    <span className="key-value-val">₹{signalData.indicators.support_zone}</span>
                  </div>
                  <div className="key-value-item">
                    <span className="key-value-label">🟢 Risk to Reward</span>
                    <span className="key-value-val">1 : {signalData.indicators.risk_reward}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div>Calculating indicator matrix...</div>
            )}
          </div>

          {/* Paper Trade Order execution */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">📋 Paper Trade</div>
            </div>
            <div className="trade-form">
              {/* Portfolio Capital Summary */}
              {portfolio && (
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.04)',
                  borderRadius: '6px',
                  padding: '0.5rem 0.75rem',
                  marginBottom: '1rem',
                  fontSize: '0.75rem'
                }}>
                  <div>
                    <span style={{ color: '#9ca3af', display: 'block', fontSize: '0.65rem', marginBottom: '0.1rem' }}>AVAILABLE CASH</span>
                    <span style={{ color: '#00e5ff', fontWeight: 700, fontSize: '0.85rem' }}>₹{portfolio.cash?.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ color: '#9ca3af', display: 'block', fontSize: '0.65rem', marginBottom: '0.1rem' }}>TOTAL EQUITY</span>
                    <span style={{ color: '#10b981', fontWeight: 700, fontSize: '0.85rem' }}>₹{portfolio.equity?.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </div>
                </div>
              )}

              <div className="form-group">
                <label>Stock</label>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <select value={symbol} onChange={(e) => setSymbol(e.target.value)} style={{ flexGrow: 1 }}>
                    {WATCHLIST.map(w => (
                      <option key={w} value={w}>{w.replace('.NS', '')}</option>
                    ))}
                  </select>
                  {chartData.length > 0 && (
                    <button 
                      onClick={() => {
                        const lp = chartData[chartData.length - 1].close;
                        setEntryPrice(lp);
                        // Auto-fill SL/Target based on standard risk parameters
                        setStopLoss(Math.round(lp * 0.995 * 100) / 100);
                        setTarget(Math.round(lp * 1.01 * 100) / 100);
                      }}
                      style={{
                        background: 'rgba(0, 229, 255, 0.1)',
                        color: '#00e5ff',
                        border: '1px solid rgba(0, 229, 255, 0.25)',
                        borderRadius: '4px',
                        padding: '0.45rem 0.6rem',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                        whiteSpace: 'nowrap',
                        boxShadow: '0 0 8px rgba(0, 229, 255, 0.1)'
                      }}
                    >
                      ⚡ Use Live Price: ₹{chartData[chartData.length - 1].close.toFixed(2)}
                    </button>
                  )}
                </div>
              </div>

              <div className="metrics-row">
                <div className="form-group">
                  <label>Entry Price (₹)</label>
                  <input type="number" value={entryPrice} onChange={(e) => setEntryPrice(parseFloat(e.target.value))} />
                </div>
                <div className="form-group">
                  <label>Quantity (Shares)</label>
                  <input type="number" value={quantity} onChange={(e) => setQuantity(parseInt(e.target.value))} />
                </div>
              </div>
              <div className="metrics-row">
                <div className="form-group">
                  <label>Stop Loss (₹)</label>
                  <input type="number" value={stopLoss} onChange={(e) => setStopLoss(parseFloat(e.target.value))} />
                </div>
                <div className="form-group">
                  <label>Target (₹)</label>
                  <input type="number" value={target} onChange={(e) => setTarget(parseFloat(e.target.value))} />
                </div>
              </div>

              {activePosition ? (
                <div className="position-details">
                  <div className="position-header-pnl">
                    <span>ACTIVE POSITION ({activePosition.signal})</span>
                    <span className={`pnl-value ${activePosition.unrealized_pnl >= 0 ? 'up' : 'down'}`}>
                      ₹{activePosition.unrealized_pnl}
                    </span>
                  </div>
                  <div className="key-value-item" style={{ fontSize: '0.75rem' }}>
                    <span className="key-value-label">Current Price</span>
                    <span>₹{activePosition.current_price || activePosition.entry_price}</span>
                  </div>
                  <div className="key-value-item" style={{ fontSize: '0.75rem' }}>
                    <span className="key-value-label">PnL today</span>
                    <span className={activePosition.unrealized_pnl >= 0 ? 'pnl-badge green' : 'pnl-badge red'}>
                      ₹{activePosition.unrealized_pnl}
                    </span>
                  </div>
                  <button className="btn btn-close-trade" style={{ background: '#ef4444', color: '#fff' }} onClick={() => handleCloseTrade(symbol)}>
                    Close Position
                  </button>
                </div>
              ) : (
                <div className="trade-buttons-row">
                  <button className="btn btn-buy" onClick={() => handleStartTrade('BUY')}>Start Trade (Buy)</button>
                  <button className="btn btn-sell" style={{ background: '#ef4444' }} onClick={() => handleStartTrade('SELL')}>Short Sell</button>
                </div>
              )}
            </div>
          </div>

          {/* Level 2 DOM (Depth of Market) Panel */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">📊 Depth of Market (Level 2)</div>
              <div style={{ fontSize: '0.7rem', color: '#9ca3af' }}>Spread: ₹{(domData?.asks && domData?.bids ? (domData.asks[0].price - domData.bids[0].price) : 0.15).toFixed(2)}</div>
            </div>
            <div style={{ fontSize: '0.75rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.25rem', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '0.2rem', fontWeight: 600, color: '#9ca3af' }}>
                <div>Bids (BUY)</div>
                <div style={{ textAlign: 'right' }}>Asks (SELL)</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                {[0, 1, 2, 3, 4].map(i => {
                  const bid = domData?.bids[i] || { price: (signalData?.entry || 1300.0) - i * 0.4, qty: 500 + i * 200 };
                  const ask = domData?.asks[i] || { price: (signalData?.entry || 1300.0) + 0.2 + i * 0.4, qty: 600 + i * 150 };
                  return (
                    <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: '#10b981' }}>
                        <span>₹{bid.price.toFixed(2)}</span>
                        <span style={{ color: '#9ca3af' }}>{bid.qty}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: '#ef4444', direction: 'rtl' }}>
                        <span>₹{ask.price.toFixed(2)}</span>
                        <span style={{ color: '#9ca3af' }}>{ask.qty}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Time & Sales Ticking prints tape */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">⏱️ Time & Sales (Live Prints)</div>
              <span className="live-pulse" style={{ background: '#10b981' }}></span>
            </div>
            <div style={{ maxHeight: '110px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.2rem', fontSize: '0.75rem' }}>
              {timeSales && timeSales.length > 0 ? (
                timeSales.map((t, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.15rem 0.35rem', background: 'rgba(255,255,255,0.01)', borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                    <span style={{ color: '#9ca3af' }}>{t.time}</span>
                    <span style={{ color: t.side === 'BUY' ? '#10b981' : '#ef4444', fontWeight: 600 }}>₹{t.price.toFixed(2)}</span>
                    <span style={{ color: '#f3f4f6' }}>{t.qty} shares</span>
                  </div>
                ))
              ) : (
                [1, 2, 3, 4, 5].map(i => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.15rem 0.35rem', opacity: 0.5 }}>
                    <span style={{ color: '#9ca3af' }}>17:40:02</span>
                    <span style={{ color: '#10b981', fontWeight: 600 }}>₹{(signalData?.entry || 1300.0) + (i * 0.1)}</span>
                    <span style={{ color: '#f3f4f6' }}>120 shares</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Derivative Flows Panel */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">💰 Derivative & FII/DII Flows</div>
              <div style={{ fontSize: '0.75rem', color: '#00e5ff' }}>Daily Net Activity</div>
            </div>
            {signalData?.derivatives ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.8rem' }}>
                <div className="key-value-item">
                  <span className="key-value-label">Put-Call Ratio (PCR)</span>
                  <span className="key-value-val" style={{ color: signalData.derivatives.pcr >= 1.0 ? '#10b981' : '#ef4444', fontWeight: 600 }}>
                    {signalData.derivatives.pcr} ({signalData.derivatives.pcr >= 1.0 ? 'Bullish' : 'Bearish'})
                  </span>
                </div>
                
                <div className="key-value-item">
                  <span className="key-value-label">Total Open Interest (OI)</span>
                  <span className="key-value-val">{signalData.derivatives.total_oi.toLocaleString()} shares</span>
                </div>

                <div className="key-value-item">
                  <span className="key-value-label">OI Change Today</span>
                  <span className="key-value-val" style={{ color: signalData.derivatives.oi_change_pct >= 0 ? '#10b981' : '#ef4444' }}>
                    {signalData.derivatives.oi_change_pct >= 0 ? '+' : ''}{signalData.derivatives.oi_change_pct}% ({signalData.derivatives.oi_status})
                  </span>
                </div>

                <div style={{ borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: '0.5rem', marginTop: '0.2rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginBottom: '0.3rem', fontWeight: 600 }}>Institutional Net Activity (₹ Cr)</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem' }}>
                    <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '4px', padding: '0.4rem', flex: 1, textAlign: 'center' }}>
                      <div style={{ fontSize: '0.65rem', color: '#9ca3af' }}>FII Net Flow</div>
                      <div style={{ fontWeight: 600, color: signalData.derivatives.fii_net_flow >= 0 ? '#10b981' : '#ef4444', fontSize: '0.85rem', marginTop: '0.1rem' }}>
                        {signalData.derivatives.fii_net_flow >= 0 ? '+' : ''}₹{signalData.derivatives.fii_net_flow} Cr
                      </div>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '4px', padding: '0.4rem', flex: 1, textAlign: 'center' }}>
                      <div style={{ fontSize: '0.65rem', color: '#9ca3af' }}>DII Net Flow</div>
                      <div style={{ fontWeight: 600, color: signalData.derivatives.dii_net_flow >= 0 ? '#10b981' : '#ef4444', fontSize: '0.85rem', marginTop: '0.1rem' }}>
                        {signalData.derivatives.dii_net_flow >= 0 ? '+' : ''}₹{signalData.derivatives.dii_net_flow} Cr
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: '0.8rem', color: '#9ca3af', textAlign: 'center', marginTop: '1rem' }}>Awaiting derivative calculation...</div>
            )}
          </div>

          {/* News & Gold Sentiment Panel */}
          <div className="panel">
            <div className="panel-header" style={{ paddingBottom: '0.4rem' }}>
              <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
                <span 
                  onClick={() => setNewsTab("stock")}
                  style={{
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    color: newsTab === 'stock' ? '#fff' : '#9ca3af',
                    borderBottom: newsTab === 'stock' ? '2px solid #00e5ff' : 'none',
                    paddingBottom: '0.2rem'
                  }}
                >
                  📰 Stock News
                </span>
                <span 
                  onClick={() => setNewsTab("gold")}
                  style={{
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    color: newsTab === 'gold' ? '#fff' : '#9ca3af',
                    borderBottom: newsTab === 'gold' ? '2px solid #00e5ff' : 'none',
                    paddingBottom: '0.2rem'
                  }}
                >
                  🏆 Gold Advisor
                </span>
              </div>
              
              {newsTab === 'stock' && signalData?.sentiment && (
                <div style={{ 
                  fontSize: '0.75rem', 
                  fontWeight: 600, 
                  color: signalData.sentiment.score > 0.15 ? '#10b981' : signalData.sentiment.score < -0.15 ? '#ef4444' : '#9ca3af' 
                }}>
                  {signalData.sentiment.sentiment} ({signalData.sentiment.score > 0 ? '+' : ''}{signalData.sentiment.score})
                </div>
              )}
              {newsTab === 'gold' && goldData && (
                <span className={`scanner-signal-badge ${goldData.signal.toLowerCase()}`} style={{ fontSize: '0.65rem', padding: '0.1rem 0.35rem' }}>
                  {goldData.signal}
                </span>
              )}
            </div>

            {newsTab === 'stock' ? (
              <div style={{ maxHeight: '240px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {signalData?.sentiment?.articles && signalData.sentiment.articles.length > 0 ? (
                  signalData.sentiment.articles.map((art, idx) => (
                    <div key={idx} style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '4px', padding: '0.4rem', fontSize: '0.75rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: '#9ca3af', marginBottom: '0.2rem', fontSize: '0.65rem' }}>
                        <span>{art.publisher} {art.date && `• ${art.date}`}</span>
                        <span style={{ 
                          color: art.sentiment === 'Positive' ? '#10b981' : art.sentiment === 'Negative' ? '#ef4444' : '#9ca3af',
                          fontWeight: 600
                        }}>
                          {art.sentiment}
                        </span>
                      </div>
                      <div style={{ color: '#f3f4f6', lineHeight: '1.2' }}>{art.title}</div>
                    </div>
                  ))
                ) : (
                  <div style={{ fontSize: '0.75rem', color: '#9ca3af', textAlign: 'center' }}>No recent news headlines.</div>
                )}
              </div>
            ) : (
              <div style={{ maxHeight: '240px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                {goldData ? (
                  <>
                    {/* Gold Prices Row */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem' }}>
                      <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '4px', padding: '0.4rem', flex: 1, textAlign: 'center' }}>
                        <div style={{ fontSize: '0.6rem', color: '#9ca3af' }}>COMEX Gold Futures</div>
                        <div style={{ fontWeight: 700, color: '#f59e0b', fontSize: '0.8rem', marginTop: '0.1rem' }}>
                          ${goldData.futures_price?.toLocaleString()} <span style={{ fontSize: '0.6rem', fontWeight: 500, color: goldData.change_pct >= 0 ? '#10b981' : '#ef4444' }}>({goldData.change_pct >= 0 ? '+' : ''}{goldData.change_pct}%)</span>
                        </div>
                      </div>
                      <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '4px', padding: '0.4rem', flex: 1, textAlign: 'center' }}>
                        <div style={{ fontSize: '0.6rem', color: '#9ca3af' }}>NSE Gold BeES</div>
                        <div style={{ fontWeight: 700, color: '#f59e0b', fontSize: '0.8rem', marginTop: '0.1rem' }}>
                          ₹{goldData.bees_price?.toFixed(2)}
                        </div>
                      </div>
                    </div>

                    {/* Advice text box */}
                    <div style={{ background: 'rgba(0, 229, 255, 0.03)', border: '1px solid rgba(0, 229, 255, 0.1)', borderRadius: '4px', padding: '0.5rem', fontSize: '0.75rem', lineHeight: '1.4', color: '#f3f4f6' }}>
                      <strong>Advice: </strong>{goldData.recommendation}
                    </div>

                    {/* Entry/Exit timing highlights */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', fontSize: '0.7rem', padding: '0 0.2rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.02)', paddingBottom: '0.2rem' }}>
                        <span style={{ color: '#9ca3af' }}>Buy Timing (Entry)</span>
                        <span style={{ color: '#10b981', fontWeight: 600 }}>{goldData.entry_advice}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: '#9ca3af' }}>Sell Timing (Exit)</span>
                        <span style={{ color: '#ef4444', fontWeight: 600 }}>{goldData.target_advice}</span>
                      </div>
                    </div>

                    {/* Gold Macro Headlines */}
                    <div style={{ borderTop: '1px solid rgba(255,255,255,0.03)', paddingTop: '0.4rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      <div style={{ fontSize: '0.7rem', color: '#00e5ff', fontWeight: 600 }}>🌍 Gold Macro News Feed</div>
                      {goldData.articles && goldData.articles.map((art, idx) => (
                        <div key={idx} style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '4px', padding: '0.35rem', fontSize: '0.7rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#9ca3af', marginBottom: '0.15rem', fontSize: '0.6rem' }}>
                            <span>{art.publisher} • {art.date}</span>
                            <span style={{ color: art.sentiment === 'Positive' ? '#10b981' : art.sentiment === 'Negative' ? '#ef4444' : '#9ca3af', fontWeight: 600 }}>{art.sentiment}</span>
                          </div>
                          <div style={{ color: '#e5e7eb', lineHeight: '1.2' }}>{art.title}</div>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div style={{ fontSize: '0.75rem', color: '#9ca3af', textAlign: 'center' }}>Connecting to MCX & COMEX news matrices...</div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    )}

    {/* User Authentication Modal */}
    {showAuthModal && (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(5, 7, 12, 0.85)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(10px)'
      }}>
        <div style={{
          width: '100%',
          maxWidth: '380px',
          background: '#0d1321',
          border: '1px solid rgba(0, 229, 255, 0.2)',
          borderRadius: '10px',
          padding: '2rem',
          boxShadow: '0 0 30px rgba(0, 229, 255, 0.15)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          position: 'relative'
        }}>
          {/* Close button */}
          <button 
            onClick={() => setShowAuthModal(false)}
            style={{
              position: 'absolute',
              top: '0.75rem',
              right: '0.75rem',
              background: 'transparent',
              border: 'none',
              color: '#9ca3af',
              fontSize: '1.2rem',
              cursor: 'pointer'
            }}
          >
            ×
          </button>

          <h3 style={{ fontFamily: 'Outfit', color: '#fff', fontSize: '1.2rem', fontWeight: 700, textAlign: 'center', marginBottom: '0.2rem' }}>
            {authTab === 'login' ? '🔑 Access QuantX Terminal' : '📝 Create Developer Account'}
          </h3>

          {/* Tab Selection */}
          <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '0.5rem', gap: '1rem' }}>
            <span 
              onClick={() => { setAuthTab("login"); setAuthError(""); }}
              style={{
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                color: authTab === 'login' ? '#00e5ff' : '#9ca3af',
                borderBottom: authTab === 'login' ? '2px solid #00e5ff' : 'none',
                paddingBottom: '0.3rem'
              }}
            >
              Sign In
            </span>
            <span 
              onClick={() => { setAuthTab("register"); setAuthError(""); }}
              style={{
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                color: authTab === 'register' ? '#00e5ff' : '#9ca3af',
                borderBottom: authTab === 'register' ? '2px solid #00e5ff' : 'none',
                paddingBottom: '0.3rem'
              }}
            >
              Register
            </span>
          </div>

          {/* Form Fields */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.65rem', color: '#9ca3af', marginBottom: '0.25rem', fontWeight: 600 }}>Username</label>
              <input 
                type="text" 
                value={authUsername}
                onChange={(e) => setAuthUsername(e.target.value)}
                placeholder="e.g. prathmesh"
                style={{
                  width: '100%',
                  background: '#111827',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '4px',
                  padding: '0.45rem',
                  fontSize: '0.8rem',
                  color: '#fff',
                  outline: 'none'
                }}
              />
            </div>

            {authTab === 'register' && (
              <div>
                <label style={{ display: 'block', fontSize: '0.65rem', color: '#9ca3af', marginBottom: '0.25rem', fontWeight: 600 }}>Email Address</label>
                <input 
                  type="email" 
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  placeholder="e.g. name@domain.com"
                  style={{
                    width: '100%',
                    background: '#111827',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '4px',
                    padding: '0.45rem',
                    fontSize: '0.8rem',
                    color: '#fff',
                    outline: 'none'
                  }}
                />
              </div>
            )}

            <div>
              <label style={{ display: 'block', fontSize: '0.65rem', color: '#9ca3af', marginBottom: '0.25rem', fontWeight: 600 }}>Password</label>
              <input 
                type="password" 
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                placeholder="••••••"
                style={{
                  width: '100%',
                  background: '#111827',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '4px',
                  padding: '0.45rem',
                  fontSize: '0.8rem',
                  color: '#fff',
                  outline: 'none'
                }}
              />
            </div>

            {authTab === 'register' && (
              <div>
                <label style={{ display: 'block', fontSize: '0.65rem', color: '#9ca3af', marginBottom: '0.25rem', fontWeight: 600 }}>Confirm Password</label>
                <input 
                  type="password" 
                  value={authConfirmPassword}
                  onChange={(e) => setAuthConfirmPassword(e.target.value)}
                  placeholder="••••••"
                  style={{
                    width: '100%',
                    background: '#111827',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '4px',
                    padding: '0.45rem',
                    fontSize: '0.8rem',
                    color: '#fff',
                    outline: 'none'
                  }}
                />
              </div>
            )}
          </div>

          {authError && (
            <div style={{ color: '#ef4444', fontSize: '0.75rem', fontWeight: 600, textAlign: 'center' }}>
              ❌ {authError}
            </div>
          )}

          {/* Action button */}
          <button
            onClick={async () => {
              if (!authUsername || !authPassword) {
                setAuthError("Please fill in all credentials.");
                return;
              }
              if (authTab === 'register') {
                if (authPassword.length < 6) {
                  setAuthError("Password must be at least 6 characters.");
                  return;
                }
                if (authPassword !== authConfirmPassword) {
                  setAuthError("Passwords do not match.");
                  return;
                }
              }
              
              const endpoint = authTab === 'login' ? 'login' : 'register';
              try {
                const response = await fetch(`${API_BASE}/auth/${endpoint}`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    username: authUsername,
                    password: authPassword,
                    email: authEmail || null
                  })
                });
                const resJson = await response.json();
                if (!response.ok) {
                  setAuthError(resJson.detail || "Authentication failed.");
                  return;
                }
                
                // Store token and reload profile
                localStorage.setItem("quantx_session_token", resJson.token);
                setCurrentUser({ username: resJson.username, is_authenticated: true });
                setShowAuthModal(false);
                setAuthUsername("");
                setAuthPassword("");
                setAuthEmail("");
                setAuthConfirmPassword("");
                setAuthError("");
                
                // Fetch dynamic portfolio statistics for logged in user
                fetchGlobals();
              } catch (e) {
                setAuthError("Server communication failed.");
              }
            }}
            style={{
              width: '100%',
              background: 'rgba(0, 229, 255, 0.15)',
              color: '#00e5ff',
              border: '1px solid rgba(0, 229, 255, 0.3)',
              borderRadius: '4px',
              padding: '0.55rem',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: 'pointer',
              marginTop: '0.5rem',
              boxShadow: '0 0 10px rgba(0, 229, 255, 0.15)'
            }}
          >
            {authTab === 'login' ? 'Access Dashboard' : 'Create Account'}
          </button>
        </div>
      </div>
    )}

    {/* Alert Configuration Settings Modal */}
    {showSettingsModal && (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(5, 7, 12, 0.85)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        backdropFilter: 'blur(10px)'
      }}>
        <div style={{
          width: '100%',
          maxWidth: '420px',
          background: '#0d1321',
          border: '1px solid rgba(0, 229, 255, 0.2)',
          borderRadius: '10px',
          padding: '2rem',
          boxShadow: '0 0 30px rgba(0, 229, 255, 0.15)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.2rem',
          position: 'relative'
        }}>
          {/* Close button */}
          <button 
            onClick={() => setShowSettingsModal(false)}
            style={{
              position: 'absolute',
              top: '0.75rem',
              right: '0.75rem',
              background: 'transparent',
              border: 'none',
              color: '#9ca3af',
              fontSize: '1.2rem',
              cursor: 'pointer'
            }}
          >
            ×
          </button>

          <h3 style={{ fontFamily: 'Outfit', color: '#fff', fontSize: '1.2rem', fontWeight: 700, textAlign: 'center', marginBottom: '0.1rem' }}>
            ⚙️ QuantX System Settings
          </h3>

          {/* Settings Tab Selector */}
          <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '0.4rem', gap: '1rem', justifyContent: 'center' }}>
            <span 
              onClick={() => { setSettingsTab("alerts"); setSettingsMessage(""); }}
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                color: settingsTab === 'alerts' ? '#00e5ff' : '#9ca3af',
                borderBottom: settingsTab === 'alerts' ? '2px solid #00e5ff' : 'none',
                paddingBottom: '0.2rem'
              }}
            >
              🔔 Alerts
            </span>
            <span 
              onClick={() => { setSettingsTab("broker"); setSettingsMessage(""); }}
              style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                color: settingsTab === 'broker' ? '#00e5ff' : '#9ca3af',
                borderBottom: settingsTab === 'broker' ? '2px solid #00e5ff' : 'none',
                paddingBottom: '0.2rem'
              }}
            >
              🔌 Broker Connector
            </span>
          </div>
          
          {settingsTab === 'alerts' ? (
            <>
              <div style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '6px', padding: '0.6rem', fontSize: '0.7rem', color: '#9ca3af', lineHeight: '1.4' }}>
                <span style={{ color: '#00e5ff', fontWeight: 600 }}>Setup Instructions:</span>
                <ol style={{ margin: '0.3rem 0 0 1rem', padding: 0 }}>
                  <li>Search <strong>@BotFather</strong> on Telegram & create a bot using <code>/newbot</code>. Copy the token.</li>
                  <li>Send any message to your new bot.</li>
                  <li>Search <strong>@userinfobot</strong> on Telegram to copy your <strong>Chat ID</strong>.</li>
                </ol>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.65rem', color: '#9ca3af', marginBottom: '0.25rem', fontWeight: 600 }}>Telegram Bot Token</label>
                  <input 
                    type="text" 
                    value={telegramToken}
                    onChange={(e) => setTelegramToken(e.target.value)}
                    placeholder="e.g. 123456789:ABCdefGhIJKlmNoPQRsT"
                    style={{
                      width: '100%',
                      background: '#111827',
                      border: '1px solid rgba(255,255,255,0.08)',
                      borderRadius: '4px',
                      padding: '0.45rem',
                      fontSize: '0.75rem',
                      color: '#fff',
                      outline: 'none',
                      fontFamily: 'monospace'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.65rem', color: '#9ca3af', marginBottom: '0.25rem', fontWeight: 600 }}>Telegram Chat ID</label>
                  <input 
                    type="text" 
                    value={telegramChatId}
                    onChange={(e) => setTelegramChatId(e.target.value)}
                    placeholder="e.g. 987654321"
                    style={{
                      width: '100%',
                      background: '#111827',
                      border: '1px solid rgba(255,255,255,0.08)',
                      borderRadius: '4px',
                      padding: '0.45rem',
                      fontSize: '0.75rem',
                      color: '#fff',
                      outline: 'none',
                      fontFamily: 'monospace'
                    }}
                  />
                </div>
              </div>
            </>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
              <div style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '6px', padding: '0.5rem', fontSize: '0.7rem', color: '#9ca3af', lineHeight: '1.4' }}>
                <span style={{ color: '#00e5ff', fontWeight: 600 }}>Broker API Mode:</span>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.3rem' }}>
                  <button 
                    onClick={() => setBrokerMode("PAPER")}
                    style={{
                      flex: 1,
                      background: brokerMode === 'PAPER' ? 'rgba(0, 229, 255, 0.15)' : 'rgba(255,255,255,0.01)',
                      color: brokerMode === 'PAPER' ? '#00e5ff' : '#9ca3af',
                      border: '1px solid ' + (brokerMode === 'PAPER' ? 'rgba(0, 229, 255, 0.3)' : 'rgba(255,255,255,0.06)'),
                      borderRadius: '4px',
                      padding: '0.3rem',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    📝 Paper Trading
                  </button>
                  <button 
                    onClick={() => setBrokerMode("ZERODHA")}
                    style={{
                      flex: 1,
                      background: brokerMode === 'ZERODHA' ? 'rgba(234, 88, 12, 0.15)' : 'rgba(255,255,255,0.01)',
                      color: brokerMode === 'ZERODHA' ? '#ea580c' : '#9ca3af',
                      border: '1px solid ' + (brokerMode === 'ZERODHA' ? 'rgba(234, 88, 12, 0.3)' : 'rgba(255,255,255,0.06)'),
                      borderRadius: '4px',
                      padding: '0.3rem',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    🔌 Zerodha Kite
                  </button>
                </div>
              </div>

              {brokerMode === 'ZERODHA' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.65rem', color: '#9ca3af', marginBottom: '0.2rem', fontWeight: 600 }}>Kite API Key</label>
                    <input 
                      type="text" 
                      value={zerodhaApiKey}
                      onChange={(e) => setZerodhaApiKey(e.target.value)}
                      placeholder="Enter Zerodha API Key"
                      style={{
                        width: '100%',
                        background: '#111827',
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: '4px',
                        padding: '0.45rem',
                        fontSize: '0.75rem',
                        color: '#fff',
                        outline: 'none',
                        fontFamily: 'monospace'
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.65rem', color: '#9ca3af', marginBottom: '0.2rem', fontWeight: 600 }}>Kite API Secret</label>
                    <input 
                      type="password" 
                      value={zerodhaApiSecret}
                      onChange={(e) => setZerodhaApiSecret(e.target.value)}
                      placeholder="••••••••••••••••"
                      style={{
                        width: '100%',
                        background: '#111827',
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: '4px',
                        padding: '0.45rem',
                        fontSize: '0.75rem',
                        color: '#fff',
                        outline: 'none',
                        fontFamily: 'monospace'
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {settingsMessage && (
            <div style={{ color: settingsMessage.startsWith('❌') ? '#ef4444' : '#10b981', fontSize: '0.75rem', fontWeight: 600, textAlign: 'center' }}>
              {settingsMessage}
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.5rem' }}>
            <button
              onClick={() => setShowSettingsModal(false)}
              style={{
                flex: 1,
                background: 'rgba(255, 255, 255, 0.03)',
                color: '#9ca3af',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '4px',
                padding: '0.5rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              onClick={async () => {
                try {
                  const endpoint = settingsTab === 'alerts' ? 'alerts/config' : 'broker/config';
                  const payload = settingsTab === 'alerts' 
                    ? { telegram_token: telegramToken, telegram_chat_id: telegramChatId }
                    : { broker_mode: brokerMode, zerodha_api_key: zerodhaApiKey, zerodha_api_secret: zerodhaApiSecret };
                  
                  const res = await fetchWithAuth(`${API_BASE}/${endpoint}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                  });
                  const json = await res.json();
                  if (res.ok && json.status === 'SUCCESS') {
                    setSettingsMessage("✅ Settings saved successfully!");
                    if (settingsTab === 'alerts') {
                      setAlertsEnabled(!!(telegramToken && telegramChatId));
                    }
                    setTimeout(() => setShowSettingsModal(false), 1200);
                  } else {
                    setSettingsMessage("❌ Save failed: " + (json.detail || "Error"));
                  }
                } catch (e) {
                  setSettingsMessage("❌ Save failed: Connection error");
                }
              }}
              style={{
                flex: 1,
                background: 'rgba(0, 229, 255, 0.15)',
                color: '#00e5ff',
                border: '1px solid rgba(0, 229, 255, 0.3)',
                borderRadius: '4px',
                padding: '0.5rem',
                fontSize: '0.75rem',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 0 10px rgba(0, 229, 255, 0.15)'
              }}
            >
              Save Settings
            </button>
          </div>
        </div>
      </div>
    )}
  </div>
);
}
