/* ============================================================
   FAS Stüdyo — FolderPicker (paylaşılır klasör seçici popover)
   window.FolderPicker.open({ urunId, anchorEl, onChange })
   Anchored dropdown (buton altına çıpalı), modal DEĞİL.
   Ağaç (parent_id), satır = üyelik toggle, inline oluşturma (prompt YOK).
   Backend sözleşmeleri DEĞİŞMEZ. Tek instance. Bağımlılık: window.toast.
   ============================================================ */
(function () {
  'use strict';
  var ICONS = { folder:'#ic-folder', folderPlus:'#ic-folder-plus', chevron:'#ic-chevron-down',
    plus:'#ic-plus', check:'#ic-check', x:'#ic-x' };
  function escHtml(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  var escAttr = escHtml;
  function toast(m,t){ if(window.toast) window.toast(m,t||'info'); }
  function icon(id,cls,style){return '<svg class="icon'+(cls?' '+cls:'')+'"'+(style?' style="'+style+'"':'')+
    ' aria-hidden="true"><use href="'+id+'"/></svg>';}
  var active = null;

  function Inst(o){
    this.urunId=o.urunId; this.anchorEl=o.anchorEl;
    this.onChange=typeof o.onChange==='function'?o.onChange:function(){};
    this.albums=[]; this.memberIds=new Set(); this.collapsed=new Set();
    this.pinned=false; this.busyRows=new Set(); this.creating=false; this.createParent=undefined;
    this.root=null; this.panel=null;
    this._onDocClick=this._onDocClick.bind(this); this._onKey=this._onKey.bind(this);
    this._reposition=this._reposition.bind(this);
  }
  Inst.prototype.open=function(){
    this._build(); document.body.appendChild(this.root); this._reposition();
    setTimeout(function(){document.addEventListener('mousedown',this._onDocClick,true);}.bind(this),0);
    document.addEventListener('keydown',this._onKey,true);
    window.addEventListener('resize',this._reposition);
    window.addEventListener('scroll',this._reposition,true);
    if(this.anchorEl) this.anchorEl.setAttribute('aria-expanded','true');
    this.panel.focus(); this.refresh(true);
  };
  Inst.prototype.close=function(){
    document.removeEventListener('mousedown',this._onDocClick,true);
    document.removeEventListener('keydown',this._onKey,true);
    window.removeEventListener('resize',this._reposition);
    window.removeEventListener('scroll',this._reposition,true);
    if(this.root&&this.root.parentNode) this.root.parentNode.removeChild(this.root);
    if(this.anchorEl){ this.anchorEl.setAttribute('aria-expanded','false'); try{this.anchorEl.focus();}catch(e){} }
    if(active===this) active=null;
  };
  Inst.prototype._build=function(){
    var root=document.createElement('div'); root.className='studio fp-root'; root.setAttribute('role','presentation');
    var p=document.createElement('div'); p.className='fp-pop';
    p.setAttribute('role','dialog'); p.setAttribute('aria-modal','false');
    p.setAttribute('aria-label','Klasöre ekle'); p.setAttribute('tabindex','-1');
    p.innerHTML='<div class="fp-head"><span class="fp-title">'+icon(ICONS.folder)+'Klasöre ekle</span>'+
      '<button type="button" class="fp-x" aria-label="Kapat">'+icon(ICONS.x)+'</button></div>'+
      '<div class="fp-body" role="tree" aria-label="Klasörler"></div><div class="fp-foot"></div>';
    root.appendChild(p); this.root=root; this.panel=p;
    this.bodyEl=p.querySelector('.fp-body'); this.footEl=p.querySelector('.fp-foot');
    p.addEventListener('click',this._onPanelClick.bind(this));
    p.querySelector('.fp-x').addEventListener('click',this.close.bind(this));
  };
  Inst.prototype._reposition=function(){
    if(!this.panel||!this.anchorEl) return;
    var GAP=6,M=8, r=this.anchorEl.getBoundingClientRect(),
        vw=window.innerWidth,vh=window.innerHeight, pw=this.panel.offsetWidth,ph=this.panel.offsetHeight;
    var left=r.right-pw; if(left+pw>vw-M) left=vw-M-pw; if(left<M) left=M;
    var below=vh-r.bottom-GAP, top;
    if(ph<=below||below>=r.top-GAP) top=r.bottom+GAP; else top=Math.max(M,r.top-GAP-ph);
    this.panel.style.left=Math.round(left)+'px'; this.panel.style.top=Math.round(top)+'px';
  };
  Inst.prototype._onDocClick=function(e){
    if(this.root.contains(e.target)) return;
    if(this.anchorEl&&this.anchorEl.contains(e.target)) return;
    this.close();
  };
  Inst.prototype._onKey=function(e){
    if(e.key==='Escape'){ e.preventDefault();
      if(this.createParent!==undefined){ this._cancelCreate(); return; } this.close(); }
  };
  Inst.prototype.refresh=function(useCache){
    var self=this;
    if(useCache&&window.FolderPicker._cache){ self.albums=window.FolderPicker._cache.albums||[]; self.render(); }
    return fetch('/api/calisma/list',{headers:{'Accept':'application/json'}})
      .then(function(r){return r.json();}).then(function(d){
        if(!d||!d.ok){ self.render(); return; }
        self.albums=d.albums||[];
        var it=(d.items||[]).filter(function(i){return i.urun_id===self.urunId;})[0];
        self.memberIds=new Set((it&&it.album_ids)||[]); self.pinned=!!it;
        window.FolderPicker._cache={albums:self.albums}; self.render();
      }).catch(function(){ self.render(); });
  };
  Inst.prototype.childrenOf=function(pid){
    return this.albums.filter(function(a){return (a.parent_id||null)===(pid||null);})
      .sort(function(x,y){return String(x.name||'').localeCompare(String(y.name||''),'tr');});
  };
  Inst.prototype.nodeHtml=function(a,depth){
    var kids=this.childrenOf(a.id),hasKids=kids.length>0,open=!this.collapsed.has(a.id),
        isMember=this.memberIds.has(a.id),busy=this.busyRows.has(a.id),
        dot=a.color?'color:'+escAttr(a.color):'';
    var toggle=hasKids?'<button type="button" class="fp-toggle'+(open?' is-open':'')+
        '" data-toggle="'+escAttr(a.id)+'" aria-label="Aç/Kapat" tabindex="-1">'+icon(ICONS.chevron)+'</button>'
      :'<span class="fp-toggle-sp" aria-hidden="true"></span>';
    var html='<div class="fp-node" role="treeitem"'+(hasKids?' aria-expanded="'+(open?'true':'false')+'"':'')+
      ' aria-selected="'+(isMember?'true':'false')+'" style="--fp-depth:'+(depth||0)+'">'+
      '<div class="fp-row'+(isMember?' is-member':'')+(busy?' is-busy':'')+'" data-row="'+escAttr(a.id)+
        '" aria-busy="'+(busy?'true':'false')+'">'+ toggle +
        icon(ICONS.folder,'fp-folder-ic',dot)+
        '<span class="fp-name" title="'+escAttr(a.name)+'">'+escHtml(a.name)+'</span>'+
        '<span class="fp-cnt">'+(a.count||0)+'</span>'+
        '<button type="button" class="fp-row-add" data-add="'+escAttr(a.id)+
          '" title="Alt klasör ekle" aria-label="Alt klasör ekle" tabindex="-1">'+icon(ICONS.folderPlus)+'</button>'+
        '<span class="fp-check" aria-hidden="'+(isMember?'false':'true')+'">'+icon(ICONS.check)+'</span>'+
      '</div>';
    if(this.createParent===a.id) html+=this._createRowHtml(depth+1,true);
    if(hasKids&&open){ html+='<div class="fp-children" role="group">';
      for(var i=0;i<kids.length;i++) html+=this.nodeHtml(kids[i],(depth||0)+1); html+='</div>'; }
    return html+'</div>';
  };
  Inst.prototype._createRowHtml=function(depth,isSub){
    var ph=isSub?'Alt klasör adı…':'Klasör adı…';
    return '<div class="fp-create" style="--fp-depth:'+(depth||0)+'">'+
      '<input type="text" class="field fp-input" placeholder="'+ph+'" aria-label="'+(isSub?'Alt klasör adı':'Yeni klasör adı')+'" maxlength="80" autocomplete="off">'+
      '<button type="button" class="fp-create-ok" title="Oluştur" aria-label="Oluştur">'+icon(ICONS.check)+'</button>'+
      '<button type="button" class="fp-create-cancel" title="Vazgeç" aria-label="Vazgeç">'+icon(ICONS.x)+'</button></div>';
  };
  Inst.prototype.render=function(){
    if(!this.bodyEl) return;
    var roots=this.childrenOf(null);
    if(!roots.length&&this.createParent===undefined){
      this.bodyEl.innerHTML='<div class="fp-empty">'+icon(ICONS.folder,'fp-empty-ic')+
        '<p>Henüz klasör yok.<br>Aşağıdan ilk klasörünü oluştur.</p></div>';
    } else {
      var html=''; if(this.createParent===null) html+=this._createRowHtml(0,false);
      for(var i=0;i<roots.length;i++) html+=this.nodeHtml(roots[i],0); this.bodyEl.innerHTML=html;
    }
    this.footEl.innerHTML=(this.createParent===null)?''
      :'<button type="button" class="fp-newroot" data-newroot="1">'+icon(ICONS.plus)+'Yeni klasör</button>'+
       '<button type="button" class="btn btn-sm fp-done">Bitti</button>';
    var inp=this.bodyEl.querySelector('.fp-create .fp-input');
    if(inp){ inp.focus(); this._wireCreateInput(inp); }
    this._reposition();
  };
  Inst.prototype._wireCreateInput=function(inp){
    var self=this;
    inp.addEventListener('keydown',function(e){
      if(e.key==='Enter'){ e.preventDefault(); self._confirmCreate(inp.value); }
      else if(e.key==='Escape'){ e.preventDefault(); e.stopPropagation(); self._cancelCreate(); }
    });
  };
  Inst.prototype._onPanelClick=function(e){
    var t=e.target;
    if(t.closest('.fp-done')){ this.close(); return; }
    if(t.closest('.fp-newroot')){ this._openCreate(null); return; }
    if(t.closest('.fp-create-ok')){ var i=this.bodyEl.querySelector('.fp-create .fp-input'); this._confirmCreate(i?i.value:''); return; }
    if(t.closest('.fp-create-cancel')){ this._cancelCreate(); return; }
    var tog=t.closest('.fp-toggle');
    if(tog){ e.stopPropagation(); var id=tog.getAttribute('data-toggle');
      if(this.collapsed.has(id)) this.collapsed.delete(id); else this.collapsed.add(id); this.render(); return; }
    var add=t.closest('.fp-row-add');
    if(add){ e.stopPropagation(); var aid=add.getAttribute('data-add'); this.collapsed.delete(aid); this._openCreate(aid); return; }
    var row=t.closest('.fp-row'); if(row){ this._toggleMembership(row.getAttribute('data-row')); return; }
  };
  Inst.prototype._openCreate=function(pid){ this.createParent=pid; this.render(); };
  Inst.prototype._cancelCreate=function(){ this.createParent=undefined; this.render(); };
  Inst.prototype._confirmCreate=function(name){
    var self=this; name=(name||'').trim(); if(!name||this.creating) return; this.creating=true;
    var parentId=this.createParent;
    fetch('/api/calisma/album/ekle',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name:name,parent_id:parentId||null})})
      .then(function(r){return r.json();}).then(function(d){
        self.creating=false;
        if(!d||!d.ok){ toast((d&&d.error)||'Klasör oluşturulamadı','error'); return; }
        self.albums=d.albums||self.albums; window.FolderPicker._cache={albums:self.albums};
        self.createParent=undefined; if(parentId) self.collapsed.delete(parentId);
        self.render(); toast('"'+name+'" oluşturuldu','success');
        self.onChange({type:'create',pinned:self.pinned,albums:self.albums});
      }).catch(function(){ self.creating=false; toast('Bağlantı hatası','error'); });
  };
  Inst.prototype._toggleMembership=function(id){
    if(!id||this.busyRows.has(id)) return;
    if(this.memberIds.has(id)) this._remove(id); else this._add(id);
  };
  Inst.prototype._setBusy=function(id,on){ if(on)this.busyRows.add(id); else this.busyRows.delete(id); this.render(); };
  Inst.prototype._add=function(id){
    var self=this; this._setBusy(id,true); var wasPinned=this.pinned;
    fetch('/api/calisma/ekle',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({urun_id:self.urunId})}).then(function(r){return r.json();}).then(function(pd){
        if(pd&&pd.ok) self.pinned=true;
        return fetch('/api/calisma/urun-albume-ekle',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({urun_id:self.urunId,album_id:id})});
      }).then(function(r){return r.json();}).then(function(d){
        self._setBusy(id,false);
        if(!d||!d.ok){ toast((d&&d.error)||'Klasöre eklenemedi','error'); return; }
        self.memberIds=new Set(d.album_ids||[]); self.albums=d.albums||self.albums;
        window.FolderPicker._cache={albums:self.albums}; self.render(); toast('Klasöre eklendi','success');
        self.onChange({type:'add',albumId:id,pinned:self.pinned,justPinned:!wasPinned,albumIds:d.album_ids||[],albums:self.albums});
      }).catch(function(){ self._setBusy(id,false); toast('Bağlantı hatası','error'); });
  };
  Inst.prototype._remove=function(id){
    var self=this; this._setBusy(id,true);
    fetch('/api/calisma/urun-albume-cikar',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({urun_id:self.urunId,album_id:id})}).then(function(r){return r.json();}).then(function(d){
        self._setBusy(id,false);
        if(!d||!d.ok){ toast((d&&d.error)||'Çıkarılamadı','error'); return; }
        self.memberIds=new Set(d.album_ids||[]); self.albums=d.albums||self.albums;
        window.FolderPicker._cache={albums:self.albums}; self.render(); toast('Klasörden çıkarıldı','success');
        self.onChange({type:'remove',albumId:id,pinned:self.pinned,albumIds:d.album_ids||[],albums:self.albums});
      }).catch(function(){ self._setBusy(id,false); toast('Bağlantı hatası','error'); });
  };
  window.FolderPicker={ _cache:null,
    open:function(o){ o=o||{}; if(!o.urunId){ console.warn('FolderPicker: urunId gerekli'); return null; }
      if(active&&active.anchorEl===o.anchorEl){ active.close(); return null; }
      if(active) active.close(); active=new Inst(o); active.open(); return active; },
    close:function(){ if(active) active.close(); } };
})();
