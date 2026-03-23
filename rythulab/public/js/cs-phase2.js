/* ═══ Phase 2: Associate Crop Selection ═══════════════════════ */

var P2_CROPS = [
    {id:"marigold",name:"Marigold (African)",type:"Associate",family:"Asteraceae",
     mfp:["pollinator_habitat","pest_repellent","beneficial_insects","trap_pest"],
     mfr:[],diseases_repelled:["nematodes","whitefly","aphids"],
     trapFor:["Helicoverpa armigera","whitefly"],
     border:true,trap:true,
     desc:"Repels nematodes, whitefly; attracts beneficial insects; traps Helicoverpa"},
    {id:"sunhemp",name:"Sunhemp (Crotalaria juncea)",type:"Associate",family:"Fabaceae",
     mfp:["nitrogen_fixation","ground_cover","biomass_mulch","nematode_suppression","moderate_moisture"],
     mfr:[],diseases_repelled:["root_knot_nematode"],
     trapFor:[],border:false,trap:false,
     desc:"Fixes nitrogen, suppresses nematodes, improves soil organic matter"},
    {id:"dhaincha",name:"Dhaincha (Sesbania bispinosa)",type:"Associate",family:"Fabaceae",
     mfp:["nitrogen_fixation","biomass_mulch","ground_cover","moderate_moisture"],
     mfr:["waterlogging_tolerance"],diseases_repelled:[],
     trapFor:[],border:false,trap:false,
     desc:"Fast N-fixation, excellent green manure, waterlogging tolerant"},
    {id:"cowpea",name:"Cowpea",type:"Associate",family:"Fabaceae",
     mfp:["nitrogen_fixation","ground_cover","pollinator_habitat","moderate_moisture"],
     mfr:[],diseases_repelled:[],
     trapFor:[],border:false,trap:false,
     desc:"Dual purpose — N fixation + food legume; ground cover prevents erosion"},
    {id:"coriander",name:"Coriander",type:"Associate",family:"Apiaceae",
     mfp:["beneficial_insects","pollinator_habitat","pest_repellent"],
     mfr:[],diseases_repelled:["aphids","spider_mite"],
     trapFor:[],border:true,trap:false,
     desc:"Attracts parasitic wasps and beneficial insects; repels aphids and spider mites"},
    {id:"basil",name:"Basil (Tulsi)",type:"Associate",family:"Lamiaceae",
     mfp:["pest_repellent","pollinator_habitat","beneficial_insects"],
     mfr:[],diseases_repelled:["aphids","whitefly","thrips"],
     trapFor:[],border:true,trap:false,
     desc:"Strong aromatic deterrent for aphids, whitefly, thrips; attracts pollinators"},
    {id:"lemongrass",name:"Lemongrass",type:"Border",family:"Poaceae",
     mfp:["wind_break","pest_repellent","erosion_control","ground_cover"],
     mfr:[],diseases_repelled:["stem_borer","armyworm"],
     trapFor:[],border:true,trap:false,
     desc:"Dense border crop; wind break; deters stem borers and armyworm"},
    {id:"castor",name:"Castor (Ricinus communis)",type:"Trap",family:"Euphorbiaceae",
     mfp:["canopy_shade","trap_pest"],
     mfr:[],diseases_repelled:[],
     trapFor:["Helicoverpa armigera","Spodoptera litura","shoot_fly"],
     border:true,trap:true,
     desc:"Trap crop for Helicoverpa armigera and Spodoptera — acts as dead-end trap"},
    {id:"mustard",name:"Mustard",type:"Trap",family:"Brassicaceae",
     mfp:["pollinator_habitat","trap_pest","beneficial_insects"],
     mfr:[],diseases_repelled:[],
     trapFor:["aphids","diamondback_moth","whitefly"],
     border:true,trap:true,
     desc:"Trap crop for aphids and whitefly; attracts beneficial insects when flowering"},
    {id:"vetiver",name:"Vetiver Grass",type:"Border",family:"Poaceae",
     mfp:["wind_break","erosion_control","ground_cover","water_retention","well_drained_soil"],
     mfr:[],diseases_repelled:[],
     trapFor:[],border:true,trap:false,
     desc:"Dense fibrous roots — excellent erosion control, wind break, water retention"},
    {id:"cluster_bean",name:"Cluster Bean (Guar)",type:"Associate",family:"Fabaceae",
     mfp:["nitrogen_fixation","ground_cover","drought_tolerance","well_drained_soil"],
     mfr:[],diseases_repelled:[],
     trapFor:[],border:false,trap:false,
     desc:"N-fixing drought-tolerant legume; improves soil structure"},
    {id:"sesbania",name:"Sesbania (Dhaincha tall)",type:"Border",family:"Fabaceae",
     mfp:["wind_break","nitrogen_fixation","biomass_mulch","canopy_shade"],
     mfr:[],diseases_repelled:[],
     trapFor:[],border:true,trap:false,
     desc:"Tall fast-growing border; wind break + N fixation + shade for border rows"},
    {id:"neem_border",name:"Neem (border use)",type:"Border",family:"Meliaceae",
     mfp:["pest_repellent","beneficial_insects","wind_break"],
     mfr:[],diseases_repelled:["stem_borer","shoot_fly","aphids","whitefly","bollworm"],
     trapFor:[],border:true,trap:false,
     desc:"Neem volatiles repel a broad spectrum of crop pests; classic IPM border plant"},
    {id:"sorghum_sudan",name:"Sorghum-Sudan Hybrid (border)",type:"Border",family:"Poaceae",
     mfp:["wind_break","biomass_mulch","canopy_shade"],
     mfr:[],diseases_repelled:[],
     trapFor:["shoot_fly","stem_borer"],
     border:true,trap:true,
     desc:"Tall dense border wind break; trap for shoot fly and stem borer"},
    {id:"tephrosia",name:"Tephrosia (Wild indigo)",type:"Associate",family:"Fabaceae",
     mfp:["nitrogen_fixation","pest_repellent","ground_cover","beneficial_insects","well_drained_soil"],
     mfr:[],diseases_repelled:["aphids","stem_borer"],
     trapFor:[],border:false,trap:false,
     desc:"Rotenone-producing legume — natural pest deterrent + N fixation"}
];

