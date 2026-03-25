var CS = {
    step:1, farmOpen:false,
    sel:[],
    wc:null, an:null,
    s5Data:null, s5Loading:false
};
var CS_STEPS=[
    {n:1,name:"Feasibility screening"},{n:2,name:"Crop selection & area"},
    {n:3,name:"Water feasibility check"},{n:4,name:"Portfolio review"},
    {n:5,name:"Crop characteristics"},{n:6,name:"Farm feasibility check"},
    {n:7,name:"Resource pressure"},{n:8,name:"Ecosystem impact"},
    {n:9,name:"Intercrop competition"},{n:10,name:"Microfeature conflicts"},
    {n:11,name:"Summary and make decisions"}
];
function cs_crop(id){return CS_CROPS.find(function(c){return c.id===id;});}
function cs_full(){return CS.sel.map(function(s){return Object.assign({},cs_crop(s.id),{a:s.a});});}

/* ── SELECTED CROPS SIDEBAR BOX (phase-aware) ──────────────── */
function cs_updateSelBox(){
    var box=document.getElementById("cs-selbox");
    if(box) box.innerHTML=cs_selBoxSidebarHtml();
}

function cs_selBoxSidebarHtml(){
    var phase=(typeof CS_ACTIVE_PHASE!=="undefined")?CS_ACTIVE_PHASE:1;

    function section(label,names,chipStyle){
        if(!names||!names.length) return '';
        return '<div style="margin-bottom:7px">'+
            '<div style="font-size:9px;font-weight:700;color:#5a7a4a;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:3px">'+label+'</div>'+
            '<div style="display:flex;flex-direction:column;gap:3px">'+
            names.map(function(n){
                return '<span style="font-size:11px;padding:2px 8px;border-radius:8px;display:block;'+chipStyle+'">'+n+'</span>';
            }).join('')+
            '</div></div>';
    }

    // Get main crop names — use CS.sel directly, or fall back to CS2.mainCrops in phase 2+
    // Get main crop names from CS.sel (phase 1 state)
    var mainNames=[];
    if(typeof CS!=="undefined" && CS.sel && typeof cs_crop==="function"){
        mainNames=CS.sel.map(function(s){
            var cr=cs_crop(s.id); return cr?cr.name:null;
        }).filter(Boolean);
    }
    // Fallback: use CS2.mainCrops if CS.sel is empty (e.g. arrived at phase 2 first)
    if(!mainNames.length && typeof CS2!=="undefined" && (CS2.mainCrops||[]).length)
        mainNames=CS2.mainCrops.map(function(cr){return cr.name;});

    if(!mainNames.length)
        return '<div style="font-size:11px;color:#8a9a7a;font-style:italic;padding:2px 0">No crops selected yet.</div>';

    // Phase 1: main crops only
    var html=section('Main Crops',mainNames,'background:#e8f5e2;color:#2d6a2d;border:1px solid #c8e6c0;');

    // Phase 2+: append associate, border, trap below main crops
    if(phase>=2&&typeof CS2!=="undefined"){
        var assocNames=(CS2.associateList||[]).filter(function(e){return(CS2.selectedAssoc||[]).indexOf(e.crop.id)>=0;}).map(function(e){return e.crop.name;});
        var borderNames=(CS2.borderList||[]).filter(function(e){return(CS2.selectedBorder||[]).indexOf(e.crop.id)>=0;}).map(function(e){return e.crop.name;});
        var trapNames=(CS2.trapList||[]).filter(function(e){return(CS2.selectedTrap||[]).indexOf(e.crop.id)>=0;}).map(function(e){return e.crop.name;});
        html+=section('Associate Crops',assocNames, 'background:#fff8e1;color:#7a4400;border:1px solid #ffe082;');
        html+=section('Border Crops',   borderNames, 'background:#f0f4e8;color:#3a5a2a;border:1px solid #c8d8b0;');
        html+=section('Trap Crops',     trapNames,   'background:#fdecea;color:#8b0000;border:1px solid #f5c6cb;');
    }

    // Phase 3+: append biodiversity below
    if(phase>=3&&typeof CS3!=="undefined"){
        // CS3.selected holds IDs; match against CS3.recommendations for names
        var bioNames=(CS3.selected||[]).map(function(id){
            var rec=(CS3.recommendations||[]).find(function(r){return r.crop.id===id;});
            return rec?rec.crop.name:null;
        }).filter(Boolean);
        html+=section('Biodiversity Crops',bioNames,'background:#f0e8f8;color:#5a1a8a;border:1px solid #d8b8f0;');
    }

    return html;
}


function cs_phase1_init(){
    var root=document.getElementById("cs-root"); if(!root)return;
    root.innerHTML="";
    root.appendChild(_cs_farmBox());
    root.appendChild(_cs_phaseTabs());
    var lay=document.createElement("div"); lay.className="cs-lay";
    lay.innerHTML='<div class="cs-sbar" id="cs-sbar"></div><div class="cs-sc" id="cs-content"></div>';
    root.appendChild(lay);
    cs_renderSidebar(); cs_renderStep(CS.step);
}

/* ── BASIC FARM SUMMARY (6 items, no CF table) ────────────────── */
function _cs_farmBasic(){
    var F=CS_FARM;
    var items=[
        {l:"Farm Area",          v:F.area+" ha"},
        {l:"Agro-climatic Zone", v:F.zone},
        {l:"Season",             v:F.season},
        {l:"Soil Type",          v:F.soil},
        {l:"Water Availability", v:F.waterAvail},
        {l:"Wind Exposure",      v:F.wind}
    ];
    var d=document.createElement("div");
    d.style.cssText="background:white;border-radius:10px;padding:10px 16px;margin-bottom:10px;border:1.5px solid var(--green-pale);display:flex;flex-wrap:wrap;gap:8px;align-items:center;";
    d.innerHTML='<span style="font-size:11px;font-weight:700;color:var(--green-dark);margin-right:4px;">Farm Context:</span>'+
        items.map(function(i){
            return '<span style="font-size:11px;color:#3a4a2a"><b style="color:var(--green-dark)">'+i.l+':</b> '+i.v+'</span>';
        }).join('<span style="color:var(--green-pale);margin:0 2px;">|</span>');
    return d;
}

