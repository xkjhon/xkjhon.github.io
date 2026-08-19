/* =============================================================
   eCobOne Mobile — code.js (Dados & Lógica Mobile Otimizada)
   ============================================================= */

const AppState = {
  metas: {
    ANA: 1262,
    URU: 492,
    LUZ: 1870,
    FOR: 634,
    RVR: 709,
    MNH: 1099
  },
  dados: {
    geral: null,
    regionais: {},
    alertas: []
  },
  dataAtualizacaoBase: null,
  avisos: [],
  regiaoSelecionada: 'GERAL',
  chartInstance: null,
  countdownSecs: 30,
  timerInterval: null
};

// Ordem definida pelo usuario: Anapolis, Uruacu, Luziania, Formosa, Rio Verde, Morrinhos
const REGIOES_ORDEM = ['ANA', 'URU', 'LUZ', 'FOR', 'RVR', 'MNH'];

const NOME_REGIAO = {
  GERAL: 'Visão Geral (Todas)',
  ANA: 'Anápolis',
  URU: 'Uruaçu',
  LUZ: 'Luziânia',
  FOR: 'Formosa',
  RVR: 'Rio Verde',
  MNH: 'Morrinhos'
};

document.addEventListener('DOMContentLoaded', function() {
  iniciarCronometro();
  carregarTudo();

  const btnRef = document.getElementById('btnRefreshMobile');
  if (btnRef) {
    btnRef.addEventListener('click', function() {
      carregarTudo();
    });
  }
});

function navToTab(tabId, el) {
  const panes = document.querySelectorAll('.tab-pane');
  panes.forEach(function(p) { p.classList.remove('active'); });

  const targetPane = document.getElementById(tabId);
  if (targetPane) targetPane.classList.add('active');

  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(function(item) { item.classList.remove('active'); });
  if (el) el.classList.add('active');

  if (tabId === 'tabGeral') {
    setTimeout(renderizarChartJsMobile, 100);
  }
}

function iniciarCronometro() {
  if (AppState.timerInterval) clearInterval(AppState.timerInterval);
  AppState.countdownSecs = 30;
  
  const labelTimer = document.getElementById('timerLabelMobile');
  
  AppState.timerInterval = setInterval(function() {
    AppState.countdownSecs--;
    if (labelTimer) labelTimer.textContent = AppState.countdownSecs + 's';
    
    if (AppState.countdownSecs <= 0) {
      carregarTudo();
    }
  }, 1000);
}

async function carregarTudo() {
  AppState.countdownSecs = 30;

  await Promise.all([
    carregarMetas(),
    carregarDados(),
    carregarAvisos()
  ]);

  atualizarHorarioAtualizacao();
  renderizarDashboardMobile();
}

function atualizarHorarioAtualizacao() {
  const elem = document.getElementById('lastUpdateLabelMobile');
  if (elem) {
    if (AppState.dataAtualizacaoBase) {
      const partes = AppState.dataAtualizacaoBase.split(' ');
      const horaStr = partes.length > 1 ? partes[1] : AppState.dataAtualizacaoBase;
      elem.textContent = 'Base: ' + horaStr;
    } else {
      const agora = new Date();
      elem.textContent = 'Base: ' + agora.toLocaleTimeString('pt-BR');
    }
  }
}

// -------------------------------------------------------------
// Carregamento dos arquivos de dados
// -------------------------------------------------------------
async function carregarAvisos() {
  const rotas = [
    '../eCobOne/Python-Updater/Files/Avisos.txt',
    '../Python-Updater/Files/Avisos.txt',
    '../Files/Avisos.txt',
    './Files/Avisos.txt',
    'Avisos.txt'
  ];

  for (const path of rotas) {
    try {
      const res = await fetch(path + '?t=' + Date.now());
      if (res.ok) {
        const texto = await res.text();
        AppState.avisos = texto.split('\n').map(function(l) { return l.trim(); }).filter(function(l) { return l; });
        return;
      }
    } catch (e) {}
  }

  AppState.avisos = [];
}

