(function(){
  // mobile menu
  var b=document.querySelector('.burger'), n=document.getElementById('nav');
  if(b&&n){
    b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o);b.setAttribute('aria-label',o?'Chiudi menu':'Menu');document.documentElement.style.overflow=o?'hidden':'';});
    n.addEventListener('click',function(e){ if(e.target.closest('a')&&n.classList.contains('open')) b.click(); });
    window.addEventListener('resize',function(){ if(n.classList.contains('open')&&getComputedStyle(b).display==='none') b.click(); });
  }
  document.querySelectorAll('.nav button.dd').forEach(function(btn){
    btn.addEventListener('click',function(){var li=btn.parentElement;var o=li.classList.toggle('open');btn.setAttribute('aria-expanded',o);});
  });
  document.addEventListener('keydown',function(e){if(e.key==='Escape'){document.querySelectorAll('.has-sub.open').forEach(function(l){l.classList.remove('open')});if(n&&n.classList.contains('open')){b.click();}}});

  // YouTube: niente viene caricato da Google finché non c'è il consenso "media"
  var canEmbed=/^https?:$/.test(location.protocol)&&!/claude|anthropic|localhost$/.test(location.hostname)&&window.top===window.self;
  var hasMedia=function(){return !!(window.URConsent&&window.URConsent.has('media'));};
  var vids=document.querySelectorAll('a.yt[data-yt]');
  function markReady(){ if(hasMedia()) vids.forEach(function(a){a.classList.add('is-ready');var c=a.querySelector('.yt-consent');if(c)c.remove();}); }
  function play(a){
    if(!canEmbed){ window.open(a.href,'_blank','noopener'); return; }
    var f=document.createElement('iframe');
    f.src='https://www.youtube-nocookie.com/embed/'+a.dataset.yt+'?autoplay=1&rel=0';
    f.allow='accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture';f.allowFullscreen=true;f.title=a.getAttribute('aria-label')||'Video';
    a.innerHTML='';a.appendChild(f);
  }
  vids.forEach(function(a){
    a.addEventListener('click',function(e){
      var t=e.target;
      if(t.closest('[data-yt-allow]')){ e.preventDefault(); window.URConsent&&window.URConsent.grant('media'); markReady(); play(a); return; }
      if(t.closest('[data-yt-out]')) return; // apre YouTube in una nuova scheda
      if(!hasMedia()){
        e.preventDefault();
        if(!a.querySelector('.yt-consent')){
          var d=document.createElement('span'); d.className='yt-consent';
          d.innerHTML='<div><span>Il video è ospitato da YouTube, che può usare cookie di terze parti.</span><span class="cc-row-btns"><button type="button" data-yt-allow>Attiva i video e guarda</button><span class="open" data-yt-out>Apri su YouTube</span></span></div>';
          a.appendChild(d);
        }
        return;
      }
      e.preventDefault(); play(a);
    });
  });
  markReady();
  document.addEventListener('ur:consent',markReady);

  // Contact forms: compose an email to the school (works on any static hosting)
  document.querySelectorAll('form.form').forEach(function(f){
    f.addEventListener('submit',function(e){
      e.preventDefault();
      if(!f.reportValidity()) return;
      var data=new FormData(f), lines=[], subj='Richiesta dal sito';
      data.forEach(function(v,k){ if(k==='privacy'||k==='form-name'||k==='sito-web') return; if(k==='Motivo del contatto') subj+=' – '+v; lines.push(k+': '+v); });
      var ok=f.parentElement.querySelector('.form-ok'), btn=f.querySelector('button[type=submit]');
      function mailFallback(){
        var href='mailto:info@uncensoredrunners.com?subject='+encodeURIComponent(subj)+'&body='+encodeURIComponent(lines.join('\n'));
        try{window.location.href=href;}catch(err){}
      }
      if(btn){btn.disabled=true;}
      // Netlify Forms: the message arrives by email to the school; on other hosts falls back to the visitor's mail app
      fetch('/',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(data).toString()})
        .then(function(r){ if(!r.ok) throw new Error(r.status); f.hidden=true; if(ok) ok.hidden=false; })
        .catch(function(){ if(btn) btn.disabled=false; mailFallback(); });
    });
  });
})();