/* ── FARM BOX ─────────────────────────────────────────────────── */
function _cs_farmBox(){
    var F=CS_FARM;
    var basic=[
        {l:"Farm Area",          v:F.area+" acres"},
        {l:"Agro-climatic Zone", v:F.zone},
        {l:"Season",             v:F.season},
        {l:"Soil Type / Texture",v:F.soil},
        {l:"Water Availability", v:F.waterAvail},
        {l:"Wind Exposure",      v:F.wind}
    ];
    var basicHtml=basic.map(function(i){
        return'<div class="cs-fbi"><div class="cs-fbi-l">'+i.l+'</div><div class="cs-fbi-v">'+i.v+'</div></div>';
    }).join("");

    function slabStyle(s){
        if(s<=1) return"background:#FCEBEB;color:#A32D2D";
        if(s===2) return"background:#FAEEDA;color:#854F0B";
        if(s===3) return"background:#fff3cd;color:#7a4400";
        if(s===4) return"background:#EAF3DE;color:#3B6D11";
        return"background:#C0DD97;color:#27500A";
    }

    var cfRows=CS_CF_ORDER.map(function(key){
        var cf=F.cf[key]; if(!cf) return"";
        return'<tr>'+
            '<td style="font-weight:600;color:var(--text-dark);white-space:nowrap;padding:6px 8px;border-bottom:1px solid var(--green-pale)">'+cf.l+'</td>'+
            '<td style="padding:6px 8px;border-bottom:1px solid var(--green-pale)"><span style="font-size:11px;font-weight:700;padding:2px 10px;border-radius:10px;'+slabStyle(cf.s)+'">'+cf.slab+'</span></td>'+
            '<td style="font-weight:700;color:var(--text-dark);padding:6px 8px;border-bottom:1px solid var(--green-pale)">'+cf.val+'</td>'+
        '</tr>';
    }).join("");

    var thBase='text-align:left;padding:7px 8px;font-size:10px;font-weight:700;border-bottom:2px solid var(--green-pale);white-space:nowrap;';
    var cfTable='<div style="overflow-x:auto;margin-top:14px">'+
        '<table style="width:100%;border-collapse:collapse;font-size:12px">'+
        '<thead><tr>'+
        '<th style="'+thBase+'color:#2a3a1a;background:var(--green-bg)">Context Feature</th>'+
        '<th style="'+thBase+'color:#2a3a1a;background:var(--green-bg)">Status</th>'+
        '<th style="'+thBase+'color:#2a3a1a;background:var(--green-bg)">Farm Value</th>'+
        '</tr></thead>'+
        '<tbody>'+cfRows+'</tbody></table></div>';

    var d=document.createElement("div"); d.className="cs-farm";
    var detailsDisplay = CS.farmOpen ? "block" : "none";
    d.innerHTML=
        '<div class="cs-farm-hd" onclick="cs_toggleFarm()">'+
            '<span class="cs-farm-hd-l">Farm Context</span>'+
            '<span id="cs-farr" style="color:#2a3a1a;font-weight:700">'+(CS.farmOpen?"▴ Context Features":"▾ Context Features")+'</span>'+
        '</div>'+
        '<div class="cs-farm-grid" style="margin-top:12px">'+basicHtml+'</div>'+
        '<div id="cs-fgrid" style="display:'+detailsDisplay+'">'+cfTable+'</div>';
    return d;
}
function cs_toggleFarm(){
    CS.farmOpen=!CS.farmOpen;
    var grid=document.getElementById("cs-fgrid");
    var arrow=document.getElementById("cs-farr");
    if(grid) grid.style.display=CS.farmOpen?"block":"none";
    if(arrow) arrow.textContent=CS.farmOpen?"▴ Context Features":"▾ Context Features";
}

/* ── PHASE TABS ───────────────────────────────────────────────── */
function _cs_phaseTabs(){
    var ph=[{n:1,l:"Main crop selection",a:true},{n:2,l:"Associate crops",a:false},{n:3,l:"Biodiversity crops",a:false},{n:4,l:"System evaluation",a:false}];
    var d=document.createElement("div"); d.className="cs-ptabs";
    d.innerHTML=ph.map(function(p){return'<button class="cs-ptab '+(p.a?"active":"")+' " onclick="cs_switchPhase('+p.n+')"><span class="cs-pnum">'+p.n+'</span>Phase '+p.n+': '+p.l+'</button>';}).join("");
    return d;
}

/* ── SIDEBAR ──────────────────────────────────────────────────── */
function cs_renderSidebar(){
    var sb=document.getElementById("cs-sbar"); if(!sb)return;
    var h='<div class="cs-sbar-hd">Phase 1 — steps</div>';
    CS_STEPS.forEach(function(s){
        var done=s.n<CS.step,cur=s.n===CS.step;
        h+='<div class="cs-si '+(done?"done":cur?"cur":"")+'" '+(done?'onclick="cs_goto('+s.n+')"':'')+'>'+
           '<div class="cs-si-n">'+(done?"✓":s.n)+'</div>'+
           '<div class="cs-si-nm">'+s.name+'</div></div>';
    });
    h+='<div style="margin-top:14px;padding-top:12px;border-top:1.5px solid var(--green-pale)">'+
       '<div style="font-size:10px;font-weight:700;color:var(--text-mid);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;padding:0 2px">Selected Crops</div>'+
       '<div id="cs-selbox">'+cs_selBoxSidebarHtml()+'</div>'+
       '</div>';
    sb.innerHTML=h;
}
function cs_renderStep(n){var el=document.getElementById("cs-content");if(!el)return;el.innerHTML=cs_buildStep(n);cs_renderSidebar();cs_updateSelBox();}
function cs_goto(n){if(n<=CS.step){CS.step=n;cs_renderStep(n);}}
function cs_invalidateStepData(step){
    if(step===1){
        CS.phase1Loaded=false;
        return;
    }
    if(step===5){
        CS.s5Data=null;
        return;
    }
    if(step===6||step===7||step===8||step===9||step===10){
        CS.an=CS.an||{};
        CS.an["s"+step]=null;
    }
}
function cs_next(){
    var nextStep=CS.step+1;
    cs_invalidateStepData(nextStep);
    CS.step=nextStep;
    cs_renderStep(CS.step);
}

/* ── STEP HEADER ──────────────────────────────────────────────── */
function cs_hd(n,title,desc){
    return'<div class="cs-bdg"><span class="cs-bdg-n">Step '+n+'</span><span class="cs-bdg-t">Phase 1 — main crop selection</span></div>'+
        '<div class="cs-ttl">'+title+'</div>'+
        (desc?'<div class="cs-dsc">'+desc+'</div>':'')+
        '<hr class="cs-hr">';
}
function cs_buildStep(n){
    var fns=[cs_s1,cs_s2,cs_s3,cs_s4,cs_s5,cs_s6,cs_s7,cs_s8,cs_s9,cs_s10,cs_s11];
    return fns[n-1]?fns[n-1]():"";
}

//TEMP_CROPS = [];

/* ── STEP 1 ───────────────────────────────────────────────────── */
function cs_s1(){
    if(!CS.phase1Loaded && !CS.phase1Loading){
        CS.phase1Loading=true;
        var farmPayload={
            area:CS_FARM.area,
            zone:CS_FARM.zone_code,
            season:CS_FARM.season_code,
            soil:CS_FARM.soil_code,
            waterAvail:CS_FARM.waterAvail,
            water_supply:CS_FARM.water_supply,
            wind:CS_FARM.wind,
            minTemp:CS_FARM.minTemp,
            maxTemp:CS_FARM.maxTemp
        };

        fetch("/api/method/rythulab.api.get_feasible_crops",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify(farmPayload)
        })
        .then(function(r){return r.json();})
        .then(function(res){
            var msg=res&&res.message?res.message:{};
            var crops=Array.isArray(msg)?msg:(Array.isArray(msg.crops)?msg.crops:[]);
            if(crops.length){
                CS_CROPS=crops;
                CS.phase1Loaded=true;
                if(CS.step===1) cs_renderStep(1);
            }
            else{
                CS_CROPS=CS_CROPS;
            }
        })
        .catch(function(err){
            console.warn("Feasible crops API failed, using local CS_CROPS.",err);
        })
        .finally(function(){
            CS.phase1Loading=false;
        });
    }

    function _cs_levelFromScore(score,fallbackBool){
        if(typeof score==="number" && !isNaN(score)){
            var lv=Math.round(score);
            if(lv<1) lv=1;
            if(lv>5) lv=5;
            return lv;
        }
        return fallbackBool?5:1;
    }

    function _cs_symbolForLevel(level){
        return ({1:"✕",2:"◔",3:"◑",4:"◕",5:"⬤"})[level]||"◑";
    }

    function _cs_styleForLevel(level){
        return ({
            1:"background:#fdecea;color:#8b0000;border:1px solid #f5c6cb;",
            2:"background:#fff3cd;color:#7a4400;border:1px solid #ffe082;",
            3:"background:#f3f6d9;color:#5b6d1f;border:1px solid #dce775;",
            4:"background:#e8f5e2;color:#2d6a2d;border:1px solid #c8e6c0;",
            5:"background:#dff3d3;color:#1f5b1f;border:1px solid #b5deb0;"
        })[level]||"background:#f3f6d9;color:#5b6d1f;border:1px solid #dce775;";
    }

    var cards=CS_CROPS.map(function(c){
        var hi=c.sc>=85,lo=c.sc<70;
        var pc=hi?"cs-p-hi":lo?"cs-p-lo":"cs-p-md";
        var fc=hi?"cs-sf-hi":lo?"cs-sf-lo":"cs-sf-md";
        var cks=[
            {k:"Season",score:c.season_score,fallback:c.sm},
            {k:"Zone",score:c.season_score,fallback:c.zm},
            {k:"Water",score:c.water_score,fallback:c.wm},
            {k:"Soil",score:c.soil_score,fallback:c.som},
            {k:"Temp",score:c.temperature_score,fallback:c.tm}
        ];
        return'<div class="cs-cc">'+
            '<div class="cs-cc-top"><div class="cs-cc-nm">'+c.name+'</div><span class="cs-pill '+pc+'">'+c.sc+'</span></div>'+
            '<div class="cs-cc-tp">'+c.type+'</div>'+
            '<div class="cs-sbar2"><div class="'+fc+'" style="width:'+c.sc+'%"></div></div>'+
            '<div class="cs-tags">'+cks.map(function(k){
                var lvl=_cs_levelFromScore(k.score,k.fallback);
                return'<span class="cs-t" title="'+k.k+' satisfaction: '+lvl+'/5" style="'+_cs_styleForLevel(lvl)+'">'+
                    '<span style="display:inline-flex;align-items:center;justify-content:center;width:10px;min-width:10px;font-size:10px;line-height:1;margin-right:4px;">'+_cs_symbolForLevel(lvl)+'</span>'+
                    k.k+
                '</span>';
            }).join('')+'</div>'+
        '</div>';
    }).join("");
    return cs_hd(1,"Feasibility screening",
        "Based on your farm's agro-climatic zone, season, soil type, temperature range, and water availability, crops are ranked by suitability score (0–100). Parameter chips show 5-level satisfaction (1=lowest, 5=highest). Your agronomic knowledge matters — you may select any crop regardless of score.")+
        '<div style="font-size:12px;color:#2a3a1a;margin-bottom:9px">'+CS_CROPS.length+' crops found — ranked by suitability score</div>'+
        '<div class="cs-cgrid">'+cards+'</div>'+
        '<div class="cs-sf"><span class="cs-fn"></span>'+
        '<button class="cs-btn pri" onclick="cs_next()">Proceed to crop selection →</button></div>';
}

