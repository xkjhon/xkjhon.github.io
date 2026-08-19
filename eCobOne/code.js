/* =============================================================
   eCobOne — code.js (Módulo de Dados, Notificações e Renderização)
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

const NOME_REGIAO = {
  GERAL: 'Visão Geral (Todas)',
  ANA: 'Anápolis',
  LUZ: 'Luziânia',
  FOR: 'Formosa',
  URU: 'Uruaçu',
  RVR: 'Rio Verde',
  MNH: 'Morrinhos'
};

document.addEventListener('DOMContentLoaded', () => {
  iniciarCronometro();
  carregarTudo();

  tentarTelaCheia();

  const entrarTelaCheiaPrimeiraInteracao = () => {
    tentarTelaCheia();
    document.removeEventListener('click', entrarTelaCheiaPrimeiraInteracao);
    document.removeEventListener('keydown', entrarTelaCheiaPrimeiraInteracao);
  };
  document.addEventListener('click', entrarTelaCheiaPrimeiraInteracao);
  document.addEventListener('keydown', entrarTelaCheiaPrimeiraInteracao);

  const btnFull = document.getElementById('btnFullscreen');
  if (btnFull) {
    btnFull.addEventListener('click', function(e) {
      e.stopPropagation();
      alternarTelaCheia();
    });
  }

  const btnRef = document.getElementById('btnRefresh');
  if (btnRef) {
    btnRef.addEventListener('click', function() {
      carregarTudo();
    });
  }
});

function tentarTelaCheia() {
  try {
    const elem = document.documentElement;
    if (!document.fullscreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement) {
      const promise = elem.requestFullscreen ? elem.requestFullscreen() :
                      elem.webkitRequestFullscreen ? elem.webkitRequestFullscreen() :
                      elem.msRequestFullscreen ? elem.msRequestFullscreen() : null;
      if (promise && promise.catch) {
        promise.catch(function() {});
      }
    }
  } catch (err) {}
}

function alternarTelaCheia() {
  if (document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement) {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    } else if (document.webkitExitFullscreen) {
      document.webkitExitFullscreen();
    } else if (document.msExitFullscreen) {
      document.msExitFullscreen();
    }
  } else {
    tentarTelaCheia();
  }
}

function iniciarCronometro() {
  if (AppState.timerInterval) clearInterval(AppState.timerInterval);
  AppState.countdownSecs = 30;
  
  const labelTimer = document.getElementById('timerLabel');
  
  AppState.timerInterval = setInterval(() => {
    AppState.countdownSecs--;
    if (labelTimer) labelTimer.textContent = `${AppState.countdownSecs}s`;
    
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
  renderizarDashboard();
}

function atualizarHorarioAtualizacao() {
  const elem = document.getElementById('lastUpdateLabel');
  if (elem) {
    if (AppState.dataAtualizacaoBase) {
      const partes = AppState.dataAtualizacaoBase.split(' ');
      const horaStr = partes.length > 1 ? partes[1] : AppState.dataAtualizacaoBase;
      elem.textContent = `Base: ${horaStr}`;
    } else {
      const agora = new Date();
      elem.textContent = `Base: ${agora.toLocaleTimeString('pt-BR')}`;
    }
  }
}

// -------------------------------------------------------------
// Carregamento de Avisos.txt
// -------------------------------------------------------------
async function carregarAvisos() {
  const rotas = [
    './Python-Updater/Files/Avisos.txt',
    './Files/Avisos.txt',
    'Avisos.txt'
  ];

  for (const path of rotas) {
    try {
      const res = await fetch(`${path}?t=${Date.now()}`);
      if (res.ok) {
        const texto = await res.text();
        AppState.avisos = texto.split('\n').map(l => l.trim()).filter(l => l);
        return;
      }
    } catch (e) {}
  }

  AppState.avisos = [];
}

function renderizarAvisos() {
  const container = document.getElementById('avisosContent');
  if (!container) return;

  const alertas = AppState.dados.alertas || [];
  const temAlertas = alertas.length > 0;

  // Alterna o Tema Amarelo da página inteira se houver religa em alerta
  document.body.classList.toggle('theme-alert-yellow', temAlertas);

  if (temAlertas) {
    container.innerHTML = alertas.map(item => {
      return `
        <div class="aviso-alert-card">
          <div class="alert-card-header">
            <span class="alert-ss-title">🐐 SS nº ${item.ss}</span>
            <span class="alert-tag">RELIGA EM ALERTA</span>
          </div>
          <div class="alert-colab-text">
            O colaborador <strong>${item.colab}</strong> tem uma Religa em Alerta!
          </div>
          <div class="alert-footer-action">
            ⏰ Vencimento: <strong style="color: #fde047; font-size: 0.88rem; background: rgba(0,0,0,0.35); padding: 2px 7px; border-radius: 4px;">${item.vencimento}h</strong> — Tratar quanto antes!
          </div>
        </div>
      `;
    }).join('');
    return;
  }

  // Se não houver alertas de religa, exibe o estado de notificações limpo
  container.innerHTML = `
    <div class="aviso-item" style="color: var(--md-text-muted); justify-content: center; padding: 16px 0;">
      <span class="aviso-bullet">🔔</span>
      <span>Nenhuma notificação ou alerta no momento.</span>
    </div>
  `;
}

// -------------------------------------------------------------
// Carregamento de Metas.txt
// -------------------------------------------------------------
async function carregarMetas() {
  const rotas = [
    './Python-Updater/Files/Metas.txt',
    './Files/Metas.txt',
    'Metas.txt'
  ];

  for (const path of rotas) {
    try {
      const res = await fetch(`${path}?t=${Date.now()}`);
      if (res.ok) {
        const texto = await res.text();
        const linhas = texto.split('\n');
        linhas.forEach(linha => {
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

// -------------------------------------------------------------
// Carregamento de dados.txt
// -------------------------------------------------------------
async function carregarDados() {
  const rotas = [
    './Python-Updater/Files/dados.txt',
    '../Python-Updater/Files/dados.txt',
    './Files/dados.txt',
    '../Files/dados.txt',
    'dados.txt'
  ];

  let carregou = false;

  for (const path of rotas) {
    try {
      const res = await fetch(`${path}?t=${Date.now()}`);
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

  blocos.forEach(blocoTexto => {
    const linhas = blocoTexto.split('\n').map(l => l.trim()).filter(l => l);
    if (linhas.length === 0) return;

    const cabecalho = linhas[0];

    if (cabecalho.toLowerCase().startsWith('atualizacao:')) {
      const val = cabecalho.replace(/^atualizacao:\s*/i, '').trim();
      AppState.dataAtualizacaoBase = val;
      return;
    }

    if (cabecalho.toLowerCase().startsWith('alertas:')) {
      linhas.slice(1).forEach(linha => {
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
      top10: []
    };

    linhas.slice(1).forEach(linha => {
      if (linha.startsWith('Serviços:')) {
        itemDados.servicos = parseInt(linha.replace('Serviços:', '').trim(), 10) || 0;
      } else if (linha.startsWith('Religas:')) {
        itemDados.religas = parseInt(linha.replace('Religas:', '').trim(), 10) || 0;
      } else if (linha.startsWith('NePago:')) {
        itemDados.nePago = parseInt(linha.replace('NePago:', '').trim(), 10) || 0;
      } else if (linha.startsWith('Faturamento:')) {
        itemDados.faturamento = linha.replace('Faturamento:', '').trim();
      } else if (linha.startsWith('EmCampo:')) {
        itemDados.emCampo = parseInt(linha.replace('EmCampo:', '').trim(), 10) || 0;
      } else if (/^\d+;/.test(linha)) {
        const partes = linha.split(';');
        if (partes.length >= 4) {
          itemDados.top10.push({
            rank: parseInt(partes[0], 10),
            nome: partes[1].trim(),
            serv: parseInt(partes[2], 10) || 0,
            rlga: parseInt(partes[3], 10) || 0,
            total: (parseInt(partes[2], 10) || 0) + (parseInt(partes[3], 10) || 0)
          });
        }
      }
    });

    if (cabecalho.toLowerCase().startsWith('geral:')) {
      AppState.dados.geral = itemDados;
    } else if (cabecalho.toLowerCase().startsWith('região:')) {
      let cod = 'OUT';
      if (cabecalho.includes('(ANA)')) cod = 'ANA';
      else if (cabecalho.includes('(LUZ)')) cod = 'LUZ';
      else if (cabecalho.includes('(FOR)')) cod = 'FOR';
      else if (cabecalho.includes('(URU)')) cod = 'URU';
      else if (cabecalho.includes('(RVR)')) cod = 'RVR';
      else if (cabecalho.includes('(MNH)')) cod = 'MNH';

      AppState.dados.regionais[cod] = itemDados;
    }
  });
}