var P2_MF_CF = {
    nitrogen_fixation:   ["N","SOC"],
    ground_cover:        ["SOC","ER","BD","WHC"],
    biomass_mulch:       ["SOC","WHC","N"],
    deep_root_aeration:  ["ESD","BD","DR"],
    pollinator_habitat:  ["PA"],
    wind_break:          ["WP","ER"],
    beneficial_insects:  ["PP"],
    pest_repellent:      ["PP"],
    water_retention:     ["WHC","W"],
    erosion_control:     ["ER"],
    nematode_suppression:["PP"],
    trap_pest:           ["PP"],
    canopy_shade:        ["TMP","HSD"],
    drought_tolerance:   ["W"],
    nitrogen_rich:       ["N"],
    moderate_moisture:   ["W","WHC","DR"],
    well_drained_soil:   ["DR","BD","ESD"]
};

var P2_DISEASE_MF = {
    "Stem borer":          ["pest_repellent","beneficial_insects","trap_pest"],
    "Shoot fly":           ["pest_repellent","trap_pest"],
    "Aphids":              ["beneficial_insects","pest_repellent"],
    "Whitefly":            ["beneficial_insects","pest_repellent","trap_pest"],
    "Bollworm":            ["pest_repellent","trap_pest","beneficial_insects"],
    "Pod borer":           ["pest_repellent","beneficial_insects"],
    "Leaf spot":           ["beneficial_insects","pest_repellent"],
    "Brown planthopper":   ["beneficial_insects","pest_repellent"],
    "Helicoverpa armigera":["trap_pest","beneficial_insects","pest_repellent"],
    "Armyworm":            ["pest_repellent","trap_pest"],
    "Thrips":              ["beneficial_insects","pest_repellent"],
    "Rust":                ["beneficial_insects"],
    "Wilt":                ["nitrogen_fixation","ground_cover"],
    "Fusarium":            ["nitrogen_fixation","ground_cover"],
    "Downy mildew":        ["pest_repellent","beneficial_insects"],
    "Blight":              ["beneficial_insects","pest_repellent"],
    "Rot":                 ["ground_cover","nitrogen_fixation"],
    "Mosaic":              ["beneficial_insects","pest_repellent"],
    "Smut":                ["beneficial_insects"]
};

/* ── Helper: is a pest entry a disease? ─────────────────────── */
function p2_isDisease(str){
    var diseaseKeys=["mildew","blight","spot","rust","rot","wilt","virus","mosaic","smut",
                     "yellowing","chlorosis","necrosis","fusarium","cercospora","alternaria",
                     "sclerotia","bacterial","fungal","viral","anthracnose","canker"];
    var lower=str.toLowerCase();
    return diseaseKeys.some(function(k){return lower.indexOf(k)>=0;});
}

var CS2 = {
    step: 1,
    mainCrops: [],
    missingMF: [],
    step1Data: null,
    step2Data: null,
    associateList: [],
    borderList: [],
    trapList: [],
    selectedAssoc: [],
    selectedBorder: [],
    selectedTrap: []
};

var CS2_STEPS = [
    {n:1, name:"Missing MF analysis"},
    {n:2, name:"MF cross-compatibility"},
    {n:3, name:"Main crop Disease risk"},
    {n:4, name:"Farm context features"},
    {n:5, name:"Border crop (wind barrier)"},
    {n:6, name:"Border crop (Pest barrier Pollination promoter)"},
    {n:7, name:"Trap crops"},
    {n:8, name:"Select & confirm"}
];

/* ── Entry point ─────────────────────────────────────────────── */
function cs_phase2_init(){
    var root=document.getElementById("cs-root"); if(!root) return;
    CS2.mainCrops = cs_full ? cs_full() : [];
    if(!CS2.mainCrops.length){
        root.innerHTML='<div style="padding:40px;text-align:center;background:white;border-radius:14px;border:1.5px solid var(--border)">'+
            '<div style="font-size:36px;margin-bottom:12px">⚠️</div>'+
            '<div style="font-size:16px;font-weight:700;color:var(--green-dark);margin-bottom:8px">Complete Phase 1 first</div>'+
            '<div style="font-size:13px;color:#3a4a2a">Please complete Phase 1 (Main crop selection) before proceeding to Phase 2.</div>'+
            '<div style="margin-top:16px"><button class="cs-btn pri" onclick="cs_switchPhase(1)">← Go to Phase 1</button></div>'+
        '</div>';
        return;
    }
    p2_computeAll();
    root.innerHTML="";
    root.appendChild(_p2_phaseTabs());
    var lay=document.createElement("div"); lay.className="cs-lay";
    lay.innerHTML='<div class="cs-sbar" id="cs-sbar"></div><div class="cs-sc" id="cs-content"></div>';
    root.appendChild(lay);
    p2_renderSidebar(); p2_renderStep(CS2.step);
    cs_fetchPhase2Step1();
    cs_fetchPhase2Step2();
}