async function carregarMetas() {
  const rotas = [
    '../eCobOne/Python-Updater/Files/Metas.txt',
    '../Python-Updater/Files/Metas.txt',
    '../Files/Metas.txt',
    './Files/Metas.txt',
    'Metas.txt'
  ];

  for (const path of rotas) {
    try {
      const res = await fetch(path + '?t=' + Date.now());
      if (res.ok) {
        const texto = await res.text();
        const linhas = texto.split('\n');
        linhas.forEach(function(linha) {
          const p = linha.trim().split(':');
          if (p.length === 2) {
            const cod = p[0].trim().toUpperCase();
            const val = parseInt(p[1].trim(), 10);
            if (!isNaN(val) && cod in AppState.metas) {
              AppState.metas[cod] = val;
            }
          }
        });
        return;
      }
    } catch (e) {}
  }
}

async function carregarDados() {
  const rotas = [
    '../eCobOne/Python-Updater/Files/dados.txt',
    '../Python-Updater/Files/dados.txt',
    '../Files/dados.txt',
    './Files/dados.txt',
    'dados.txt'
  ];

  let carregou = false;

  for (const path of rotas) {
    try {
      const res = await fetch(path + '?t=' + Date.now());
      if (res.ok) {
        const texto = await res.text();
        parsearDadosTxt(texto);
        carregou = true;
        break;
      }
    } catch (e) {}
  }

  if (!carregou && !AppState.dados.geral) {
    usarDadosFallback();
  }
}

function parsearDadosTxt(texto) {
  const blocos = texto.split(/\n(?=Atualizacao:|Alertas:|Geral:|Região:)/i);

  AppState.dados.geral = null;
  AppState.dados.regionais = {};
  AppState.dados.alertas = [];

  blocos.forEach(function(blocoTexto) {
    const linhas = blocoTexto.split('\n').map(function(l) { return l.trim(); }).filter(function(l) { return l; });
    if (linhas.length === 0) return;

    const cabecalho = linhas[0];

    if (cabecalho.toLowerCase().indexOf('atualizacao:') === 0) {
      const val = cabecalho.replace(/^atualizacao:\s*/i, '').trim();
      AppState.dataAtualizacaoBase = val;
      return;
    }

    if (cabecalho.toLowerCase().indexOf('alertas:') === 0) {
      linhas.slice(1).forEach(function(linha) {
        if (linha !== '0') {
          const partes = linha.split(';');
          if (partes.length >= 2) {
            AppState.dados.alertas.push({
              ss: partes[0].trim(),
              colab: partes[1].trim(),
              servico: partes[2] ? partes[2].trim() : 'RESTABELECIMENTO',
              regiao: partes[3] ? partes[3].trim() : 'OUT',
              vencimento: partes[4] ? partes[4].trim() : '18:00'
            });
          }
        }
      });
      return;
    }

    const itemDados = {
      servicos: 0,
      religas: 0,
      nePago: 0,
      faturamento: 'R$ 0,00',
      emCampo: 0,
      top10: [],
      bottom10: []
    };

    let modoPiores = false;

    linhas.slice(1).forEach(function(linha) {
      if (linha.toLowerCase().indexOf('piores:') === 0) {
        modoPiores = true;
        return;
      }
      if (linha.indexOf('Serviços:') === 0) {
        itemDados.servicos = parseInt(linha.replace('Serviços:', '').trim(), 10) || 0;
      } else if (linha.indexOf('Religas:') === 0) {
        itemDados.religas = parseInt(linha.replace('Religas:', '').trim(), 10) || 0;
      } else if (linha.indexOf('NePago:') === 0) {
        itemDados.nePago = parseInt(linha.replace('NePago:', '').trim(), 10) || 0;
      } else if (linha.indexOf('Faturamento:') === 0) {
        itemDados.faturamento = linha.replace('Faturamento:', '').trim();
      } else if (linha.indexOf('EmCampo:') === 0) {
        itemDados.emCampo = parseInt(linha.replace('EmCampo:', '').trim(), 10) || 0;
      } else if (/^\d+;/.test(linha)) {
        const partes = linha.split(';');
        if (partes.length >= 4) {
          const itemColab = {
            rank: parseInt(partes[0], 10),
            nome: partes[1].trim(),
            serv: parseInt(partes[2], 10) || 0,
            rlga: parseInt(partes[3], 10) || 0,
            total: (parseInt(partes[2], 10) || 0) + (parseInt(partes[3], 10) || 0)
          };
          if (modoPiores) {
            itemDados.bottom10.push(itemColab);
          } else {
            itemDados.top10.push(itemColab);
          }
        }
      }
    });

    if (!itemDados.bottom10 || itemDados.bottom10.length === 0) {
      itemDados.bottom10 = itemDados.top10.slice().sort(function(a, b) { return a.total - b.total; });
    }

    if (cabecalho.toLowerCase().indexOf('geral:') === 0) {
      AppState.dados.geral = itemDados;
    } else if (cabecalho.toLowerCase().indexOf('região:') === 0) {
      let cod = 'OUT';
      if (cabecalho.indexOf('(ANA)') !== -1) cod = 'ANA';
      else if (cabecalho.indexOf('(URU)') !== -1) cod = 'URU';
      else if (cabecalho.indexOf('(LUZ)') !== -1) cod = 'LUZ';
      else if (cabecalho.indexOf('(FOR)') !== -1) cod = 'FOR';
      else if (cabecalho.indexOf('(RVR)') !== -1) cod = 'RVR';
      else if (cabecalho.indexOf('(MNH)') !== -1) cod = 'MNH';

      AppState.dados.regionais[cod] = itemDados;
    }
  });
}

