(function(){
  // mobile menu
  var b=document.querySelector('.burger'), n=document.getElementById('nav');
  if(b&&n){b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o);document.body.style.overflow=o?'hidden':'';});}
  document.querySelectorAll('.nav button.dd').forEach(function(btn){
    btn.addEventListener('click',function(){var li=btn.parentElement;var o=li.classList.toggle('open');btn.setAttribute('aria-expanded',o);});
  });
  document.addEventListener('keydown',function(e){if(e.key==='Escape'){document.querySelectorAll('.has-sub.open').forEach(function(l){l.classList.remove('open')});if(n&&n.classList.contains('open')){b.click();}}});

  // YouTube facade: loads the privacy-friendly player only after a click
  var canEmbed=/^https?:$/.test(location.protocol)&&!/claude|anthropic|localhost$/.test(location.hostname)&&window.top===window.self;
  document.querySelectorAll('a.yt[data-yt]').forEach(function(a){
    a.addEventListener('click',function(e){
      if(!canEmbed) return; // falls back to opening YouTube
      e.preventDefault();
      var f=document.createElement('iframe');
      f.src='https://www.youtube-nocookie.com/embed/'+a.dataset.yt+'?autoplay=1&rel=0';
      f.allow='accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture';f.allowFullscreen=true;f.title=a.getAttribute('aria-label')||'Video';
      a.innerHTML='';a.appendChild(f);
    });
  });

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