function usarDadosFallback() {
  AppState.dados.geral = {
    servicos: 393,
    religas: 727,
    nePago: 38,
    faturamento: 'R$ 26.222,84',
    emCampo: 11745,
    top10: [
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
    ]
  };

  AppState.dados.regionais = {
    ANA: { servicos: 73, religas: 110, nePago: 3, faturamento: 'R$ 3.682,47', emCampo: 2223, top10: AppState.dados.geral.top10.slice(0, 5) },
    LUZ: { servicos: 180, religas: 240, nePago: 17, faturamento: 'R$ 7.496,36', emCampo: 4862, top10: AppState.dados.geral.top10.slice(0, 5) },
    FOR: { servicos: 0, religas: 76, nePago: 0, faturamento: 'R$ 0,00', emCampo: 950, top10: AppState.dados.geral.top10.slice(0, 5) },
    URU: { servicos: 10, religas: 53, nePago: 0, faturamento: 'R$ 0,00', emCampo: 552, top10: AppState.dados.geral.top10.slice(0, 5) },
    RVR: { servicos: 75, religas: 82, nePago: 12, faturamento: 'R$ 12.650,12', emCampo: 1287, top10: AppState.dados.geral.top10.slice(0, 5) },
    MNH: { servicos: 55, religas: 166, nePago: 6, faturamento: 'R$ 2.393,89', emCampo: 1871, top10: AppState.dados.geral.top10.slice(0, 5) }
  };
}