/* ── STEP 2 — area in hectares, no Resources column ─────────── */
function cs_s2(){
    var tot=CS.sel.reduce(function(a,s){return a+parseFloat(s.a||0);},0);
    var pct=Math.min(100,(tot/CS_FARM.area)*100);
    var bc=tot>CS_FARM.area?"var(--csr400)":tot>CS_FARM.area*0.9?"var(--csa600)":"var(--csg400)";
    var rows=CS_CROPS.map(function(c){
        var s=CS.sel.find(function(x){return x.id===c.id;}),sel=!!s;
        var pc=c.sc>=85?"cs-p-hi":c.sc<70?"cs-p-lo":"cs-p-md";
        return'<tr>'+
            '<td><input type="checkbox" '+(sel?"checked":"")+' onchange="cs_toggleCrop(\''+c.id+'\',this.checked)"></td>'+
            '<td style="font-weight:700;color:var(--text-dark)">'+c.name+'</td>'+
            '<td style="color:#3a4a2a">'+c.type+'</td>'+
            '<td><span class="cs-pill '+pc+'">'+c.sc+'%</span></td>'+
            '<td style="color:var(--text-dark)">'+c.wr+'mm</td>'+
            '<td><input type="number" class="cs-ainp" id="csa-'+c.id+'" value="'+(s?s.a:"")+'" placeholder="0" min="0" max="'+CS_FARM.area+'" step="0.1" '+(sel?"":"disabled")+' onchange="cs_updateArea(\''+c.id+'\',this.value)"> ha</td>'+
        '</tr>';
    }).join("");
    return cs_hd(2,"Crop selection & area planning",
        "Select the crops you want to grow this season. For each selected crop, enter the area (hectares) you plan to allocate. Total must not exceed "+CS_FARM.area+" hectares.")+
        '<table class="cs-tbl"><thead><tr><th></th><th>Crop</th><th>Type</th><th>Score</th><th>Water req.</th><th>Area (ha)</th></tr></thead><tbody>'+rows+'</tbody></table>'+
        '<div class="cs-abar"><span style="color:#2a3a1a;white-space:nowrap">Area used:</span>'+
        '<div class="cs-abw"><div class="cs-abf" id="cs-abf" style="width:'+pct+'%;background:'+bc+'"></div></div>'+
        '<span style="font-size:13px;font-weight:700;color:var(--text-dark)" id="cs-atxt">'+tot.toFixed(1)+' / '+CS_FARM.area+' ha</span></div>'+
        '<div class="cs-sf"><span class="cs-fn" id="cs-snote">'+CS.sel.length+' crop(s) selected.</span>'+
        '<button class="cs-btn sec" onclick="cs_goto(1)">← Back</button>'+
        '<button class="cs-btn pri" onclick="cs_toWater()">Run water feasibility check →</button></div>';
}
function cs_toggleCrop(id,checked){
    if(checked){if(!CS.sel.find(function(s){return s.id===id;}))CS.sel.push({id:id,a:0});var e=document.getElementById("csa-"+id);if(e)e.disabled=false;}
    else{CS.sel=CS.sel.filter(function(s){return s.id!==id;});var e=document.getElementById("csa-"+id);if(e){e.disabled=true;e.value="";}}
    cs_abar();
}
function cs_updateArea(id,v){var s=CS.sel.find(function(x){return x.id===id;});if(s)s.a=parseFloat(v)||0;cs_abar();}
function cs_abar(){
    var tot=CS.sel.reduce(function(a,s){return a+parseFloat(s.a||0);},0);
    var pct=Math.min(100,(tot/CS_FARM.area)*100),ok=tot<=CS_FARM.area;
    var c=ok?(tot>CS_FARM.area*0.9?"var(--csa600)":"var(--csg400)"):"var(--csr400)";
    var abf=document.getElementById("cs-abf"),atx=document.getElementById("cs-atxt"),sn=document.getElementById("cs-snote");
    if(abf){abf.style.width=pct+"%";abf.style.background=c;}
    if(atx){atx.textContent=tot.toFixed(1)+" / "+CS_FARM.area+" ha";atx.style.color=c;}
    if(sn)sn.textContent=CS.sel.length+" crop(s) selected."+(ok?"":" Area exceeds farm size.");
    cs_updateSelBox();
}
function cs_toWater(){
    var tot=CS.sel.reduce(function(a,s){return a+parseFloat(s.a||0);},0);
    if(!CS.sel.length){alert("Select at least one crop.");return;}
    if(tot<=0){alert("Enter area for each selected crop.");return;}
    cs_calcWater();cs_next();
}