/* ── Fetch Phase 2 Step 1 from backend ───────────────────────── */
function cs_fetchPhase2Step1(){
    var crops = CS2.mainCrops;
    if(!crops || !crops.length) return;
    if(CS2.p2s1Loading) return;
    CS2.p2s1Loading = true;
    fetch("/api/method/rythulab.api.get_phase2_missing_mfs", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            selected_crops: crops.map(function(c){
                return {id:c.id, cropid:c.cropid||c.id, name:c.name, type:c.type||"", a:c.a||0};
            })
        })
    })
    .then(function(r){ return r.json(); })
    .then(function(res){
        var msg = res && res.message ? res.message : {};
        if(!msg.ok) return;
        CS2.step1Data = {
            missing_mfs: Array.isArray(msg.missing_mfs) ? msg.missing_mfs : [],
            missing_mf_details: Array.isArray(msg.missing_mf_details) ? msg.missing_mf_details : [],
            recommended_crops: Array.isArray(msg.recommended_crops) ? msg.recommended_crops : [],
            required_mfs: Array.isArray(msg.required_mfs) ? msg.required_mfs : [],
            available_mfs: Array.isArray(msg.available_mfs) ? msg.available_mfs : []
        };
        if(Array.isArray(msg.missing_mfs)){
            CS2.missingMF = msg.missing_mfs;
        }
        if(Array.isArray(msg.recommended_crops)){
            msg.recommended_crops.forEach(function(rec){
                var already = CS2.associateList.find(function(e){
                    return e.crop && e.crop.id === rec.crop_id;
                });
                if(!already){
                    CS2.associateList.push({
                        crop: {
                            id: rec.crop_id,
                            name: rec.crop_name,
                            mfp: rec.covers_missing_mfs || [],
                            type: "Associate",
                            family: "",
                            desc: "",
                            border: false,
                            trap: false
                        },
                        reasons: rec.reasons || []
                    });
                }
            });
        }
    })
    .catch(function(err){
        console.warn("Phase 2 Step 1 backend fetch failed:", err);
    })
    .finally(function(){
        CS2.p2s1Loading = false;
        if(CS2.step === 1) p2_renderStep(1);
    });
}

/* ── Fetch Phase 2 Step 2 from backend ───────────────────────── */
function cs_fetchPhase2Step2(){
    var crops = CS2.mainCrops;
    if(!crops || !crops.length) return;
    if(CS2.p2s2Loading) return;
    CS2.p2s2Loading = true;
    fetch("/api/method/rythulab.api.get_phase2_cross_compatibility", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            selected_crops: crops.map(function(c){
                return {id:c.id, cropid:c.cropid||c.id, name:c.name, type:c.type||"", a:c.a||0};
            })
        })
    })
    .then(function(r){ return r.json(); })
    .then(function(res){
        var msg = res && res.message ? res.message : {};
        if(!msg.ok) return;

        CS2.step2Data = {
            selected_crop_ids: Array.isArray(msg.selected_crop_ids) ? msg.selected_crop_ids : [],
            selected_produced_mfs: Array.isArray(msg.selected_produced_mfs) ? msg.selected_produced_mfs : [],
            selected_required_mfs: Array.isArray(msg.selected_required_mfs) ? msg.selected_required_mfs : [],
            associated_crops: Array.isArray(msg.associated_crops) ? msg.associated_crops : []
        };

        (CS2.step2Data.associated_crops || []).forEach(function(rec){
            var producedCodes = (rec.candidate_produced_mfs || []).map(function(mf){
                return mf && mf.mf_code ? mf.mf_code : null;
            }).filter(Boolean);

            var already = CS2.associateList.find(function(e){
                return e.crop && e.crop.id === rec.crop_id;
            });

            if(!already){
                CS2.associateList.push({
                    crop: {
                        id: rec.crop_id,
                        name: rec.crop_name,
                        mfp: producedCodes,
                        type: "Associate",
                        family: "",
                        desc: "",
                        border: false,
                        trap: false
                    },
                    reasons: Array.isArray(rec.reasons) ? rec.reasons.slice() : []
                });
                return;
            }

            already.crop.mfp = Array.from(new Set((already.crop.mfp || []).concat(producedCodes)));
            (rec.reasons || []).forEach(function(reason){
                if(already.reasons.indexOf(reason) < 0){
                    already.reasons.push(reason);
                }
            });
        });
    })
    .catch(function(err){
        console.warn("Phase 2 Step 2 backend fetch failed:", err);
    })
    .finally(function(){
        CS2.p2s2Loading = false;
        if(CS2.step === 2) p2_renderStep(2);
    });
}

/* ── Compute all recommendations upfront ─────────────────────── */
function p2_computeAll(){
    var mc = CS2.mainCrops;
    var availMF = [];
    mc.forEach(function(c){ (c.mfp||[]).forEach(function(m){ if(availMF.indexOf(m)<0) availMF.push(m); }); });
    var reqMF = [];
    mc.forEach(function(c){ (c.mfr||[]).forEach(function(m){ if(reqMF.indexOf(m)<0) reqMF.push(m); }); });
    CS2.missingMF = reqMF.filter(function(m){ return availMF.indexOf(m)<0; });

    var assoc=[], border=[], trap=[];
    P2_CROPS.forEach(function(ac){
        var reasons=[];
        CS2.missingMF.forEach(function(mf){
            if((ac.mfp||[]).indexOf(mf)>=0)
                reasons.push('Produces missing MF "'+cs_mfl(mf)+'" needed by main crops');
        });
        mc.forEach(function(mc2){
            (mc2.mfr||[]).forEach(function(mfNeeded){
                if((ac.mfp||[]).indexOf(mfNeeded)>=0 && reasons.indexOf('Produces "'+cs_mfl(mfNeeded)+'" required by '+mc2.name)<0)
                    reasons.push('Produces "'+cs_mfl(mfNeeded)+'" MF required by '+mc2.name);
            });
        });
        mc.forEach(function(mc3){
            (mc3.pests||[]).forEach(function(pest){
                Object.keys(P2_DISEASE_MF).forEach(function(dis){
                    if(pest.toLowerCase().indexOf(dis.toLowerCase())>=0){
                        P2_DISEASE_MF[dis].forEach(function(mf){
                            if((ac.mfp||[]).indexOf(mf)>=0){
                                var r='Reduces risk of "'+dis+'" (pest of '+mc3.name+') via MF "'+cs_mfl(mf)+'"';
                                if(reasons.indexOf(r)<0) reasons.push(r);
                            }
                        });
                    }
                });
            });
        });
        var weakCFs=["N","P","K","SOC","PP","WP"];
        weakCFs.forEach(function(cfk){
            var cf=CS_FARM.cf[cfk]; if(!cf||cf.s>3) return;
            (ac.mfp||[]).forEach(function(mf){
                if(P2_MF_CF[mf]&&P2_MF_CF[mf].indexOf(cfk)>=0){
                    var r='Improves weak CF "'+cf.l+'" ('+cf.slab+') via MF "'+cs_mfl(mf)+'"';
                    if(reasons.indexOf(r)<0) reasons.push(r);
                }
            });
        });
        if(reasons.length>0 && !ac.border && !ac.trap)
            assoc.push({crop:ac, reasons:reasons});
        if(ac.border && reasons.length>0)
            border.push({crop:ac, reasons:reasons});
        if(ac.trap && reasons.length>0)
            trap.push({crop:ac, reasons:reasons});
    });
    if(CS_FARM.cf.WP&&CS_FARM.cf.WP.s<=3){
        P2_CROPS.forEach(function(ac){
            if((ac.mfp||[]).indexOf("wind_break")>=0){
                var already=border.find(function(b){return b.crop.id===ac.id;});
                if(!already) border.push({crop:ac,reasons:['Farm wind protection is "'+CS_FARM.cf.WP.slab+'" — border wind break needed']});
                else if(already.reasons.indexOf('Farm wind protection is "'+CS_FARM.cf.WP.slab+'" — border wind break needed')<0)
                    already.reasons.push('Farm wind protection is "'+CS_FARM.cf.WP.slab+'" — border wind break needed');
            }
        });
    }
    P2_CROPS.forEach(function(ac){
        if((ac.mfp||[]).indexOf("pollinator_habitat")>=0 && ac.border){
            var already=border.find(function(b){return b.crop.id===ac.id;});
            if(!already) border.push({crop:ac,reasons:['Provides pollinator habitat MF for farm biodiversity']});
            else if(already.reasons.indexOf('Provides pollinator habitat MF for farm biodiversity')<0)
                already.reasons.push('Provides pollinator habitat MF for farm biodiversity');
        }
    });
    mc.forEach(function(mc4){
        (mc4.pests||[]).forEach(function(pest){
            P2_CROPS.forEach(function(ac){
                if(!ac.trap) return;
                (ac.trapFor||[]).forEach(function(tf){
                    if(pest.toLowerCase().indexOf(tf.toLowerCase())>=0||tf.toLowerCase().indexOf(pest.split(" ")[0].toLowerCase())>=0){
                        var already=trap.find(function(t){return t.crop.id===ac.id;});
                        var r='Trap crop for "'+tf+'" (pest of '+mc4.name+')';
                        if(!already) trap.push({crop:ac,reasons:[r]});
                        else if(already.reasons.indexOf(r)<0) already.reasons.push(r);
                    }
                });
            });
        });
    });

    CS2.associateList = assoc;
    CS2.borderList    = border;
    CS2.trapList      = trap;

    // Start empty — user selects crops manually; sidebar updates as they tick
    CS2.selectedAssoc  = [];
    CS2.selectedBorder = [];
    CS2.selectedTrap   = [];
}