// -------------------------------------------------------------
// Renderização do Dashboard
// -------------------------------------------------------------
function renderizarDashboard() {
  renderizarAvisos();
  renderizarChipsFiltro();
  renderizarQuadrosMetricas();
  renderizarMetasEGrafico();
  renderizarLeaderboard();
}

function renderizarChipsFiltro() {
  const container = document.getElementById('regionChipsContainer');
  if (!container) return;

  const regioes = ['GERAL', 'ANA', 'LUZ', 'FOR', 'URU', 'RVR', 'MNH'];

  container.innerHTML = regioes.map(cod => {
    const isActive = AppState.regiaoSelecionada === cod;
    const rotulo = cod === 'GERAL' ? '🌐 Todas (Geral)' : NOME_REGIAO[cod];
    const tagMeta = cod !== 'GERAL' && AppState.metas[cod] ? `<span class="chip-tag">Meta ${AppState.metas[cod]}</span>` : '';

    return `
      <button class="chip ${isActive ? 'active' : ''}" onclick="selecionarRegiao('${cod}')">
        ${rotulo} ${tagMeta}
      </button>
    `;
  }).join('');
}

function selecionarRegiao(cod) {
  AppState.regiaoSelecionada = cod;
  renderizarDashboard();
}

function renderizarQuadrosMetricas() {
  const cod = AppState.regiaoSelecionada;
  const dados = cod === 'GERAL' ? AppState.dados.geral : AppState.dados.regionais[cod];

  if (!dados) return;

  const totalExecutado = dados.servicos + dados.religas;

  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  setVal('metricServicos', dados.servicos.toLocaleString('pt-BR'));
  setVal('metricReligas', dados.religas.toLocaleString('pt-BR'));
  setVal('metricNePago', dados.nePago.toLocaleString('pt-BR'));
  setVal('metricFaturamento', dados.faturamento);
  setVal('metricEmCampo', dados.emCampo.toLocaleString('pt-BR'));
  setVal('metricTotalExec', `${totalExecutado.toLocaleString('pt-BR')} total exec.`);
}