/* ── STEP 3 — two-line formula ───────────────────────────────── */
function cs_calcWater(){
    var F=CS_FARM,crops=cs_full(),ta=crops.reduce(function(a,c){return a+c.a;},0),ws=0;
    crops.forEach(function(c){ws+=c.wr*(c.a/ta);});
    var req=ws*0.8;
    CS.wc={ok:req<=F.wa,req:Math.round(req),avl:F.wa,ws:Math.round(ws),
        bd:crops.map(function(c){return{nm:c.name,wr:c.wr,sh:+(c.a/ta*100).toFixed(1),cn:Math.round(c.wr*(c.a/ta))};})};
}
function cs_s3(){
    if(!CS.wc)cs_calcWater();
    var w=CS.wc,F=CS_FARM;
    var bd=w.bd.map(function(b){
        return'<div class="cs-fcr"><span class="cs-fcrl">'+b.nm+' ('+b.sh+'% of area)</span><span class="cs-fcrv">'+b.cn+'mm</span></div>';
    }).join("");
    return cs_hd(3,"Water feasibility check",
        "Verifying whether the farm's total water supply can meet the aggregate demand of all selected crops.")+
        '<div class="cs-fcrd"><div class="cs-fcht">Formula</div>'+
        '<div class="cs-fcfm">Σ (CropWaterRequirement × AreaShare) × WMF (0.8) ≤ Farm Water Availability</div>'+
        '<div class="cs-fcfm" style="margin-top:4px;font-size:12px;opacity:0.85">Farm Water Availability = (SeasonalRainfall × RainfallEfficiency) + IrrigationWater + SoilStoredWater</div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">Seasonal rainfall × efficiency ('+F.rain+'mm × '+F.re+')</span><span class="cs-fcrv">'+Math.round(F.rain*F.re)+'mm</span></div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">Irrigation water</span><span class="cs-fcrv">'+F.irr+'mm</span></div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">Soil stored water</span><span class="cs-fcrv">'+F.sw+'mm</span></div>'+
        '<div class="cs-fcr"><span class="cs-fcrl"><strong>Total farm water available</strong></span><span class="cs-fcrv"><strong>'+w.avl+'mm</strong></span></div></div>'+
        '<div class="cs-fcrd"><div class="cs-fcht">Crop demand breakdown</div>'+bd+
        '<div class="cs-fcr"><span class="cs-fcrl">Weighted average water requirement</span><span class="cs-fcrv">'+w.ws+'mm</span></div>'+
        '<div class="cs-fcr"><span class="cs-fcrl"><strong>× WMF 0.8 = system water requirement</strong></span><span class="cs-fcrv"><strong>'+w.req+'mm required</strong></span></div></div>'+
        '<div class="cs-vcrd '+(w.ok?"cs-vc-ok":"cs-vc-warn")+'">'+
        '<div class="cs-vci '+(w.ok?"cs-vci-ok":"cs-vci-warn")+'">'+(w.ok?"✓":"!")+'</div>'+
        '<div><div class="cs-vttl">'+(w.ok?"System is water feasible ✓":"Water demand exceeds availability")+'</div>'+
        '<div class="cs-vmsg">'+(w.ok?
            "Your crop system requires ~"+w.req+"mm — within the farm's available "+w.avl+"mm.":
            "System demands ~"+w.req+"mm but only "+w.avl+"mm available. Please revise your crop selection or reduce area of high water demand crops.")+
        '</div></div></div>'+
        '<div class="cs-sf"><span class="cs-fn"></span>'+
        '<button class="cs-btn sec" onclick="cs_goto(2)">← Back</button>'+
        '<button class="cs-btn pri" onclick="cs_next()">Portfolio review →</button></div>';
}

/* ── STEP 4 — High water demand, no N-fixing, no Resources/Root depth ── */
function cs_s4(){
    var crops=cs_full(),ta=crops.reduce(function(a,c){return a+c.a;},0);
    var bars=crops.map(function(c){
        var pct=ta>0?(c.a/ta*100):0;
        return'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'+
            '<span style="font-size:12px;min-width:140px;color:var(--text-dark)">'+c.name+'</span>'+
            '<div style="flex:1;background:#ccdcc0;border-radius:3px;height:14px;overflow:hidden">'+
            '<div style="width:'+pct+'%;height:100%;background:var(--csg400);border-radius:3px;display:flex;align-items:center;padding:0 5px">'+
            '<span style="font-size:10px;color:white;white-space:nowrap">'+c.a.toFixed(1)+'ha</span></div></div>'+
            '<span style="font-size:11px;color:#2a3a1a;min-width:32px;text-align:right">'+pct.toFixed(0)+'%</span></div>';
    }).join("");
    var stickyTd='position:sticky;left:0;z-index:1;background:white;';
    var stickyTh='position:sticky;left:0;z-index:2;background:#e8f5e2;';
    var rows=crops.map(function(c){
        return'<tr><td style="'+stickyTd+'font-weight:700;white-space:nowrap">'+c.name+'</td><td style="color:#3a4a2a">'+c.type+'</td>'+
            '<td>'+c.a.toFixed(1)+' ha</td><td>'+Math.round(c.a/ta*100)+'%</td>'+
            '<td>'+c.wr+'mm</td></tr>';
    }).join("");
    var nhi=crops.filter(function(c){return c.res==="High";}).length;
    return cs_hd(4,"Portfolio review",null)+
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">'+
        '<div class="cs-fcrd"><div class="cs-fcht">Area allocation</div>'+bars+
        '<div style="font-size:11px;color:#2a3a1a;margin-top:6px">Total: '+ta.toFixed(1)+' / '+CS_FARM.area+' ha</div></div>'+
        '<div class="cs-fcrd"><div class="cs-fcht">Portfolio summary</div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">Crops selected</span><span class="cs-fcrv">'+crops.length+'</span></div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">Total area</span><span class="cs-fcrv">'+ta.toFixed(1)+' ha</span></div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">Water feasibility</span><span class="cs-fcrv" style="color:'+(CS.wc&&CS.wc.ok?"var(--csg600)":"var(--csr600)")+'">'+( CS.wc&&CS.wc.ok?"Feasible ✓":"At risk !")+'</span></div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">High water demand crops</span><span class="cs-fcrv">'+nhi+'</span></div></div></div>'+
        '<div style="overflow-x:auto"><table class="cs-dtbl"><thead><tr>'+
        '<th style="'+stickyTh+'">Crop</th><th>Type</th><th>Area (ha)</th><th>Area %</th><th>Water req.</th>'+
        '</tr></thead><tbody>'+rows+'</tbody></table></div>'+
        '<div class="cs-sf"><span class="cs-fn"></span>'+
        '<button class="cs-btn sec" onclick="cs_goto(2)">← Revise</button>'+
        '<button class="cs-btn pri" onclick="cs_runAnalysis()">Run full analysis →</button></div>';
}

/* ── Fetch Phase 1 Step 5 crop characteristics from backend ─── */
function cs_fetchS5(){
    if(CS.s5Loading) return;
    CS.s5Loading = true;
    var ids = CS.sel.map(function(s){ return s.id; });
    fetch("/api/method/rythulab.api.get_phase1_crop_characteristics", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({crop_ids: ids})
    })
    .then(function(r){ return r.json(); })
    .then(function(res){
        var msg = res && res.message ? res.message : {};
        if(msg.ok && msg.characteristics){
            CS.s5Data = msg.characteristics;
        }
    })
    .catch(function(err){
        console.warn("Phase 1 Step 5 characteristics fetch failed:", err);
    })
    .finally(function(){
        CS.s5Loading = false;
        if(CS.step === 5) cs_renderStep(5);
    });
}