/* ── Phase tabs ──────────────────────────────────────────────── */
function _p2_phaseTabs(){
    var phases=[
        {n:1,l:"Main crop selection",a:false},
        {n:2,l:"Associate crops",a:true},
        {n:3,l:"Biodiversity crops",a:false},
        {n:4,l:"System evaluation",a:false}
    ];
    var d=document.createElement("div"); d.className="cs-ptabs";
    d.innerHTML=phases.map(function(p){
        return'<button class="cs-ptab '+(p.a?"active":"")+(p.n>2?" off":"")+'" onclick="'+(p.n<=2?"cs_switchPhase("+p.n+")":"")+'">'+
            '<span class="cs-pnum">'+p.n+'</span>Phase '+p.n+': '+p.l+'</button>';
    }).join("");
    return d;
}

/* ── Sidebar ──────────────────────────────────────────────── */
function p2_renderSidebar(){
    var sb=document.getElementById("cs-sbar"); if(!sb) return;
    var h='<div class="cs-sbar-hd">Phase 2 — steps</div>';
    CS2_STEPS.forEach(function(s){
        var done=s.n<CS2.step,cur=s.n===CS2.step;
        h+='<div class="cs-si '+(done?"done":cur?"cur":"")+'" '+(done?'onclick="p2_goto('+s.n+')"':'')+">"+
           '<div class="cs-si-n">'+(done?"✓":s.n)+'</div>'+
           '<div class="cs-si-nm">'+s.name+'</div></div>';
    });
    // Selected crops box — always below steps, inside sidebar
    var selHtml=(typeof cs_selBoxSidebarHtml==="function")?cs_selBoxSidebarHtml():"";
    h+='<div style="margin-top:16px;padding-top:12px;border-top:2px solid var(--green-pale)">'+
       '<div style="font-size:9px;font-weight:700;color:var(--text-mid);text-transform:uppercase;letter-spacing:0.6px;margin-bottom:8px;padding:0 2px">✔ Selected Crops</div>'+
       '<div id="cs-selbox">'+selHtml+'</div>'+
       '</div>';
    sb.innerHTML=h;
}
function p2_renderStep(n){var el=document.getElementById("cs-content");if(!el)return;el.innerHTML=p2_buildStep(n);p2_renderSidebar();if(typeof cs_updateSelBox==="function")cs_updateSelBox();}
function p2_goto(n){if(n<=CS2.step){CS2.step=n;p2_renderStep(n);}}
function p2_next(){CS2.step++;p2_renderStep(CS2.step);}

/* ── Step header ─────────────────────────────────────────────── */
function p2_hd(n,title,desc){
    return'<div class="cs-bdg"><span class="cs-bdg-n">Step '+n+'</span><span class="cs-bdg-t">Phase 2 — associate crop selection</span></div>'+
        '<div class="cs-ttl">'+title+'</div>'+
        (desc?'<div class="cs-dsc">'+desc+'</div>':'')+
        '<hr class="cs-hr">';
}
function p2_buildStep(n){
    var fns=[p2_s1,p2_s2,p2_s3,p2_s4,p2_s5,p2_s6,p2_s7,p2_s8];
    return fns[n-1]?fns[n-1]():"";
}