function usarDadosFallback() {
  const topExemplo = [
    { rank: 1, nome: 'TIAGO LUCIO FERNANDES SOUSA', serv: 53, rlga: 4, total: 57 },
    { rank: 2, nome: 'RONIS MARCIO CANDIDO FERREIRA', serv: 30, rlga: 12, total: 42 },
    { rank: 3, nome: 'FLAVIO DOURADO DE SOUZA', serv: 34, rlga: 3, total: 37 },
    { rank: 4, nome: 'JONATAN RODRIGO BATISTA FELIX', serv: 30, rlga: 0, total: 30 },
    { rank: 5, nome: 'PEDRO HENRIQUE CIRINO DE MELO', serv: 0, rlga: 28, total: 28 },
    { rank: 6, nome: 'RONILSON DAS CHAGAS OLIVEIRA', serv: 17, rlga: 8, total: 25 },
    { rank: 7, nome: 'LANIELSON DE SOUSA LIMA', serv: 6, rlga: 18, total: 24 },
    { rank: 8, nome: 'DAMIAO PEREIRA DE MENESES', serv: 0, rlga: 24, total: 24 },
    { rank: 9, nome: 'HELLEN CRISTINA VALADARES', serv: 0, rlga: 22, total: 22 },
    { rank: 10, nome: 'RAPHAEL SILVA DE SOUZA', serv: 17, rlga: 4, total: 21 }
  ];

  const bottomExemplo = topExemplo.slice().sort(function(a, b) { return a.total - b.total; });

  AppState.dados.geral = {
    servicos: 393,
    religas: 727,
    nePago: 38,
    faturamento: 'R$ 26.222,84',
    emCampo: 11745,
    top10: topExemplo,
    bottom10: bottomExemplo
  };

  AppState.dados.regionais = {
    ANA: { servicos: 73, religas: 110, nePago: 3, faturamento: 'R$ 3.682,47', emCampo: 2223, top10: topExemplo.slice(0, 5), bottom10: bottomExemplo.slice(0, 5) },
    URU: { servicos: 10, religas: 53, nePago: 0, faturamento: 'R$ 0,00', emCampo: 552, top10: topExemplo.slice(0, 5), bottom10: bottomExemplo.slice(0, 5) },
    LUZ: { servicos: 180, religas: 240, nePago: 17, faturamento: 'R$ 7.496,36', emCampo: 4862, top10: topExemplo.slice(0, 5), bottom10: bottomExemplo.slice(0, 5) },
    FOR: { servicos: 0, religas: 76, nePago: 0, faturamento: 'R$ 0,00', emCampo: 950, top10: topExemplo.slice(0, 5), bottom10: bottomExemplo.slice(0, 5) },
    RVR: { servicos: 75, religas: 82, nePago: 12, faturamento: 'R$ 12.650,12', emCampo: 1287, top10: topExemplo.slice(0, 5), bottom10: bottomExemplo.slice(0, 5) },
    MNH: { servicos: 55, religas: 166, nePago: 6, faturamento: 'R$ 2.393,89', emCampo: 1871, top10: topExemplo.slice(0, 5), bottom10: bottomExemplo.slice(0, 5) }
  };
}