// Apertura della home: foto a tutto schermo in dissolvenza, con barre di avanzamento, pausa, frecce e swipe
(function(){
  var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('[data-hero]').forEach(function(h){
    var s=[].slice.call(h.querySelectorAll('.hs')), d=[].slice.call(h.querySelectorAll('.hb-dot')), cap=h.querySelector('.hero-cap'), pb=h.querySelector('.hb-pause');
    var n=s.length; if(!n) return;
    var cur=0, paused=reduce, fallback=null;
    function preload(i){ var im=s[i%n].querySelector('img'); if(im&&im.loading==='lazy') im.loading='eager'; }
    function arm(){ // riavvia la barra della foto corrente
      clearTimeout(fallback);
      var dot=d[cur]; if(!dot) return;
      dot.classList.remove('is-on'); void dot.offsetWidth; dot.classList.add('is-on');
    }
    function show(i){
      s[cur].classList.remove('is-on'); s[cur].setAttribute('aria-hidden','true');
      cur=(i+n)%n;
      s[cur].classList.add('is-on'); s[cur].removeAttribute('aria-hidden');
      d.forEach(function(x,j){ x.classList.toggle('done',j<cur); x.classList.remove('is-on'); x.setAttribute('aria-current',j===cur?'true':'false'); });
      if(cap){ cap.classList.add('swap'); setTimeout(function(){ cap.textContent=s[cur].getAttribute('data-caption')||''; cap.classList.remove('swap'); },250); }
      arm(); preload(cur+1);
    }
    d.forEach(function(x,j){
      x.addEventListener('click',function(){ show(j); });
      x.addEventListener('animationend',function(){ if(j===cur&&!paused) show(cur+1); });
    });
    function setPaused(p){ paused=p; h.classList.toggle('is-paused',p); if(pb){ pb.setAttribute('aria-label',p?'Riprendi il carosello':'Metti in pausa il carosello'); pb.setAttribute('aria-pressed',p?'true':'false'); } }
    if(pb) pb.addEventListener('click',function(){ setPaused(!paused); if(!paused) arm(); });
    var pr=h.querySelector('.hb-prev'), nx=h.querySelector('.hb-next');
    if(pr) pr.addEventListener('click',function(){ show(cur-1); });
    if(nx) nx.addEventListener('click',function(){ show(cur+1); });
    var x0=null, y0=null;
    h.addEventListener('touchstart',function(e){ if(e.target.closest('a,button')) return; x0=e.touches[0].clientX; y0=e.touches[0].clientY; },{passive:true});
    h.addEventListener('touchend',function(e){ if(x0===null) return; var dx=e.changedTouches[0].clientX-x0, dy=e.changedTouches[0].clientY-y0; x0=null; if(Math.abs(dx)>50&&Math.abs(dx)>Math.abs(dy)) show(cur+(dx<0?1:-1)); },{passive:true});
    document.addEventListener('visibilitychange',function(){ h.classList.toggle('is-paused',paused||document.hidden); });
    setPaused(paused); show(0); preload(1);
  });
})();

// Comparsa dei contenuti e percorso che si disegna mentre si scorre
(function(){
  var root=document.documentElement;
  // nelle pagine interne marca da solo i blocchi principali
  var auto='.page-head .ph-text, .page-body > *, .card-list > *, .cols > .flow > *, .posts > .post-card, .post-list > .post-row, .article > .flow > *, .article .prose > figure, .pn > a';
  document.querySelectorAll(auto).forEach(function(el){
    if(el.hasAttribute('data-reveal')||el.closest('[data-reveal]')) return;
    el.setAttribute('data-reveal','');
    var sib=el.parentElement?[].slice.call(el.parentElement.children):[];
    var k=sib.indexOf(el); if(k>0&&k<6) el.style.setProperty('--d',k);
  });
  var els=document.querySelectorAll('[data-reveal], .trail, .step');
  if(!('IntersectionObserver' in window)){ els.forEach(function(el){el.classList.add('is-in');}); return; }
  var io=new IntersectionObserver(function(entries){
    entries.forEach(function(en){ if(en.isIntersecting){ en.target.classList.add('is-in'); io.unobserve(en.target); } });
  },{rootMargin:'0px 0px -10% 0px',threshold:0.08});
  els.forEach(function(el){ io.observe(el); });
  // sicurezza: se qualcosa non viene osservato (stampa, anteprime), dopo 4s mostra tutto ciò che è già sopra
  setTimeout(function(){ els.forEach(function(el){ if(el.getBoundingClientRect().top<innerHeight) el.classList.add('is-in'); }); },4000);
  root.classList.add('js');
})();

// Ombra dell'intestazione quando si scorre
(function(){
  var h=document.querySelector('.site-header'); if(!h) return;
  var on=false;
  function f(){ var s=window.scrollY>8; if(s!==on){ on=s; h.classList.toggle('is-scrolled',s); } }
  window.addEventListener('scroll',f,{passive:true}); f();
})();