/* ── Reusable crop recommendation card ───────────────────────── */
function p2_cropCard(entry, selArr, prefix){
    var ac=entry.crop, sel=selArr.indexOf(ac.id)>=0;
    var tags=(ac.mfp||[]).slice(0,4).map(function(m){return'<span class="cs-t cs-t-p">'+cs_mfl(m)+'</span>';}).join("");
    var reasons=entry.reasons.map(function(r){return'<li style="margin-bottom:3px">'+r+'</li>';}).join("");
    return'<div style="background:var(--green-bg);border:1.5px solid '+(sel?"var(--green-mid)":"var(--border)")+';border-radius:10px;padding:12px;margin-bottom:8px">'+
        '<div style="display:flex;align-items:flex-start;gap:10px">'+
        '<input type="checkbox" id="'+prefix+'_'+ac.id+'" '+(sel?"checked":"")+
            ' style="margin-top:3px;width:16px;height:16px;flex-shrink:0"'+
            ' onchange="p2_toggleSel(\''+prefix+'\',\''+ac.id+'\',this.checked)">'+
        '<div style="flex:1">'+
        '<div style="font-size:13px;font-weight:700;color:var(--text-dark);margin-bottom:2px">'+ac.name+'</div>'+
        '<div style="font-size:11px;color:#3a4a2a;margin-bottom:5px">'+ac.type+' · '+ac.family+' · '+ac.desc+'</div>'+
        '<div style="margin-bottom:6px">'+tags+'</div>'+
        '<div style="background:white;border-radius:6px;padding:7px 10px">'+
        '<div style="font-size:10px;font-weight:700;color:#2a3a1a;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px">Reasons for recommendation:</div>'+
        '<ul style="font-size:11px;color:#2a3a1a;padding-left:16px;margin:0">'+reasons+'</ul>'+
        '</div></div></div></div>';
}
function p2_toggleSel(prefix, id, checked){
    var arr = prefix==="assoc"?CS2.selectedAssoc:prefix==="border"?CS2.selectedBorder:CS2.selectedTrap;
    if(checked){if(arr.indexOf(id)<0)arr.push(id);}
    else{var i=arr.indexOf(id);if(i>=0)arr.splice(i,1);}
    if(typeof cs_updateSelBox==="function") cs_updateSelBox();
}

/* ── Step 1: Missing MF — grouped by microfeature ───────────── */
function p2_s1(){
    var mc=CS2.mainCrops;
    var step1Data=CS2.step1Data||{};
    var availMF=Array.isArray(step1Data.available_mfs)?step1Data.available_mfs.slice():[];
    var reqMF=Array.isArray(step1Data.required_mfs)?step1Data.required_mfs.slice():[];
    var missing=Array.isArray(step1Data.missing_mfs)?step1Data.missing_mfs.slice():CS2.missingMF.slice();
    var missingDetails=Array.isArray(step1Data.missing_mf_details)?step1Data.missing_mf_details:[];

    if(!availMF.length){
        mc.forEach(function(c){(c.mfp||[]).forEach(function(m){if(availMF.indexOf(m)<0)availMF.push(m);});});
    }
    if(!reqMF.length){
        mc.forEach(function(c){(c.mfr||[]).forEach(function(m){if(reqMF.indexOf(m)<0)reqMF.push(m);});});
    }

    var availHtml=availMF.map(function(m){return'<span class="cs-t cs-t-p">'+cs_mfl(m)+'</span>';}).join(" ");
    var reqHtml=reqMF.map(function(m){
        var isMissing=missing.indexOf(m)>=0;
        return'<span class="cs-t '+(isMissing?"cs-t-f":"cs-t-p")+'">'+cs_mfl(m)+(isMissing?" ✗":"")+'</span>';
    }).join(" ");
    var missingHtml=missing.length?
        missing.map(function(m){return'<span class="cs-t cs-t-f">'+cs_mfl(m)+'</span>';}).join(" "):
        '<span style="color:var(--csg600);font-size:12px">None — all required MFs are covered by main crops ✓</span>';

    // Group associate crops by missing MF
    var mfGroupsHtml = '';
    if(missingDetails.length){
        mfGroupsHtml = '<div style="font-size:12px;font-weight:700;color:#2a3a1a;margin-bottom:10px">Associate crops available for each missing microfeature:</div>';
        missingDetails.forEach(function(detail){
            var mfCode = detail.mf_code;
            var reasonHtml = Array.isArray(detail.required_by_reasons) && detail.required_by_reasons.length
                ? '<div style="font-size:11px;color:#3a4a2a;background:#fff;border-radius:6px;padding:8px 10px;margin-bottom:8px">'+detail.required_by_reasons.join('<br>')+'</div>'
                : '';
            var providingEntries = CS2.associateList.filter(function(entry){
                return (entry.crop && entry.crop.mfp || []).indexOf(mfCode) >= 0;
            });
            var cropListHtml;
            if(providingEntries.length){
                cropListHtml = providingEntries.map(function(entry){
                    return p2_cropCard(entry, CS2.selectedAssoc, 'assoc');
                }).join('');
            } else if(Array.isArray(detail.producer_crops) && detail.producer_crops.length){
                cropListHtml = detail.producer_crops.map(function(crop){
                    return '<div style="background:var(--green-bg);border:1.5px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:6px">'+
                        '<div style="font-size:13px;font-weight:700;color:var(--text-dark);margin-bottom:2px">'+crop.crop_name+'</div>'+
                        '<div style="font-size:11px;color:#3a4a2a">Crop ID: '+crop.crop_id+'</div>'+
                        '</div>';
                }).join('');
            } else {
                cropListHtml = '<div style="font-size:11px;color:#8a9a7a;padding:8px 12px;background:#f9f9f9;border-radius:6px;margin-bottom:6px">No associate crops in current database provide this microfeature.</div>';
            }
            mfGroupsHtml +=
                '<div style="margin-bottom:16px">'+
                '<div style="font-size:12px;font-weight:700;color:#2a3a1a;background:#f0f7e8;border-left:3px solid var(--green-mid);border-radius:0 7px 7px 0;padding:7px 12px;margin-bottom:8px;display:flex;align-items:center;gap:8px">'+
                '<span style="background:var(--green-mid);color:white;font-size:10px;padding:1px 7px;border-radius:8px">Missing MF</span>'+
                (detail.mf_label || cs_mfl(mfCode))+'</div>'+
                reasonHtml+
                cropListHtml+
                '</div>';
        });
    } else if(missing.length){
        mfGroupsHtml = '<div style="font-size:12px;font-weight:700;color:#2a3a1a;margin-bottom:10px">Associate crops available for each missing microfeature:</div>';
        missing.forEach(function(mf){
            var providingCrops = P2_CROPS.filter(function(ac){
                return (ac.mfp||[]).indexOf(mf)>=0;
            });
            var cropListHtml;
            if(providingCrops.length){
                cropListHtml = providingCrops.map(function(ac){
                    var entry = CS2.associateList.find(function(e){return e.crop.id===ac.id;});
                    if(entry) return p2_cropCard(entry, CS2.selectedAssoc, "assoc");
                    // Simple card if not in associateList
                    var sel = CS2.selectedAssoc.indexOf(ac.id)>=0;
                    var tags=(ac.mfp||[]).slice(0,3).map(function(m){return'<span class="cs-t cs-t-p">'+cs_mfl(m)+'</span>';}).join("");
                    return'<div style="background:var(--green-bg);border:1.5px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:6px;display:flex;align-items:flex-start;gap:10px">'+
                        '<input type="checkbox" id="assoc_'+ac.id+'" '+(sel?"checked":"")+' style="margin-top:3px;width:16px;height:16px;flex-shrink:0" onchange="p2_toggleSel(\'assoc\',\''+ac.id+'\',this.checked)">'+
                        '<div><div style="font-size:13px;font-weight:700;color:var(--text-dark);margin-bottom:2px">'+ac.name+'</div>'+
                        '<div style="font-size:11px;color:#3a4a2a;margin-bottom:4px">'+ac.type+' · '+ac.family+'</div>'+
                        '<div>'+tags+'</div></div></div>';
                }).join("");
            } else {
                cropListHtml = '<div style="font-size:11px;color:#8a9a7a;padding:8px 12px;background:#f9f9f9;border-radius:6px;margin-bottom:6px">No associate crops in current database provide this microfeature.</div>';
            }
            mfGroupsHtml +=
                '<div style="margin-bottom:16px">'+
                '<div style="font-size:12px;font-weight:700;color:#2a3a1a;background:#f0f7e8;border-left:3px solid var(--green-mid);border-radius:0 7px 7px 0;padding:7px 12px;margin-bottom:8px;display:flex;align-items:center;gap:8px">'+
                '<span style="background:var(--green-mid);color:white;font-size:10px;padding:1px 7px;border-radius:8px">Missing MF</span>'+
                cs_mfl(mf)+'</div>'+
                cropListHtml+
                '</div>';
        });
    } else {
        mfGroupsHtml = '<div class="cs-empty">No missing MFs — main crops cover all their own requirements.</div>';
    }

    return p2_hd(1,"Missing MF analysis",
        "Computing Missing MF = Required MF (main crops) − Available MF (main crops). If not empty, associate crops that produce each missing MF are listed below, grouped by microfeature.")+
        '<div class="cs-fcrd" style="margin-bottom:10px">'+
        '<div class="cs-fcht">Main crop MF summary</div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">MFs produced by main crops</span><span style="display:flex;flex-wrap:wrap;gap:3px;justify-content:flex-end">'+availHtml+'</span></div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">MFs required by main crops</span><span style="display:flex;flex-wrap:wrap;gap:3px;justify-content:flex-end">'+reqHtml+'</span></div>'+
        '<div class="cs-fcr"><span class="cs-fcrl" style="color:var(--csr600);font-weight:700">Missing MF (Required − Available)</span><span style="display:flex;flex-wrap:wrap;gap:3px;justify-content:flex-end">'+missingHtml+'</span></div>'+
        '</div>'+
        mfGroupsHtml+
        '<div class="cs-sf"><span class="cs-fn">'+missing.length+' missing MF(s) found. Select crops above to include in your system.</span>'+
        '<button class="cs-btn pri" onclick="p2_next()">MF cross-compatibility →</button></div>';
}