/* ── STEP 5 — frozen first row ───────────────────────────────── */
function cs_s5(){
    if(!CS.s5Data && !CS.s5Loading) cs_fetchS5();

    var charMap = CS.s5Data || {};
    var crops = cs_full().map(function(c){
        var ch = charMap[c.id] || {};
        var baseSens = {ph:'',temp:'',water:'',heat:'',frost:'',airflow:'',subm:'',extreme:''};
        return Object.assign(
            {temp:'',pH_r:'',hum:'',rootD:'',rd:'',cSpread:'',cNature:'',gHabit:'',
             crit:'',alelo:'',nFix:'',shadeTol:0,windTol:'',sal:'',family:'',
             pests:[],frostSens:'',sens:baseSens},
            c,
            ch,
            {sens: Object.assign({}, baseSens, c.sens||{}, ch.sens||{})}
        );
    });

    if(!CS.s5Data && CS.s5Loading){
        return cs_hd(5,"Crop characteristics",
            "All agronomic characteristics for selected crops. Sensitivity levels — High / Very High: highly vulnerable (red), Medium: moderate risk (amber), Low: tolerant (green).")+
            '<div class="cs-empty" style="padding:32px;text-align:center;color:#8a9a7a">Loading crop characteristics from database…</div>'+
            '<div class="cs-sf"><span class="cs-fn"></span>'+
            '<button class="cs-btn sec" onclick="cs_goto(4)">← Back</button>'+
            '<button class="cs-btn pri" onclick="cs_next()">Run feasibility check →</button></div>';
    }

    function sv(v){
        if(!v||v==="-")return'<span style="color:#2a3a1a">—</span>';
        var hi=v==="High"||v==="Very High";
        var md=v==="Medium";
        return'<span style="'+(hi?"color:var(--csr600);font-weight:700":md?"color:var(--csa600);font-weight:700":"color:var(--csg600)")+'">'+v+'</span>';
    }
    var rows=crops.map(function(c){
        return'<tr>'+
        '<td style="position:sticky;left:0;z-index:1;background:white;white-space:nowrap;font-weight:700">'+c.name+'</td>'+
        '<td style="white-space:nowrap">'+c.temp+'</td>'+
        '<td>'+c.pH_r+'</td>'+
        '<td>'+c.hum+'</td>'+
        '<td>'+c.wr+'</td>'+
        '<td>'+c.rootD+'</td>'+
        '<td>'+c.h+'</td>'+
        '<td>'+c.cSpread+'</td>'+
        '<td style="white-space:nowrap;font-size:11px">'+c.cNature+'</td>'+
        '<td style="font-size:11px">'+c.gHabit+'</td>'+
        '<td style="color:var(--csr600);font-weight:700;white-space:nowrap">'+c.crit+'</td>'+
        '<td>'+c.alelo+'</td>'+
        '<td>'+c.nFix+'</td>'+
        '<td>'+c.shadeTol+'%</td>'+
        '<td>'+c.windTol+'</td>'+
        '<td>'+c.sal+'</td>'+
        '<td style="white-space:nowrap;font-size:11px">'+c.family+'</td>'+
        '<td style="font-size:10px;max-width:200px">'+(c.pests||[]).join("; ")+'</td>'+
        '<td>'+c.frostSens+'</td>'+
        '<td>'+sv(c.sens.ph)+'</td>'+
        '<td>'+sv(c.sens.temp)+'</td>'+
        '<td>'+sv(c.sens.water)+'</td>'+
        '<td>'+sv(c.sens.heat)+'</td>'+
        '<td>'+sv(c.sens.frost)+'</td>'+
        '<td>'+sv(c.sens.airflow)+'</td>'+
        '<td>'+sv(c.sens.subm)+'</td>'+
        '<td>'+sv(c.sens.extreme)+'</td>'+
        '</tr>';
    }).join("");

    var stickyRow='position:sticky;top:0;z-index:2;';
    var stickyCol='position:sticky;left:0;z-index:3;';  // Crop column: sticky both ways
    var thBase='text-align:left;padding:7px 8px;font-size:10px;font-weight:700;white-space:nowrap;border-bottom:2px solid var(--green-pale);';
    var thCrop=thBase+'background:#e8f5e2;color:#2a3a1a;'+stickyRow+stickyCol;
    var thDark=thBase+'background:#f0f5ec;color:#2a3a1a;'+stickyRow;

    return cs_hd(5,"Crop characteristics",
        "All agronomic characteristics for selected crops. Sensitivity levels — High / Very High: highly vulnerable (red), Medium: moderate risk (amber), Low: tolerant (green).")+
        '<div style="overflow:auto;max-height:420px;border:1px solid var(--green-pale);border-radius:8px;">'+
        '<table class="cs-dtbl" style="min-width:2000px"><thead><tr>'+
        '<th style="'+thCrop+'">Crop</th><th style="'+thDark+'">Temp</th><th style="'+thDark+'">pH</th><th style="'+thDark+'">Humidity</th>'+
        '<th style="'+thDark+'">Water (mm/season/Ha)</th><th style="'+thDark+'">Root Depth</th><th style="'+thDark+'">Height (m)</th>'+
        '<th style="'+thDark+'">Canopy Spread (m)</th><th style="'+thDark+'">Canopy Nature</th><th style="'+thDark+'">Growth Habit</th>'+
        '<th style="'+thDark+'">Critical Parameters</th><th style="'+thDark+'">Allelopathy</th><th style="'+thDark+'">N-Fixation</th>'+
        '<th style="'+thDark+'">Shade Tol (%)</th><th style="'+thDark+'">Wind Tol</th><th style="'+thDark+'">Salinity (dS/m)</th>'+
        '<th style="'+thDark+'">Crop Family</th><th style="'+thDark+'">Common Pest</th><th style="'+thDark+'">Frost Sens</th>'+
        '<th style="'+thDark+'">Soil pH Sensitivity</th><th style="'+thDark+'">Temp Range Sensitivity</th>'+
        '<th style="'+thDark+'">Water Sensitivity</th><th style="'+thDark+'">Heat Sensitivity</th><th style="'+thDark+'">Frost Sensitivity</th>'+
        '<th style="'+thDark+'">Airflow Sensitivity</th><th style="'+thDark+'">Submergence Sensitivity</th>'+
        '<th style="'+thDark+'">Extreme Weather Sensitivity</th>'+
        '</tr></thead><tbody>'+rows+'</tbody></table></div>'+
        '<div class="cs-sf"><span class="cs-fn"></span>'+
        '<button class="cs-btn sec" onclick="cs_goto(4)">← Back</button>'+
        '<button class="cs-btn pri" onclick="cs_next()">Run feasibility check →</button></div>';
}

