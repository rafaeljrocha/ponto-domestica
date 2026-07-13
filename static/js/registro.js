(function () {
  const wrap = document.querySelector('.reg-wrap');
  const cfg = {
    lat: parseFloat(wrap.dataset.lat),
    lng: parseFloat(wrap.dataset.lng),
    raio: parseFloat(wrap.dataset.raio),
    selfie: wrap.dataset.selfie === '1',
  };
  const botao = document.getElementById('botao');
  const geoPill = document.getElementById('geo-pill');
  const geoTxt = document.getElementById('geo-txt');
  let pos = null; // {lat,lng,acc}

  // relógio
  function tick() {
    const d = new Date();
    document.getElementById('relogio').textContent = d.toLocaleTimeString('pt-BR');
  }
  setInterval(tick, 1000); tick();

  // haversine (só para exibir status ao usuário)
  function dist(aLat, aLng, bLat, bLng) {
    const R = 6371000, r = Math.PI / 180;
    const dLat = (bLat - aLat) * r, dLng = (bLng - aLng) * r;
    const s = Math.sin(dLat / 2) ** 2 +
      Math.cos(aLat * r) * Math.cos(bLat * r) * Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(s), Math.sqrt(1 - s));
  }

  function atualizaGeo() {
    if (!navigator.geolocation) {
      geoPill.className = 'pill out'; geoPill.textContent = 'sem GPS';
      geoTxt.textContent = 'este aparelho não informa a localização';
      return;
    }
    navigator.geolocation.watchPosition(function (p) {
      pos = { lat: p.coords.latitude, lng: p.coords.longitude, acc: p.coords.accuracy };
      if (!isNaN(cfg.lat)) {
        const d = dist(pos.lat, pos.lng, cfg.lat, cfg.lng);
        if (d <= cfg.raio) {
          geoPill.className = 'pill ok'; geoPill.textContent = 'na área';
          geoTxt.textContent = 'você está no local de trabalho';
        } else {
          geoPill.className = 'pill out'; geoPill.textContent = 'fora da área';
          geoTxt.textContent = 'a ' + Math.round(d) + ' m do local — o registro será marcado assim mesmo';
        }
      } else {
        geoPill.className = 'pill ok'; geoPill.textContent = 'localizado';
        geoTxt.textContent = 'posição capturada';
      }
    }, function () {
      geoPill.className = 'pill out'; geoPill.textContent = 'GPS negado';
      geoTxt.textContent = 'permita a localização para registrar com precisão';
    }, { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 });
  }
  atualizaGeo();

  async function tiraSelfie() {
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file'; input.accept = 'image/*'; input.capture = 'user';
      input.onchange = () => {
        const f = input.files[0];
        if (!f) return resolve(null);
        const rd = new FileReader();
        rd.onload = () => resolve(rd.result);
        rd.readAsDataURL(f);
      };
      input.click();
    });
  }

  botao.addEventListener('click', async function () {
    botao.disabled = true;
    let selfie = null;
    if (cfg.selfie) { selfie = await tiraSelfie(); }
    try {
      const resp = await fetch("/registro/marcar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lat: pos ? pos.lat : null,
          lng: pos ? pos.lng : null,
          selfie: selfie,
        }),
      });
      const j = await resp.json();
      if (j.ok) { mostraComprovante(j); }
      else { alert("Não foi possível registrar. Tente novamente."); botao.disabled = false; }
    } catch (e) {
      alert("Falha de conexão. Verifique a internet e tente de novo.");
      botao.disabled = false;
    }
  });

  function mostraComprovante(j) {
    document.getElementById('rc-tipo').textContent =
      (j.tipo === 'entrada' ? 'Entrada registrada' : 'Saída registrada');
    document.getElementById('rc-code').textContent = 'Comprovante ' + j.comprovante;
    document.getElementById('rc-nome').textContent = j.colaborador;
    document.getElementById('rc-hora').textContent = j.horario;
    const area = document.getElementById('rc-area');
    area.textContent = j.dentro_area ? 'Dentro da área' :
      ('Fora da área' + (j.distancia_m ? ' (' + Math.round(j.distancia_m) + ' m)' : ''));
    const stamp = document.getElementById('stamp');
    stamp.style.background = j.tipo === 'entrada' ? '#E4F0E9' : '#F5E4DF';
    stamp.style.color = j.tipo === 'entrada' ? '#2E7D5B' : '#B4462F';
    document.getElementById('receipt').classList.add('show');
    // recarrega após 1.4s para refletir o novo estado do botão e a lista
    setTimeout(() => location.reload(), 1600);
  }
})();