/* ── Step 2: MF Cross-compatibility ──────────────────────────── */
function p2_s2(){
    var step2Associated = CS2.step2Data && Array.isArray(CS2.step2Data.associated_crops)
        ? CS2.step2Data.associated_crops
        : null;
    var suggestions;
    if(step2Associated){
        var ids = step2Associated.map(function(item){ return item.crop_id; });
        suggestions = ids.map(function(id){
            return CS2.associateList.find(function(entry){ return entry.crop && entry.crop.id === id; });
        }).filter(Boolean);
    } else {
        suggestions = CS2.associateList.filter(function(e){
            return e.reasons.some(function(r){return r.indexOf("required by")>=0;});
        });
    }
    var html=suggestions.length?
        suggestions.map(function(e){return p2_cropCard(e,CS2.selectedAssoc,"assoc");}).join(""):
        '<div class="cs-empty">No additional cross-compatibility recommendations found — main crops already satisfy each other\'s MF requirements.</div>';
    return p2_hd(2,"MF cross-compatibility check",
        "Checking if any produced MFs of main crops can cater to required MFs of other crops in the feasible list. If not, associate crops are suggested to fill the gap with no other conflicts.")+
        html+
        '<div class="cs-sf"><span class="cs-fn">'+suggestions.length+' crop(s) suggested.</span>'+
        '<button class="cs-btn sec" onclick="p2_goto(1)">← Back</button>'+
        '<button class="cs-btn pri" onclick="p2_next()">Main crop Disease risk →</button></div>';
}