// -------------------------------------------------------------
// Renderização do Dashboard Mobile
// -------------------------------------------------------------
function renderizarDashboardMobile() {
  renderizarChipsFiltroMobile();
  renderizarAvisosMobile();
  renderizarQuadrosMetricasMobile();
  renderizarMetasEGraficoMobile();
  renderizarLeaderboardPioresMobile();
  renderizarLeaderboardMobile();
}

function renderizarChipsFiltroMobile() {
  const container = document.getElementById('regionChipsMobile');
  if (!container) return;

  const lista = ['GERAL'].concat(REGIOES_ORDEM);

  container.innerHTML = lista.map(function(cod) {
    const isActive = AppState.regiaoSelecionada === cod;
    const rotulo = cod === 'GERAL' ? '🌐 Todas (Geral)' : NOME_REGIAO[cod];

    return `
      <button class="m-chip ${isActive ? 'active' : ''}" onclick="selecionarRegiaoMobile('${cod}')">
        ${rotulo}
      </button>
    `;
  }).join('');
}

function selecionarRegiaoMobile(cod) {
  AppState.regiaoSelecionada = cod;
  renderizarDashboardMobile();
}

function renderizarAvisosMobile() {
  const banner = document.getElementById('mobileAlertBanner');
  const container = document.getElementById('mAvisosContent');
  const badgeDot = document.getElementById('navAvisoBadge');

  const alertas = AppState.dados.alertas || [];
  const temAlertas = alertas.length > 0;

  if (document.body && document.body.classList) {
    document.body.classList.toggle('theme-alert-yellow', temAlertas);
  }

  if (badgeDot) badgeDot.style.display = temAlertas ? 'block' : 'none';

  if (temAlertas) {
    if (banner) {
      banner.style.display = 'flex';
      banner.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span style="background: #f59e0b; color: #451a03; font-weight: 800; font-size: 0.65rem; padding: 2px 6px; border-radius: 4px;">ALERTA</span>
          <span style="color: #fef08a; font-weight: 800; font-size: 0.82rem;">SS nº ${alertas[0].ss}</span>
        </div>
        <div style="font-size: 0.78rem; color: #fffbeb; font-weight: 600; margin-top: 2px;">
          <strong>${alertas[0].colab}</strong> — Religa em Alerta!
        </div>
        <div style="font-size: 0.72rem; color: #fde047; font-weight: 800; text-align: right;">
          ⏰ Vencimento: ${alertas[0].vencimento}h
        </div>
      `;
    }

    if (container) {
      container.innerHTML = alertas.map(function(item) {
        return `
          <div class="m-reg-card" style="border: 1px solid #f59e0b; background: rgba(245, 158, 11, 0.12);">
            <div class="m-reg-top">
              <span class="m-reg-name" style="color: #fef08a;">SS nº ${item.ss}</span>
              <span class="m-reg-badge" style="background: #f59e0b; color: #451a03;">ALERTA</span>
            </div>
            <div style="font-size: 0.8rem; font-weight: 700; color: #fffbeb;">
              Colaborador: ${item.colab}
            </div>
            <div style="font-size: 0.74rem; color: #fde047; font-weight: 800; margin-top: 2px;">
              ⏰ Vencimento Estimado: ${item.vencimento}h
            </div>
          </div>
        `;
      }).join('');
    }
    return;
  }

  if (banner) banner.style.display = 'none';

  if (container) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--md-text-muted); padding: 20px 10px; font-size: 0.82rem;">
        🔔 Nenhum aviso ou alerta pendente no momento.
      </div>
    `;
  }
}

function renderizarQuadrosMetricasMobile() {
  const cod = AppState.regiaoSelecionada;
  const dados = cod === 'GERAL' ? AppState.dados.geral : AppState.dados.regionais[cod];

  if (!dados) return;

  const totalExecutado = dados.servicos + dados.religas;

  const setVal = function(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  setVal('mEmCampo', dados.emCampo.toLocaleString('pt-BR'));
  setVal('mServicos', dados.servicos.toLocaleString('pt-BR'));
  setVal('mReligas', dados.religas.toLocaleString('pt-BR'));
  setVal('mNePago', dados.nePago.toLocaleString('pt-BR'));
  setVal('mFaturamento', dados.faturamento);
  setVal('mTotalExec', totalExecutado.toLocaleString('pt-BR'));
}

function renderizarMetasEGraficoMobile() {
  const cod = AppState.regiaoSelecionada;
  
  let metaAlvo = 0;
  let realizadoAlvo = 0;

  if (cod === 'GERAL') {
    const vals = [];
    for (const key in AppState.metas) {
      vals.push(AppState.metas[key]);
    }
    metaAlvo = vals.reduce(function(a, b) { return a + b; }, 0);
    const g = AppState.dados.geral;
    realizadoAlvo = g ? g.servicos : 0;
  } else {
    metaAlvo = AppState.metas[cod] || 0;
    const r = AppState.dados.regionais[cod];
    realizadoAlvo = r ? r.servicos : 0;
  }

  const pct = metaAlvo > 0 ? Math.min(Math.round((realizadoAlvo / metaAlvo) * 100), 100) : 0;

  const elemTitle = document.getElementById('mMetaTitle');
  if (elemTitle) elemTitle.textContent = cod === 'GERAL' ? 'Meta Global eCobOne' : `Meta — ${NOME_REGIAO[cod]}`;

  const elemPct = document.getElementById('mGlobalPct');
  if (elemPct) elemPct.textContent = `${pct}%`;

  const elemFill = document.getElementById('mGlobalProgressBar');
  if (elemFill) elemFill.style.width = `${pct}%`;

  const elemStats = document.getElementById('mGlobalStatsText');
  if (elemStats) {
    elemStats.innerHTML = `<span><strong>${realizadoAlvo.toLocaleString('pt-BR')}</strong> Realiz. (SERV)</span> <span>Meta: <strong>${metaAlvo.toLocaleString('pt-BR')}</strong></span>`;
  }

  const containerReg = document.getElementById('mRegionalGoalsGrid');
  if (containerReg) {
    containerReg.innerHTML = REGIOES_ORDEM.map(function(c) {
      const meta = AppState.metas[c] || 0;
      const d = AppState.dados.regionais[c];
      const real = d ? d.servicos : 0;
      const p = meta > 0 ? Math.min(Math.round((real / meta) * 100), 100) : 0;

      let statusBadge = p >= 100 ? '🏆 Batida' : p >= 60 ? '⚡ Em Progresso' : '🎯 Em Execução';

      return `
        <div class="m-reg-card">
          <div class="m-reg-top">
            <span class="m-reg-name">${NOME_REGIAO[c]}</span>
            <span class="m-reg-badge">${statusBadge}</span>
          </div>
          <div class="m-reg-vals">
            <span><strong>${real}</strong> / ${meta}</span>
            <span><strong>${p}%</strong></span>
          </div>
          <div class="m-reg-bar-bg">
            <div class="m-reg-bar-fill" style="width: ${p}%"></div>
          </div>
        </div>
      `;
    }).join('');
  }

  renderizarChartJsMobile();
}

function renderizarChartJsMobile() {
  const canvas = document.getElementById('mobileGoalsChart');
  if (!canvas || typeof Chart === 'undefined') return;

  const labels = REGIOES_ORDEM.map(function(c) { return NOME_REGIAO[c]; });
  const metasData = REGIOES_ORDEM.map(function(c) { return AppState.metas[c] || 0; });
  const realizadosData = REGIOES_ORDEM.map(function(c) {
    const d = AppState.dados.regionais[c];
    return d ? d.servicos : 0;
  });

  const isYellow = document.body && document.body.classList && document.body.classList.contains('theme-alert-yellow');
  const barColor = isYellow ? '#f59e0b' : '#10b981';
  const barBorder = isYellow ? '#d97706' : '#059669';
  const labelColor = isYellow ? '#fde68a' : '#a7f3d0';
  const metaBg = isYellow ? 'rgba(251, 191, 36, 0.22)' : 'rgba(52, 211, 153, 0.25)';
  const metaBorder = isYellow ? '#fbbf24' : '#34d399';

  if (AppState.chartInstance) {
    AppState.chartInstance.destroy();
  }

  const ctx = canvas.getContext('2d');
  AppState.chartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Meta',
          data: metasData,
          backgroundColor: metaBg,
          borderColor: metaBorder,
          borderWidth: 1.5,
          borderRadius: 4
        },
        {
          label: 'Realizado',
          data: realizadosData,
          backgroundColor: barColor,
          borderColor: barBorder,
          borderWidth: 1.5,
          borderRadius: 4
        }
      ]
    },
    options: {
      animation: { duration: 400 },
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: {
            color: labelColor,
            boxWidth: 8,
            font: { family: 'Plus Jakarta Sans', size: 9, weight: '600' }
          }
        }
      },
      scales: {
        x: {
          ticks: { color: labelColor, font: { family: 'Plus Jakarta Sans', size: 8, weight: '600' } },
          grid: { display: false }
        },
        y: {
          ticks: { color: labelColor, font: { size: 8 } },
          grid: { color: isYellow ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)' }
        }
      }
    }
  });
}

