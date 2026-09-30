(function(){
  // mobile menu
  var b=document.querySelector('.burger'), n=document.getElementById('nav');
  if(b&&n){b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o);document.body.style.overflow=o?'hidden':'';});}
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