/* ── ANALYSIS ENGINE ──────────────────────────────────────────── */
function cs_runAnalysis(){cs_calcAnalysis();cs_next();}
function cs_calcAnalysis(){
    var c=cs_full();
    CS.an={s6:null,s7:null,s8:null,s9:null,s10:null};
}
function _ck6(cr){
    var F=CS_FARM;
    return cr.map(function(c){
        var phMin=parseFloat((c.pH_r||"5–8").replace("–","-").split(/[-–]/)[0]);
        var phMax=parseFloat((c.pH_r||"5–8").replace("–","-").split(/[-–]/)[1]);
        var farmPH=parseFloat(F.cf.pH.val);
        return{crop:c,checks:[
            {k:"Soil pH",    ok:farmPH>=phMin&&farmPH<=phMax, det:"Farm pH "+F.cf.pH.val+", crop needs "+c.pH_r,              sv:true},
            {k:"Temperature",ok:F.cf.TMP.s>=3,               det:"Farm temp suitability "+F.cf.TMP.val+" from optimum; crop critical: "+c.crit, sv:true},
            {k:"Water",      ok:F.wa>=c.wr*0.65,              det:"Farm has "+F.wa+"mm available, crop needs ~"+c.wr+"mm/season", sv:false},
            {k:"Season",     ok:!!c.sm,                       det:"Kharif season compatibility",                               sv:true},
            {k:"Zone",       ok:!!c.zm,                       det:"SAT zone compatibility",                                    sv:true}
        ]};
    });
}
function _ck7(cr){
    var F=CS_FARM,ws=[];
    cr.forEach(function(c){
        if(c.res==="High"&&F.cf.N.s<=2)
            ws.push({cn:c.name,t:"warn",m:c.name+' — Resource demand is High and farm Available Nitrogen CF is "'+F.cf.N.slab+'" (≤ Weak). Nitrogen depletion risk.'});
    });
    return ws;
}
function _ck8(cr){
    var F=CS_FARM,ws=[];
    cr.forEach(function(c){
        if((c.mfr||[]).indexOf("high_moisture")>=0&&F.cf.W.s<=3)
            ws.push({cn:c.name,m:c.name+' produces requirement for MF "high moisture". Farm Water Availability CF is "'+F.cf.W.slab+'" (value: '+F.cf.W.val+') — already '+F.cf.W.slab+'. This crop will deteriorate this CF further. Hence revise.'});
        if((c.mfr||[]).indexOf("nitrogen_rich")>=0&&F.cf.N.s<=2)
            ws.push({cn:c.name,m:c.name+' produces requirement for MF "nitrogen-rich soil". Farm Available Nitrogen CF is "'+F.cf.N.slab+'" (value: '+F.cf.N.val+' kg/ha) — already Weak. This crop will worsen nitrogen depletion. Hence revise.'});
        if((c.mfs||[]).indexOf("pollinator_habitat")>=0&&F.cf.PA.s<=3)
            ws.push({cn:c.name,m:c.name+' suppresses MF "pollinator habitat". Farm Pollinator Activity CF is "'+F.cf.PA.slab+'" — this crop reduces it further. Hence revise.'});
    });
    return ws;
}
function _ck9(cr){
    var cf=[];
    for(var i=0;i<cr.length;i++){
        for(var j=i+1;j<cr.length;j++){
            var a=cr[i],b=cr[j];
            if(a.rd==="Deep"&&b.rd==="Deep")
                cf.push({a:a.name,b:b.name,t:"Root",m:a.name+" and "+b.name+" have root competition — both have deep root systems. Competition for deep soil moisture and nutrients likely."});
            if(a.rd==="Shallow"&&b.rd==="Shallow")
                cf.push({a:a.name,b:b.name,t:"Root",m:a.name+" and "+b.name+" have root competition — both have shallow roots. Surface nutrient and moisture competition likely."});
            if(a.h>0&&b.h>0&&Math.abs(a.h-b.h)<=0.5&&a.h>0.8&&b.h>0.8)
                cf.push({a:a.name,b:b.name,t:"Canopy",m:a.name+" and "+b.name+" have canopy competition — similar heights ("+a.h+"m vs "+b.h+"m). Light competition in adjacent rows likely."});
            var sh=(a.pests||[]).filter(function(p){
                return(b.pests||[]).some(function(bp){
                    var pa=p.split(" ")[0],pb=bp.split(" ")[0];
                    return pa===pb||p.indexOf(pb)>=0||bp.indexOf(pa)>=0;
                });
            });
            if(sh.length)
                cf.push({a:a.name,b:b.name,t:"Pest",m:a.name+" and "+b.name+" have pest-host competition — shared pest relationships. Co-planting may amplify field-level pest pressure."});
        }
    }
    return cf;
}
function _ck10(cr){
    var cf=[],req=[],sup=[];
    cr.forEach(function(c){(c.mfr||[]).forEach(function(m){req.push({m:m,cn:c.name});});});
    cr.forEach(function(c){(c.mfs||[]).forEach(function(m){sup.push({m:m,cn:c.name});});});
    req.forEach(function(r){sup.forEach(function(s){
        if(r.m===s.m&&r.cn!==s.cn)
            cf.push({nc:r.cn,sc:s.cn,mf:r.m,
                msg:r.cn+' requires MF "'+cs_mfl(r.m)+'", but '+s.cn+' suppresses this same MF. '+
                    'Required MF ∩ Suppress MF is not empty — conflict between '+r.cn+' (requires) and '+s.cn+' (suppresses). Note the warning with reason.'});
    });});
    return cf;
}

/* ── STEP 6 ───────────────────────────────────────────────────── */
function cs_buildS6Payload(){
    var farmCFs={};
    Object.keys(CS_FARM.cf||{}).forEach(function(key){
        var cf=CS_FARM.cf[key]||{};
        farmCFs[key]={
            l:cf.l,
            unit:cf.unit,
            val:cf.val,
            s:cf.s,
            slab:cf.slab
        };
    });

    return {
        selected_crops: cs_full().map(function(c){
            return {
                id:c.id,
                cropid:c.cropid||c.id,
                name:c.name,
                type:c.type,
                a:c.a
            };
        }),
        farm_cfs: farmCFs,
        farm_context: {
            area: CS_FARM.area,
            zone: CS_FARM.zone_code||CS_FARM.zone,
            season: CS_FARM.season_code||CS_FARM.season,
            soil: CS_FARM.soil_code||CS_FARM.soil,
            waterAvail: CS_FARM.waterAvail,
            water_supply: CS_FARM.water_supply,
            wind: CS_FARM.wind,
            minTemp: CS_FARM.minTemp,
            maxTemp: CS_FARM.maxTemp,
            rain: CS_FARM.rain,
            re: CS_FARM.re,
            irr: CS_FARM.irr,
            sw: CS_FARM.sw
        }
    };
}

function cs_fetchS6Analysis(){
    if(CS.s6Loading) return;

    CS.s6Loading=true;
    CS.s6Error=null;

    fetch("/api/method/rythulab.api.get_phase1_farm_feasibility",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(cs_buildS6Payload())
    })
    .then(function(r){return r.json();})
    .then(function(res){
        var msg=res&&res.message?res.message:{};
        CS.an=CS.an||{};
        CS.an.s6=Array.isArray(msg.results)?msg.results:[];
    })
    .catch(function(err){
        console.warn("Step 6 backend check failed, using local fallback.",err);
        CS.s6Error=err;
        CS.an=CS.an||{};
        CS.an.s6=_ck6(cs_full());
    })
    .finally(function(){
        CS.s6Loading=false;
        if(CS.step===6) cs_renderStep(6);
    });
}

function cs_s6(){
    if(!CS.an)cs_calcAnalysis();
    if(!CS.an.s6&&!CS.s6Loading) cs_fetchS6Analysis();

    if(CS.s6Loading){
        return cs_hd(6,"Feasibility check",
            "(Can the crop grow here?) : Assesses whether key conditions like soil, water, and climate match the crop’s growth needs.")+
            '<div class="cs-empty">Running farm feasibility check from backend...</div>'+
            '<div class="cs-sf"><span class="cs-fn">Sending all farm CFs to backend.</span>'+
            '<button class="cs-btn sec" onclick="cs_goto(5)">← Back</button></div>';
    }

    var data=Array.isArray(CS.an.s6)?CS.an.s6:[];
    var anyF=data.some(function(d){return(d.checks||[]).some(function(c){return!c.ok;});});
    var cards=data.map(function(d){
        var checks=d.checks||[];
        var ck=checks.map(function(c){
            return'<span class="cs-chk '+(c.ok?"cs-chk-p":c.sv?"cs-chk-f":"cs-chk-w")+'">'+(c.ok?"✓":"✗")+" "+c.k+"</span>";
        }).join("");
        var fails=checks.filter(function(c){return!c.ok;});
        var det=fails.length?
            '<div class="cs-wlist" style="margin-top:7px">'+fails.map(function(f){
                return'<div class="cs-wi '+(f.sv?"cs-wi-s":"cs-wi-w")+'">'+
                '<div class="cs-wt">'+f.k+': '+(f.sv?"Severe warning":"Warning")+'</div>'+
                '<div class="cs-wb">'+f.det+'</div></div>';
            }).join("")+'</div>':
            '<div style="font-size:11px;color:var(--csg600);margin-top:5px">All critical parameters met — crop viable for this farm.</div>';
        return'<div class="cs-cicd"><div class="cs-cicn">'+d.crop.name+'</div><div class="cs-chktags">'+ck+'</div>'+det+'</div>';
    }).join("");
    return cs_hd(6,"Feasibility check",
        "(Can the crop grow here?) : Assesses whether key conditions like soil, water, and climate match the crop’s growth needs.")+
        '<div class="cs-cig">'+(cards||'<div class="cs-empty">No farm feasibility response returned.</div>')+'</div>'+
        '<div class="cs-sf"><span class="cs-fn">'+(anyF?"Severe warnings detected — review before proceeding.":"All crops cleared the farm feasibility check.")+'</span>'+
        '<button class="cs-btn sec" onclick="cs_goto(5)">← Back</button>'+
        '<button class="cs-btn pri" onclick="cs_next()">Resource pressure check →</button></div>';
}