function renderizarLeaderboardMobile() {
  const container = document.getElementById('mLeaderboardBody');
  if (!container) return;

  const cod = AppState.regiaoSelecionada;
  const dados = cod === 'GERAL' ? AppState.dados.geral : AppState.dados.regionais[cod];

  if (!dados || !dados.top10 || dados.top10.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--md-text-muted); padding: 15px;">
        Nenhum colaborador nesta seleção.
      </div>
    `;
    return;
  }

  container.innerHTML = dados.top10.map(function(colab) {
    let rankIcon = colab.rank === 1 ? '🥇' : colab.rank === 2 ? '🥈' : colab.rank === 3 ? '🥉' : colab.rank;

    return `
      <div class="m-leaderboard-item">
        <div class="m-rank">${rankIcon}</div>
        <div class="m-colab-info">
          <div class="m-colab-name">${colab.nome}</div>
          <div class="m-colab-sub">⚡ SERV: ${colab.serv} | 🔌 RLGA: ${colab.rlga}</div>
        </div>
        <div class="m-total-badge">🏆 ${colab.total}</div>
      </div>
    `;
  }).join('');
}

function renderizarLeaderboardPioresMobile() {
  const container = document.getElementById('mLeaderboardPioresBody');
  if (!container) return;

  const cod = AppState.regiaoSelecionada;
  const dados = cod === 'GERAL' ? AppState.dados.geral : AppState.dados.regionais[cod];

  let piores = [];
  if (dados && dados.bottom10 && dados.bottom10.length > 0) {
    piores = dados.bottom10;
  } else if (dados && dados.top10) {
    piores = dados.top10.slice().sort(function(a, b) { return a.total - b.total; });
  }

  if (!piores || piores.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; color: var(--md-text-muted); padding: 15px;">
        Nenhum colaborador nesta seleção.
      </div>
    `;
    return;
  }

  container.innerHTML = piores.map(function(colab, idx) {
    const rankNum = idx + 1;
    const rankIcon = `🔻 ${rankNum}º`;

    return `
      <div class="m-leaderboard-item" style="background: rgba(239, 68, 68, 0.08);">
        <div class="m-rank-pior">${rankIcon}</div>
        <div class="m-colab-info">
          <div class="m-colab-name" style="color: #fecdd3;">${colab.nome}</div>
          <div class="m-colab-sub" style="color: #fca5a5;">⚡ SERV: ${colab.serv} | 🔌 RLGA: ${colab.rlga}</div>
        </div>
        <div class="m-total-badge m-total-badge-pior">🔻 ${colab.total}</div>
      </div>
    `;
  }).join('');
}