/* ── Step 3: Main crop Disease risk — diseases only ─────────── */
function p2_s3(){
    var mc=CS2.mainCrops;

    // Only show diseases (not pests)
    var diseaseRows=mc.map(function(c){
        var diseases=(c.pests||[]).filter(p2_isDisease);
        if(!diseases.length) return'';
        return'<tr><td style="font-weight:700;color:var(--text-dark)">'+c.name+'</td>'+
            '<td style="font-size:11px;color:#3a4a2a">'+diseases.join(", ")+'</td></tr>';
    }).filter(Boolean).join("");

    if(!diseaseRows) diseaseRows='<tr><td colspan="2" style="color:#aaa;font-style:italic;padding:10px;text-align:center">No disease records found for selected crops.</td></tr>';

    // Find associate crops that mitigate disease risks
    var suggestions=CS2.associateList.filter(function(e){
        return e.reasons.some(function(r){return r.indexOf("Reduces risk")>=0;});
    });

    // Also match by disease keywords in reasons
    var diseaseSuggestions=suggestions.filter(function(e){
        return e.reasons.some(function(r){
            return r.indexOf("Reduces risk")>=0 && Object.keys(P2_DISEASE_MF).some(function(dis){
                return p2_isDisease(dis) && r.toLowerCase().indexOf(dis.toLowerCase())>=0;
            });
        });
    });

    // If no disease-specific crops, show all with disease-fighting MFs (beneficial_insects, pest_repellent)
    if(!diseaseSuggestions.length){
        diseaseSuggestions = CS2.associateList.filter(function(e){
            return (e.crop.mfp||[]).some(function(mf){return mf==="beneficial_insects"||mf==="nematode_suppression";});
        });
    }

    var html=diseaseSuggestions.length?
        diseaseSuggestions.map(function(e){return p2_cropCard(e,CS2.selectedAssoc,"assoc");}).join(""):
        '<div class="cs-empty">No disease-specific associate crops found for current main crop selection.</div>';

    return p2_hd(3,"Main crop Disease risk",
        "Listing disease risks (fungal, bacterial, viral) for selected main crops. Associate crops that produce microfeatures which mitigate these disease risks are recommended below.")+
        '<div class="cs-fcrd" style="margin-bottom:10px">'+
        '<div class="cs-fcht">Main crop disease risks</div>'+
        '<table class="cs-dtbl"><thead><tr><th>Crop</th><th>Key diseases</th></tr></thead><tbody>'+diseaseRows+'</tbody></table>'+
        '</div>'+
        '<div style="font-size:12px;font-weight:700;color:#2a3a1a;margin-bottom:8px">Crops that mitigate these disease risks:</div>'+
        html+
        '<div class="cs-sf"><span class="cs-fn">'+diseaseSuggestions.length+' crop(s) suggested.</span>'+
        '<button class="cs-btn sec" onclick="p2_goto(2)">← Back</button>'+
        '<button class="cs-btn pri" onclick="p2_next()">Farm context features →</button></div>';
}

/* ── Step 4: Farm context features ───────────────────────────── */
function p2_s4(){
    var weakCFs=CS_CF_ORDER.filter(function(k){return CS_FARM.cf[k]&&CS_FARM.cf[k].s<=3;});
    var cfRows=weakCFs.map(function(k){
        var cf=CS_FARM.cf[k];
        var mfsHelp=Object.keys(P2_MF_CF).filter(function(mf){return P2_MF_CF[mf].indexOf(k)>=0;});
        return'<tr><td style="font-weight:700;color:var(--text-dark)">'+cf.l+'</td>'+
            '<td><span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:8px;background:#fff3cd;color:#7a4400">'+cf.slab+'</span></td>'+
            '<td style="font-size:11px;color:#3a4a2a">'+mfsHelp.map(cs_mfl).join(", ")+'</td></tr>';
    }).join("");
    var suggestions=CS2.associateList.filter(function(e){
        return e.reasons.some(function(r){return r.indexOf("Improves weak CF")>=0;});
    });
    var html=suggestions.length?
        suggestions.map(function(e){return p2_cropCard(e,CS2.selectedAssoc,"assoc");}).join(""):
        '<div class="cs-empty">No CF-specific associate crop recommendations for current farm profile.</div>';
    return p2_hd(4,"Farm context features",
        "Checking for vulnerable context features of the farm (poor/moderate values) and crops that produce MFs which improve these context features via the MF-CF interaction table.")+
        '<div class="cs-fcrd" style="margin-bottom:10px">'+
        '<div class="cs-fcht">Weak / moderate CFs that need support</div>'+
        '<table class="cs-dtbl"><thead><tr><th>Context Feature</th><th>Current Status</th><th>MFs that improve it</th></tr></thead><tbody>'+cfRows+'</tbody></table>'+
        '</div>'+
        html+
        '<div class="cs-sf"><span class="cs-fn">'+suggestions.length+' crop(s) suggested.</span>'+
        '<button class="cs-btn sec" onclick="p2_goto(3)">← Back</button>'+
        '<button class="cs-btn pri" onclick="p2_next()">Border crop (wind barrier) →</button></div>';
}

/* ── Step 5: Border crop (wind barrier) ──────────────────────── */
function p2_s5(){
    var wpCF=CS_FARM.cf.WP;
    var windWeak=wpCF&&wpCF.s<=3;
    var html=CS2.borderList.filter(function(e){
        return(e.crop.mfp||[]).indexOf("wind_break")>=0||e.reasons.some(function(r){return r.indexOf("wind")>=0;});
    });
    var cards=html.length?
        html.map(function(e){return p2_cropCard(e,CS2.selectedBorder,"border");}).join(""):
        '<div class="cs-empty">No wind-specific border crops needed — farm wind protection CF is adequate.</div>';
    return p2_hd(5,"Border crop (wind barrier)",
        "If the farm is at risk for high wind exposure (CF Wind Protection is weak/moderate), crops that produce wind break MF are recommended as border crops to act as wind barriers.")+
        '<div class="cs-vcrd '+(windWeak?"cs-vc-warn":"cs-vc-ok")+'" style="margin-bottom:10px">'+
        '<div class="cs-vci '+(windWeak?"cs-vci-warn":"cs-vci-ok")+'">'+(windWeak?"!":"✓")+'</div>'+
        '<div><div class="cs-vttl">Wind Protection CF: '+(wpCF?wpCF.slab:"N/A")+'</div>'+
        '<div class="cs-vmsg">'+(windWeak?"Farm wind protection is "+wpCF.slab+" — border wind barrier crops are recommended.":"Farm wind protection is adequate — no urgent border wind barrier needed.")+'</div>'+
        '</div></div>'+
        cards+
        '<div class="cs-sf"><span class="cs-fn">'+html.length+' border crop(s) suggested for wind barrier.</span>'+
        '<button class="cs-btn sec" onclick="p2_goto(4)">← Back</button>'+
        '<button class="cs-btn pri" onclick="p2_next()">Border crop (Pest barrier Pollination promoter) →</button></div>';
}

