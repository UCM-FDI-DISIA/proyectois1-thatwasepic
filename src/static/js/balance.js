// static/js/balance.js
(function () {
  const socket = window.socket || io();
  window.socket = socket;

  const salaId = window.salaId;
  const meId = Number(window.myId);

  function setHeaderBalance(v) {
    const el = document.getElementById('balance');
    if (el) { el.textContent = Number(v).toFixed(2); el.dataset.balance = v; }
  }

  // Entra a la sala al conectar
  socket.on('connect', () => {
    if (salaId) socket.emit('join_sala_blackjack', { sala_id: salaId });
  });

  // Estado completo de la mesa
  socket.on('estado_blackjack', (st) => {
    window.lastState = st;
    // si tienes un render propio, no lo toco:
    if (typeof window.render === 'function') window.render(st);
    if (typeof window.startCountdown === 'function') window.startCountdown(st);
    // sincroniza saldo encabezado
    if (st && st.jugadores && st.jugadores[meId]) {
      setHeaderBalance(st.jugadores[meId].balance);
    }
  });

  // Actualización puntual de saldo
  socket.on('balance_update', (p) => {
    if (p && typeof p.nuevo_balance !== 'undefined') {
      setHeaderBalance(p.nuevo_balance);
    }
  });

  // Helpers opcionales (si los llamas desde botones)
  window.apostarBJ  = (cantidad) => socket.emit('apostar_blackjack', { sala_id: salaId, cantidad });
  window.hitBJ      = () => socket.emit('hit_blackjack',   { sala_id: salaId });
  window.standBJ    = () => socket.emit('stand_blackjack', { sala_id: salaId });
  window.revanchaBJ = () => socket.emit('voto_revancha',   { sala_id: salaId });
})();