/* ── STEP 7 ───────────────────────────────────────────────────── */
function cs_fetchS7Analysis(){
    if(CS.s7Loading) return;

    CS.s7Loading=true;
    CS.s7Error=null;

    fetch("/api/method/rythulab.api.get_phase1_resource_pressure",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(cs_buildS6Payload())
    })
    .then(function(r){return r.json();})
    .then(function(res){
        var msg=res&&res.message?res.message:{};
        CS.an=CS.an||{};
        CS.an.s7=Array.isArray(msg.warnings)?msg.warnings:[];
    })
    .catch(function(err){
        console.warn("Step 7 backend check failed, using local fallback.",err);
        CS.s7Error=err;
        CS.an=CS.an||{};
        CS.an.s7=_ck7(cs_full());
    })
    .finally(function(){
        CS.s7Loading=false;
        if(CS.step===7) cs_renderStep(7);
    });
}

function cs_s7(){
    if(!CS.an)cs_calcAnalysis();
    if(!Array.isArray(CS.an.s7)&&!CS.s7Loading) cs_fetchS7Analysis();

    if(CS.s7Loading){
        return cs_hd(7,"Resource pressure check/Sustainability Check",
            "(Will the crop stress farm resources?): Evaluates if growing this crop will place high demand on limited soil nutrients or water resources.")+
            '<div class="cs-empty">Running resource pressure check from backend...</div>'+
            '<div class="cs-sf"><span class="cs-fn">Sending farm context features to backend.</span>'+
            '<button class="cs-btn sec" onclick="cs_goto(6)">← Back</button></div>';
    }

    var ws=Array.isArray(CS.an.s7)?CS.an.s7:[];
    var bd=ws.length?
        '<div class="cs-wlist">'+ws.map(function(w){
            return'<div class="cs-wi '+(w.t==="note"?"cs-wi-ok":"cs-wi-w")+'">'+
            '<div class="cs-wt">'+(w.t==="note"?"Note":"Resource pressure warning")+" — "+w.cn+'</div>'+
            '<div class="cs-wb">'+w.m+'</div></div>';
        }).join("")+'</div>':
        '<div class="cs-empty">No resource pressure warnings detected.</div>';
    return cs_hd(7,"Resource Pressure Check/Sustainability Check",
        "(Will the crop stress farm resources?): Evaluates if growing this crop will place high demand on limited soil nutrients or water resources")+
        bd+
        '<div class="cs-sf"><span class="cs-fn">'+ws.length+' warning(s) found.</span>'+
        '<button class="cs-btn sec" onclick="cs_goto(6)">← Back</button>'+
        '<button class="cs-btn pri" onclick="cs_next()">Ecosystem impact check →</button></div>';
}

/* ── STEP 8 — no revision button ─────────────────────────────── */
function cs_fetchS8Analysis(){
    if(CS.s8Loading) return;

    CS.s8Loading=true;
    CS.s8Error=null;

    fetch("/api/method/rythulab.api.get_phase1_ecosystem_impact",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(cs_buildS6Payload())
    })
    .then(function(r){return r.json();})
    .then(function(res){
        var msg=res&&res.message?res.message:{};
        CS.an=CS.an||{};
        CS.an.s8=Array.isArray(msg.warnings)?msg.warnings:[];
    })
    .catch(function(err){
        console.warn("Step 8 backend check failed, using local fallback.",err);
        CS.s8Error=err;
        CS.an=CS.an||{};
        CS.an.s8=_ck8(cs_full());
    })
    .finally(function(){
        CS.s8Loading=false;
        if(CS.step===8) cs_renderStep(8);
    });
}

function cs_s8(){
    if(!CS.an)cs_calcAnalysis();
    if(!Array.isArray(CS.an.s8)&&!CS.s8Loading) cs_fetchS8Analysis();

    if(CS.s8Loading){
        return cs_hd(8,"Impact check",
            '(Will crop ecosystem effects worsen CF?)“Assesses whether the crop may worsen existing weak soil, water, or biological conditions on the farm')+

            '<div class="cs-empty">Running ecosystem impact check from backend...</div>'+
            '<div class="cs-sf"><span class="cs-fn">Sending farm context features to backend.</span>'+
            '<button class="cs-btn sec" onclick="cs_goto(7)">← Back</button></div>';
    }

    var ws=Array.isArray(CS.an.s8)?CS.an.s8:[];
    var bd=ws.length?
        '<div class="cs-wlist">'+ws.map(function(w){
            return'<div class="cs-wi cs-wi-w">'+
            '<div class="cs-wt">Ecosystem impact — '+w.cn+'</div>'+
            '<div class="cs-wb">'+w.m+'</div></div>';
        }).join("")+'</div>':
        '<div class="cs-empty">No ecosystem impact warnings — none of the selected crops deteriorate weak context features of this farm.</div>';
    return cs_hd(8,"Impact check",
        '(Will crop ecosystem effects worsen CF?)“Assesses whether the crop may worsen existing weak soil, water, or biological conditions on the farm')+
        bd+
        '<div class="cs-sf"><span class="cs-fn">'+ws.length+' warning(s) found.</span>'+
        '<button class="cs-btn sec" onclick="cs_goto(7)">← Back</button>'+
        '<button class="cs-btn pri" onclick="cs_next()">Intercrop competition →</button></div>';
}

/* ── STEP 9 ───────────────────────────────────────────────────── */
function cs_buildS9Payload(){
    return {
        selected_crops: cs_full().map(function(c){
            return {
                id:c.id,
                cropid:c.cropid||c.id,
                name:c.name,
                type:c.type,
                a:c.a
            };
        })
    };
}

function cs_fetchS9Analysis(){
    if(CS.s9Loading) return;

    CS.s9Loading=true;
    CS.s9Error=null;

    fetch("/api/method/rythulab.api.get_phase1_intercrop_competition",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(cs_buildS9Payload())
    })
    .then(function(r){return r.json();})
    .then(function(res){
        var msg=res&&res.message?res.message:{};
        CS.an=CS.an||{};
        CS.an.s9=Array.isArray(msg.warnings)?msg.warnings:[];
    })
    .catch(function(err){
        console.warn("Step 9 backend check failed, using local fallback.",err);
        CS.s9Error=err;
        CS.an=CS.an||{};
        CS.an.s9=_ck9(cs_full());
    })
    .finally(function(){
        CS.s9Loading=false;
        if(CS.step===9) cs_renderStep(9);
    });
}

function cs_s9(){
    if(!CS.an)cs_calcAnalysis();
    if(!Array.isArray(CS.an.s9)&&!CS.s9Loading) cs_fetchS9Analysis();

    if(CS.s9Loading){
        return cs_hd(9,"Intercrop competition check",
            'Identifies potential conflicts between selected crops due to competition for light, nutrients, water, or shared pests')+
            '<div class="cs-empty">Running intercrop competition check from backend...</div>'+
            '<div class="cs-sf"><span class="cs-fn">Sending selected crops to backend.</span>'+
            '<button class="cs-btn sec" onclick="cs_goto(8)">← Back</button></div>';
    }

    var cf=Array.isArray(CS.an.s9)?CS.an.s9:[];
    var bd=cf.length?
        '<div class="cs-wlist">'+cf.map(function(c){
            return'<div class="cs-wi cs-wi-w">'+
            '<div class="cs-wt">'+c.t+' competition — '+c.a+' × '+c.b+'</div>'+
            '<div class="cs-wb">'+c.m+'</div></div>';
        }).join("")+'</div>':
        '<div class="cs-empty">No intercrop competition conflicts detected.</div>';
    return cs_hd(9,"Intercrop competition check",
       'Identifies potential conflicts between selected crops due to competition for light, nutrients, water, or shared pests')+
        bd+
        '<div class="cs-sf"><span class="cs-fn">'+cf.length+' conflict(s) found.</span>'+
        (cf.length?'<button class="cs-btn rev" onclick="cs_goto(2)">← Revise selection</button>':"")+
        '<button class="cs-btn sec" onclick="cs_goto(8)">← Back</button>'+
        '<button class="cs-btn pri" onclick="cs_next()">Microfeature conflicts →</button></div>';
}