/* ── Step 6: Border crop (Pest barrier Pollination promoter) ─── */
function p2_s6(){
    var ppCF=CS_FARM.cf.PP, paCF=CS_FARM.cf.PA;
    var pestBorder=CS2.borderList.filter(function(e){
        return(e.crop.mfp||[]).indexOf("pest_repellent")>=0||(e.crop.mfp||[]).indexOf("beneficial_insects")>=0;
    });
    var polBorder=CS2.borderList.filter(function(e){
        return(e.crop.mfp||[]).indexOf("pollinator_habitat")>=0;
    });
    var cards=(pestBorder.concat(polBorder.filter(function(e){
        return!pestBorder.find(function(p){return p.crop.id===e.crop.id;});
    }))).map(function(e){return p2_cropCard(e,CS2.selectedBorder,"border");}).join("");
    return p2_hd(6,"Border crop (Pest barrier Pollination promoter)",
        "Based on the farm's general pest vulnerability (Pest Pressure CF) and region, crops that act as pest barriers and promote pollination are recommended as border crops.")+
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">'+
        '<div class="cs-fcrd"><div class="cs-fcht">Pest Pressure CF</div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">Status</span><span style="font-weight:700;color:'+(ppCF&&ppCF.s<=2?"var(--csr600)":"var(--csa600)")+'">'+( ppCF?ppCF.slab:"N/A")+'</span></div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">Value</span><span class="cs-fcrv">'+(ppCF?ppCF.val:"N/A")+'</span></div>'+
        '</div>'+
        '<div class="cs-fcrd"><div class="cs-fcht">Pollinator Activity CF</div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">Status</span><span style="font-weight:700;color:var(--csa600)">'+(paCF?paCF.slab:"N/A")+'</span></div>'+
        '<div class="cs-fcr"><span class="cs-fcrl">Value</span><span class="cs-fcrv">'+(paCF?paCF.val:"N/A")+'</span></div>'+
        '</div></div>'+
        (cards||'<div class="cs-empty">No pest barrier / pollinator border crops found.</div>')+
        '<div class="cs-sf"><span class="cs-fn">Select border crops to include in your system.</span>'+
        '<button class="cs-btn sec" onclick="p2_goto(5)">← Back</button>'+
        '<button class="cs-btn pri" onclick="p2_next()">Trap crops →</button></div>';
}

/* ── Step 7: Trap Crops ──────────────────────────────────────── */
function p2_s7(){
    var html=CS2.trapList.length?
        CS2.trapList.map(function(e){return p2_cropCard(e,CS2.selectedTrap,"trap");}).join(""):
        '<div class="cs-empty">No trap crops identified for the current main crop pest profile.</div>';
    return p2_hd(7,"Trap crops",
        "Trap crops lure the key pests of main crops away from the main field. They are planted in border rows or small patches and destroyed (with pests) before pests disperse.")+
        html+
        '<div class="cs-sf"><span class="cs-fn">'+CS2.trapList.length+' trap crop(s) identified.</span>'+
        '<button class="cs-btn sec" onclick="p2_goto(6)">← Back</button>'+
        '<button class="cs-btn pri" onclick="p2_next()">Review & confirm →</button></div>';
}

/* ── Step 8: Final Selection ─────────────────────────────────── */
function p2_s8(){
    function selList(ids, pool, label, badgeColor){
        var items=pool.filter(function(e){return ids.indexOf(e.crop.id)>=0;});
        if(!items.length) return'<div style="font-size:12px;color:#8a9a7a;padding:6px 0">None selected</div>';
        return items.map(function(e){
            return'<div style="display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--green-pale)">'+
                '<span style="font-size:11px;font-weight:700;padding:2px 9px;border-radius:8px;background:'+badgeColor+';color:white">'+label+'</span>'+
                '<span style="font-size:13px;font-weight:700;color:var(--text-dark)">'+e.crop.name+'</span>'+
                '<span style="font-size:11px;color:#3a4a2a;flex:1">'+e.reasons[0]+'</span>'+
            '</div>';
        }).join("");
    }
    var total=CS2.selectedAssoc.length+CS2.selectedBorder.length+CS2.selectedTrap.length;
    return p2_hd(8,"Review & confirm — associate crop selection",
        "Your complete associate crop system below. Review the selected crops across all three categories, then confirm to proceed to Phase 3.")+
        '<div class="cs-fcrd" style="margin-bottom:10px">'+
        '<div class="cs-fcht">Associate crops ('+CS2.selectedAssoc.length+' selected)</div>'+
        selList(CS2.selectedAssoc,CS2.associateList,"ASSOCIATE","var(--csg600)")+
        '</div>'+
        '<div class="cs-fcrd" style="margin-bottom:10px">'+
        '<div class="cs-fcht">Border crops ('+CS2.selectedBorder.length+' selected)</div>'+
        selList(CS2.selectedBorder,CS2.borderList,"BORDER","var(--csa600)")+
        '</div>'+
        '<div class="cs-fcrd" style="margin-bottom:10px">'+
        '<div class="cs-fcht">Trap crops ('+CS2.selectedTrap.length+' selected)</div>'+
        selList(CS2.selectedTrap,CS2.trapList,"TRAP","var(--csr600)")+
        '</div>'+
        '<div class="cs-vcrd cs-vc-ok"><div class="cs-vci cs-vci-ok">✓</div>'+
        '<div><div class="cs-vttl">'+total+' associate crops confirmed</div>'+
        '<div class="cs-vmsg">Your associate crop system is ready. Proceed to Phase 3 to check biodiversity and functional group coverage.</div>'+
        '</div></div>'+
        '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px">'+
        '<button class="cs-btn sec" onclick="p2_goto(1)">← Revisit selections</button>'+
        '<button class="cs-btn pri" onclick="cs_switchPhase(3)">Proceed to Phase 3 →</button>'+
        '</div>';
}