function renderizarMetasEGrafico() {
  const cod = AppState.regiaoSelecionada;
  
  let metaAlvo = 0;
  let realizadoAlvo = 0;

  if (cod === 'GERAL') {
    metaAlvo = Object.values(AppState.metas).reduce((a, b) => a + b, 0);
    const g = AppState.dados.geral;
    realizadoAlvo = g ? g.servicos : 0;
  } else {
    metaAlvo = AppState.metas[cod] || 0;
    const r = AppState.dados.regionais[cod];
    realizadoAlvo = r ? r.servicos : 0;
  }

  const pct = metaAlvo > 0 ? Math.min(Math.round((realizadoAlvo / metaAlvo) * 100), 100) : 0;

  const elemTitle = document.getElementById('metaTitle');
  if (elemTitle) elemTitle.textContent = cod === 'GERAL' ? 'Meta Global eCobOne' : `Meta — ${NOME_REGIAO[cod]}`;

  const elemPct = document.getElementById('globalPctLabel');
  if (elemPct) elemPct.textContent = `${pct}%`;

  const elemFill = document.getElementById('globalProgressBar');
  if (elemFill) elemFill.style.width = `${pct}%`;

  const elemStats = document.getElementById('globalStatsText');
  if (elemStats) {
    elemStats.innerHTML = `<span><strong>${realizadoAlvo.toLocaleString('pt-BR')}</strong> Realiz. (SERV)</span> <span>Meta: <strong>${metaAlvo.toLocaleString('pt-BR')}</strong></span>`;
  }

  const containerReg = document.getElementById('regionalGoalsGrid');
  if (containerReg) {
    const codigosReg = ['ANA', 'LUZ', 'FOR', 'URU', 'RVR', 'MNH'];
    containerReg.innerHTML = codigosReg.map(c => {
      const meta = AppState.metas[c] || 0;
      const d = AppState.dados.regionais[c];
      const real = d ? d.servicos : 0;
      const p = meta > 0 ? Math.min(Math.round((real / meta) * 100), 100) : 0;

      let statusBadge = p >= 100 ? '🏆 Batida' : p >= 60 ? '⚡ Em Progresso' : '🎯 Em Execução';

      return `
        <div class="regional-card">
          <div class="regional-card-top">
            <span class="regional-name">${NOME_REGIAO[c]}</span>
            <span class="regional-badge">${statusBadge}</span>
          </div>
          <div class="regional-progress-val">
            <span><strong>${real}</strong> / ${meta}</span>
            <span><strong>${p}%</strong></span>
          </div>
          <div class="regional-bar-bg">
            <div class="regional-bar-fill" style="width: ${p}%"></div>
          </div>
        </div>
      `;
    }).join('');
  }

  renderizarChartJs();
}

function renderizarChartJs() {
  const canvas = document.getElementById('goalsChart');
  if (!canvas || typeof Chart === 'undefined') return;

  const codigos = ['ANA', 'LUZ', 'FOR', 'URU', 'RVR', 'MNH'];
  const labels = codigos.map(c => NOME_REGIAO[c]);
  const metasData = codigos.map(c => AppState.metas[c] || 0);
  const realizadosData = codigos.map(c => {
    const d = AppState.dados.regionais[c];
    return d ? d.servicos : 0;
  });

  const isYellow = document.body.classList.contains('theme-alert-yellow');
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
          label: 'Meta Planejada',
          data: metasData,
          backgroundColor: metaBg,
          borderColor: metaBorder,
          borderWidth: 1.5,
          borderRadius: 6
        },
        {
          label: 'Realizado (Hoje)',
          data: realizadosData,
          backgroundColor: barColor,
          borderColor: barBorder,
          borderWidth: 1.5,
          borderRadius: 6
        }
      ]
    },
    options: {
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
          ticks: { color: labelColor, font: { family: 'Plus Jakarta Sans', size: 9, weight: '600' } },
          grid: { display: false }
        },
        y: {
          ticks: { color: labelColor, font: { size: 8 } },
          grid: { color: 'rgba(245, 158, 11, 0.15)' }
        }
      }
    }
  });
}

function renderizarLeaderboard() {
  const tbody = document.getElementById('leaderboardBody');
  if (!tbody) return;

  const cod = AppState.regiaoSelecionada;
  const dados = cod === 'GERAL' ? AppState.dados.geral : AppState.dados.regionais[cod];

  if (!dados || !dados.top10 || dados.top10.length === 0) {
    tbody.innerHTML = `
      <tr class="leaderboard-row">
        <td colspan="5" style="text-align: center; color: var(--md-text-muted); padding: 10px;">
          Nenhum colaborador nesta seleção.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = dados.top10.map(colab => {
    let rankClass = colab.rank === 1 ? 'rank-1' : colab.rank === 2 ? 'rank-2' : colab.rank === 3 ? 'rank-3' : '';
    let rankIcon = colab.rank === 1 ? '🥇' : colab.rank === 2 ? '🥈' : colab.rank === 3 ? '🥉' : colab.rank;

    return `
      <tr class="leaderboard-row">
        <td style="width: 30px;">
          <div class="rank-pill ${rankClass}">${rankIcon}</div>
        </td>
        <td>
          <div class="colab-name">${colab.nome}</div>
        </td>
        <td style="width: 70px;">
          <span class="val-badge val-serv">⚡ ${colab.serv}</span>
        </td>
        <td style="width: 70px;">
          <span class="val-badge val-rlga">🔌 ${colab.rlga}</span>
        </td>
        <td style="width: 70px;">
          <span class="val-badge val-total">🏆 ${colab.total}</span>
        </td>
      </tr>
    `;
  }).join('');
}