/* ── STEP 10 ──────────────────────────────────────────────────── */
function cs_buildS10Payload(){
    return {
        selected_crops: cs_full().map(function(c){
            return {
                id:c.id,
                cropid:c.cropid||c.id,
                name:c.name,
                type:c.type,
                a:c.a
            };
        })
    };
}

function cs_fetchS10Analysis(){
    if(CS.s10Loading) return;

    CS.s10Loading=true;
    CS.s10Error=null;

    fetch("/api/method/rythulab.api.get_phase1_microfeature_conflicts",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(cs_buildS10Payload())
    })
    .then(function(r){return r.json();})
    .then(function(res){
        var msg=res&&res.message?res.message:{};
        CS.an=CS.an||{};
        CS.an.s10=Array.isArray(msg.warnings)?msg.warnings:[];
    })
    .catch(function(err){
        console.warn("Step 10 backend check failed, using local fallback.",err);
        CS.s10Error=err;
        CS.an=CS.an||{};
        CS.an.s10=_ck10(cs_full());
    })
    .finally(function(){
        CS.s10Loading=false;
        if(CS.step===10) cs_renderStep(10);
    });
}

function cs_s10(){
    if(!CS.an)cs_calcAnalysis();
    if(!Array.isArray(CS.an.s10)&&!CS.s10Loading) cs_fetchS10Analysis();

    if(CS.s10Loading){
        return cs_hd(10,"Microfeature conflict check",
            'Checks for other conflicts that may arise between the Microfeatures of the main crops.<br><br>')+
            '<div class="cs-empty">Running microfeature conflict check from backend...</div>'+
            '<div class="cs-sf"><span class="cs-fn">Sending selected crops to backend.</span>'+
            '<button class="cs-btn sec" onclick="cs_goto(9)">← Back</button></div>';
    }

    var cf=Array.isArray(CS.an.s10)?CS.an.s10:[];
    var bd=cf.length?
        '<div class="cs-wlist">'+cf.map(function(c){
            return'<div class="cs-wi cs-wi-w">'+
            '<div class="cs-wt">MF conflict — "'+c.mf_label+'" ('+c.nc+' vs '+c.sc+')</div>'+
            '<div class="cs-wb">'+c.msg+'</div></div>';
        }).join("")+'</div>':
        '<div class="cs-empty">No microfeature conflicts detected.</div>';
    return cs_hd(10,"Microfeature conflict check",
        'Checks for other conflicts that may arise between the Microfeatures of the main crops.<br><br>'+
        '<strong>Rule:</strong> Required MF ∩ Suppress MF not empty → flag conflicts between Crop X (required MF) and Crop Y (suppress the same MF). Note the warning with reason.')+
        bd+
        '<div class="cs-sf"><span class="cs-fn">'+cf.length+' conflict(s) found.</span>'+
        (cf.length?'<button class="cs-btn rev" onclick="cs_goto(2)">← Revise selection</button>':"")+
        '<button class="cs-btn sec" onclick="cs_goto(9)">← Back</button>'+
        '<button class="cs-btn pri" onclick="cs_next()">View summary →</button></div>';
}

/* ── STEP 11 — Summary and make decisions ────────────────────── */
function cs_s11(){
    if(!CS.an)cs_calcAnalysis();
    var a=CS.an;
    var s6=Array.isArray(a.s6)?a.s6:[];
    var s7=Array.isArray(a.s7)?a.s7:[];
    var s8=Array.isArray(a.s8)?a.s8:[];
    var s9=Array.isArray(a.s9)?a.s9:[];
    var s10=Array.isArray(a.s10)?a.s10:[];
    var w6=s6.reduce(function(t,d){return t+(d.checks||[]).filter(function(c){return!c.ok;}).length;},0);
    var sv=s6.reduce(function(t,d){return t+(d.checks||[]).filter(function(c){return!c.ok&&c.sv;}).length;},0);
    var w7=s7.length,w8=s8.length,w9=s9.length,w10=s10.length,tw=w6+w7+w8+w9+w10;
    var crops=cs_full();
    var srows=[
        {n:6,l:"Farm feasibility check",  w:w6},
        {n:7,l:"Resource pressure check", w:w7},
        {n:8,l:"Ecosystem impact check",  w:w8},
        {n:9,l:"Intercrop competition",   w:w9},
        {n:10,l:"Microfeature conflicts", w:w10}
    ].map(function(r){
        var cl=r.w===0?"var(--csg600)":r.w<=2?"var(--csa600)":"var(--csr600)";
        return'<div class="cs-fcr" style="cursor:pointer" onclick="cs_goto('+r.n+')">'+
            '<span class="cs-fcrl">Step '+r.n+': '+r.l+'</span>'+
            '<span class="cs-fcrv" style="color:'+cl+'">'+(r.w===0?"No issues":r.w+" warning(s)")+" →</span></div>";
    }).join("");
    var crows=crops.map(function(c){
        return'<tr><td>'+c.name+'</td><td style="color:#3a4a2a">'+c.type+'</td>'+
            '<td>'+c.a.toFixed(1)+' ha</td><td>'+c.wr+'mm</td></tr>';
    }).join("");
    var vrd=sv>0?
        '<div class="cs-vcrd cs-vc-fail"><div class="cs-vci cs-vci-fail">!</div><div>'+
        '<div class="cs-vttl">Severe warnings — revision recommended</div>'+
        '<div class="cs-vmsg">'+sv+' severe issue(s) found. Revise your crop selection before proceeding to Phase 2.</div>'+
        '</div></div>':
        tw===0?
        '<div class="cs-vcrd cs-vc-ok"><div class="cs-vci cs-vci-ok">✓</div><div>'+
        '<div class="cs-vttl">All checks passed — ready to proceed</div>'+
        '<div class="cs-vmsg">No critical issues found across steps 6–10. You may proceed to Phase 2.</div>'+
        '</div></div>':
        '<div class="cs-vcrd cs-vc-warn"><div class="cs-vci cs-vci-warn">~</div><div>'+
        '<div class="cs-vttl">Minor warnings — proceed with caution</div>'+
        '<div class="cs-vmsg">'+tw+' warning(s) noted across steps 6–10. You can proceed or revise.</div>'+
        '</div></div>';
    return cs_hd(11,"Summary and make decisions",
        "Consolidated results from Step 6 to Step 10. Review all warnings, then decide to revise or proceed to Phase 2.")+
        '<div class="cs-scards">'+
        '<div class="cs-sc2"><div class="cs-sc2-n sn-g">'+crops.length+'</div><div class="cs-sc2-l">crops selected</div></div>'+
        '<div class="cs-sc2"><div class="cs-sc2-n '+(tw===0?"sn-g":tw<=3?"sn-w":"sn-r")+'">'+tw+'</div><div class="cs-sc2-l">total warnings</div></div>'+
        '<div class="cs-sc2"><div class="cs-sc2-n '+(sv===0?"sn-g":"sn-r")+'">'+sv+'</div><div class="cs-sc2-l">severe issues</div></div></div>'+
        '<div class="cs-fcrd" style="margin-bottom:10px">'+
        '<div class="cs-fcht">Step 6 to Step 10 — warnings summary (click to review)</div>'+srows+'</div>'+
        '<div class="cs-fcrd" style="margin-bottom:10px"><div class="cs-fcht">Confirmed crop portfolio</div>'+
        '<table class="cs-dtbl"><thead><tr><th>Crop</th><th>Type</th><th>Area (ha)</th><th>Water req.</th></tr></thead>'+
        '<tbody>'+crows+'</tbody></table></div>'+
        vrd+
        '<div class="cs-sf"><span class="cs-fn">Phase 2 will recommend associate crops based on missing microfeatures.</span>'+
        '<button class="cs-btn rev" onclick="cs_goto(2)">← Revise selection</button>'+
        '<button class="cs-btn pri" '+(sv>0?"disabled":"")+' onclick="cs_switchPhase(2,true)">Proceed to Phase 2 →</button></div>';
}