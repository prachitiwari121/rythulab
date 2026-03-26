/* ═══ Phase 3: Biodiversity Crop Selection ════════════════════ */

var P3_CROPS = [];

var P3_GROUPS = ["Legume","Grass","Broad-leaf","Root/Tuber","Cover crop"];
var P3_MF_BIODIVERSITY = ["pollinator_habitat","beneficial_insects","p_cycling","ground_cover","nitrogen_fixation","biomass_mulch","deep_root_aeration","erosion_control","water_retention"];

var CS3 = {
    step: 1,
    selected: [],
    gaps: {},
    recommendations: [],
    step2BackendRecs: [],
    step1Step2Data: null,
    p3s12Loading: false,
    step3Data: null,
    p3s3Loading: false,
    step4Data: null,
    p3s4Loading: false
};

/* ── Entry point ─────────────────────────────────────────────── */
function cs_phase3_init(){
    var root=document.getElementById("cs-root"); if(!root) return;
    p3_computeGaps();
    root.innerHTML="";
    root.appendChild(_p3_phaseTabs());
    var lay=document.createElement("div"); lay.className="cs-lay";
    lay.innerHTML='<div class="cs-sbar" id="cs-sbar"></div><div class="cs-sc" id="cs-content"></div>';
    root.appendChild(lay);
    p3_renderSidebar(); p3_renderStep(CS3.step);
    cs_fetchPhase3Step1Step2();
}

function p3_collectAllSelectedCrops(){
    var combined = [];
    var seen = {};

    function addCrop(crop){
        if(!crop) return;
        var cropId = (crop.cropid || crop.id || "").toString().trim();
        if(!cropId || seen[cropId]) return;
        seen[cropId] = true;
        combined.push({
            id: crop.id || cropId,
            cropid: cropId,
            name: crop.name || crop.crop_name || cropId
        });
    }

    if(typeof cs_full === "function"){
        (cs_full() || []).forEach(addCrop);
    }

    if(typeof CS2 !== "undefined"){
        (CS2.selectedAssoc || []).forEach(function(id){
            var entry = (CS2.associateList || []).find(function(item){ return item.crop && item.crop.id === id; });
            addCrop(entry && entry.crop);
        });
        (CS2.selectedBorder || []).forEach(function(id){
            var entry = (CS2.borderList || []).find(function(item){ return item.crop && item.crop.id === id; });
            addCrop(entry && entry.crop);
        });
        (CS2.selectedTrap || []).forEach(function(id){
            var entry = (CS2.trapList || []).find(function(item){ return item.crop && item.crop.id === id; });
            addCrop(entry && entry.crop);
        });
    }

    (CS3.selected || []).forEach(function(id){
        var entry = (CS3.recommendations || []).find(function(item){ return item.crop && item.crop.id === id; });
        addCrop(entry && entry.crop);
    });

    return combined;
}

function p3_upsertRecommendations(entries){
    (entries || []).forEach(function(entry){
        if(!entry || !entry.crop || !entry.crop.id) return;

        var existing = CS3.recommendations.find(function(item){
            return item.crop && item.crop.id === entry.crop.id;
        });

        if(!existing){
            CS3.recommendations.push(entry);
            return;
        }

        existing.crop.name = existing.crop.name || entry.crop.name;
        existing.crop.family = existing.crop.family || entry.crop.family;
        existing.crop.group = existing.crop.group || entry.crop.group;
        existing.crop.h = existing.crop.h || entry.crop.h;
        existing.crop.rootD = existing.crop.rootD || entry.crop.rootD;
        existing.crop.desc = existing.crop.desc || entry.crop.desc;
        existing.crop.mfp = Array.from(new Set((existing.crop.mfp || []).concat(entry.crop.mfp || [])));
        existing.crop.cfImprove = Array.from(new Set((existing.crop.cfImprove || []).concat(entry.crop.cfImprove || [])));
        existing.crop.step1_score = existing.crop.step1_score || entry.crop.step1_score;
        (entry.reasons || []).forEach(function(reason){
            if(existing.reasons.indexOf(reason) < 0){
                existing.reasons.push(reason);
            }
        });
    });
}

function cs_fetchPhase3Step3(){
    if(CS3.p3s3Loading) return;
    CS3.p3s3Loading = true;

    fetch("/api/method/rythulab.api.get_phase3_mf_biodiversity_crops", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            selected_crops: p3_collectAllSelectedCrops(),
            mf_codes: ["MF18","MF19","MF20","MF24","MF29"]
        })
    })
    .then(function(r){ return r.json(); })
    .then(function(res){
        var msg = res && res.message ? res.message : {};
        if(!msg.ok) return;

        CS3.step3Data = msg;

        function isFunctionalGroupReason(reason){
            return (reason || "").indexOf("functional group") >= 0;
        }

        function isWeakCfReason(reason){
            return (reason || "").indexOf("weak CF") >= 0;
        }

        var preserved = (CS3.recommendations || []).map(function(entry){
            if(!entry || !entry.crop) return null;

            var baseReasons = Array.isArray(entry.reasons) ? entry.reasons : [];
            var keptReasons = baseReasons.filter(function(reason){
                return isFunctionalGroupReason(reason) || isWeakCfReason(reason);
            });
            var isSelected = Array.isArray(CS3.selected) && CS3.selected.indexOf(entry.crop.id) >= 0;

            if(!keptReasons.length && !isSelected) return null;

            return {
                crop: {
                    id: entry.crop.id,
                    name: entry.crop.name,
                    family: entry.crop.family,
                    group: entry.crop.group,
                    h: entry.crop.h,
                    rootD: entry.crop.rootD,
                    mfp: Array.isArray(entry.crop.mfp) ? entry.crop.mfp.slice() : [],
                    cfImprove: Array.isArray(entry.crop.cfImprove) ? entry.crop.cfImprove.slice() : [],
                    desc: entry.crop.desc,
                    step1_score: entry.crop.step1_score
                },
                reasons: keptReasons.length ? keptReasons : baseReasons.slice()
            };
        }).filter(Boolean);

        CS3.recommendations = preserved;
        p3_upsertRecommendations(Array.isArray(msg.recommendations) ? msg.recommendations : []);

        if(CS3.step === 3) p3_renderStep(3);
    })
    .catch(function(err){
        console.warn("Phase 3 Step 3 backend fetch failed:", err);
    })
    .finally(function(){
        CS3.p3s3Loading = false;
    });
}

function cs_fetchPhase3Step4(){
    if(CS3.p3s4Loading) return;
    CS3.p3s4Loading = true;

    var farmCfs = {};
    (CS_CF_ORDER || []).forEach(function(k, index){
        var cf = CS_FARM && CS_FARM.cf ? CS_FARM.cf[k] : null;
        if(!cf || !cf.slab) return;
        var cfCode = "CF" + String(index + 1);
        farmCfs[cfCode] = cf.slab;
    });

    fetch("/api/method/rythulab.api.get_phase3_cf_improvement_crops", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            selected_crops: p3_collectAllSelectedCrops(),
            farm_cfs: farmCfs
        })
    })
    .then(function(r){ return r.json(); })
    .then(function(res){
        var msg = res && res.message ? res.message : {};
        if(!msg.ok) return;

        CS3.step4Data = msg;

        function isFunctionalGroupReason(reason){
            return (reason || "").toLowerCase().indexOf("functional group") >= 0;
        }

        function isBiodiversityReason(reason){
            var text = (reason || "").toLowerCase();
            return text.indexOf("biodiversity") >= 0 ||
                text.indexOf("pollinator") >= 0 ||
                text.indexOf("phosphorus") >= 0 ||
                text.indexOf("leaf litter") >= 0;
        }

        function isWeakCfReason(reason){
            return (reason || "").toLowerCase().indexOf("weak cf") >= 0;
        }

        var preserved = (CS3.recommendations || []).map(function(entry){
            if(!entry || !entry.crop) return null;

            var baseReasons = Array.isArray(entry.reasons) ? entry.reasons : [];
            var keptReasons = baseReasons.filter(function(reason){
                return !isWeakCfReason(reason) && (isFunctionalGroupReason(reason) || isBiodiversityReason(reason));
            });
            var isSelected = Array.isArray(CS3.selected) && CS3.selected.indexOf(entry.crop.id) >= 0;

            if(!keptReasons.length && !isSelected) return null;

            return {
                crop: {
                    id: entry.crop.id,
                    name: entry.crop.name,
                    family: entry.crop.family,
                    group: entry.crop.group,
                    h: entry.crop.h,
                    rootD: entry.crop.rootD,
                    mfp: Array.isArray(entry.crop.mfp) ? entry.crop.mfp.slice() : [],
                    cfImprove: Array.isArray(entry.crop.cfImprove) ? entry.crop.cfImprove.slice() : [],
                    desc: entry.crop.desc,
                    step1_score: entry.crop.step1_score
                },
                reasons: keptReasons.length ? keptReasons : baseReasons.slice()
            };
        }).filter(Boolean);

        CS3.recommendations = preserved;
        p3_upsertRecommendations(Array.isArray(msg.recommendations) ? msg.recommendations : []);

        if(CS3.step === 4) p3_renderStep(4);
    })
    .catch(function(err){
        console.warn("Phase 3 Step 4 backend fetch failed:", err);
    })
    .finally(function(){
        CS3.p3s4Loading = false;
    });
}

function cs_fetchPhase3Step1Step2(){
    if(CS3.p3s12Loading) return;
    CS3.p3s12Loading = true;

    var selected = p3_collectAllSelectedCrops();

    fetch("/api/method/rythulab.api.get_phase3_biodiversity_gap_analysis", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ selected_crops: selected })
    })
    .then(function(r){ return r.json(); })
    .then(function(res){
        var msg = res && res.message ? res.message : {};
        if(!msg.ok) return;

        CS3.step1Step2Data = msg;

        var apiGaps = msg.gaps || {};
        CS3.gaps = {
            missingGroups: Array.isArray(apiGaps.missingGroups) ? apiGaps.missingGroups : (CS3.gaps.missingGroups || []),
            families: apiGaps.families && typeof apiGaps.families === "object" ? apiGaps.families : (CS3.gaps.families || {}),
            missingLayers: Array.isArray(apiGaps.missingLayers) ? apiGaps.missingLayers : (CS3.gaps.missingLayers || []),
            missingRoots: Array.isArray(apiGaps.missingRoots) ? apiGaps.missingRoots : (CS3.gaps.missingRoots || []),
            coveredGroups: apiGaps.coveredGroups && typeof apiGaps.coveredGroups === "object" ? apiGaps.coveredGroups : (CS3.gaps.coveredGroups || {}),
            allGroups: Array.isArray(apiGaps.allGroups) ? apiGaps.allGroups : (CS3.gaps.allGroups || P3_GROUPS.slice()),
            allLayers: Array.isArray(apiGaps.allLayers) ? apiGaps.allLayers : (CS3.gaps.allLayers || ["Low","Mid","Tall"]),
            allRoots: Array.isArray(apiGaps.allRoots) ? apiGaps.allRoots : (CS3.gaps.allRoots || ["Shallow","Medium","Deep"])
        };

        var backendRecs = Array.isArray(msg.recommended_crops) ? msg.recommended_crops : [];
        CS3.step2BackendRecs = backendRecs.map(function(rec){
            return {
                crop: {
                    id: rec.crop_id,
                    name: rec.crop_name,
                    family: rec.family || "",
                    group: rec.functional_group || "",
                    h: rec.canopy_layer_class || "",
                    rootD: rec.root_depth_class || "",
                    mfp: [],
                    cfImprove: [],
                    desc: "",
                    step1_score: rec.step1_score
                },
                reasons: Array.isArray(rec.reasons) ? rec.reasons.slice() : []
            };
        });

        (CS3.step2BackendRecs || []).forEach(function(entry){
            var existing = CS3.recommendations.find(function(item){
                return item.crop && entry.crop && item.crop.id === entry.crop.id;
            });

            if(!existing){
                CS3.recommendations.push(entry);
                return;
            }

            existing.crop.name = existing.crop.name || entry.crop.name;
            existing.crop.family = existing.crop.family || entry.crop.family;
            existing.crop.group = existing.crop.group || entry.crop.group;
            existing.crop.h = existing.crop.h || entry.crop.h;
            existing.crop.rootD = existing.crop.rootD || entry.crop.rootD;
            existing.crop.mfp = Array.from(new Set((existing.crop.mfp || []).concat(entry.crop.mfp || [])));
            (entry.reasons || []).forEach(function(reason){
                if(existing.reasons.indexOf(reason) < 0){
                    existing.reasons.push(reason);
                }
            });
        });

        if(CS3.step === 1 || CS3.step === 2) p3_renderStep(CS3.step);
    })
    .catch(function(err){
        console.warn("Phase 3 Step 1/2 backend fetch failed:", err);
    })
    .finally(function(){
        CS3.p3s12Loading = false;
    });
}

/* ── Compute gaps ────────────────────────────────────────────── */
function p3_computeGaps(){
    var mc = cs_full ? cs_full() : [];
    var assocCrops = CS2.selectedAssoc.concat(CS2.selectedBorder).concat(CS2.selectedTrap).map(function(id){
        var e=CS2.associateList.concat(CS2.borderList).concat(CS2.trapList).find(function(x){return x.crop.id===id;});
        return e?e.crop:null;
    }).filter(Boolean);
    var allCrops = mc.concat(assocCrops);

    var coveredGroups={};
    allCrops.forEach(function(c){
        var g=c.type||c.group||"";
        var grp=g.indexOf("Cereal")>=0?"Grass":g.indexOf("Pulse")>=0||g.indexOf("Legume")>=0?"Legume":
                g.indexOf("Oilseed")>=0?"Broad-leaf":g.indexOf("Root")>=0?"Root/Tuber":"Broad-leaf";
        coveredGroups[grp]=true;
    });
    var missingGroups=P3_GROUPS.filter(function(g){return!coveredGroups[g];});

    var families={};
    allCrops.forEach(function(c){if(c.family)families[c.family]=true;});

    var layers={Low:false,Mid:false,Tall:false};
    allCrops.forEach(function(c){
        var h=parseFloat(c.h||0);
        if(h<0.6)layers.Low=true; else if(h<1.8)layers.Mid=true; else layers.Tall=true;
    });
    var missingLayers=Object.keys(layers).filter(function(l){return!layers[l];});

    var roots={Shallow:false,Medium:false,Deep:false};
    allCrops.forEach(function(c){if(c.rd||c.rootD){var r=c.rd||c.rootD;if(r.indexOf("Shallow")>=0)roots.Shallow=true;else if(r.indexOf("Deep")>=0)roots.Deep=true;else roots.Medium=true;}});
    var missingRoots=Object.keys(roots).filter(function(r){return!roots[r];});

    CS3.gaps={
        missingGroups:missingGroups,
        families:families,
        missingLayers:missingLayers,
        missingRoots:missingRoots,
        coveredGroups:coveredGroups,
        allGroups:P3_GROUPS.slice(),
        allLayers:["Low","Mid","Tall"],
        allRoots:["Shallow","Medium","Deep"]
    };

    var recs=[];
    P3_CROPS.forEach(function(bc){
        var reasons=[];
        CS3.gaps.missingGroups.forEach(function(g){
            if(bc.group===g) reasons.push('Fills missing functional group: '+g);
        });
        CS3.gaps.missingLayers.forEach(function(l){
            var h=parseFloat(bc.h||0);
            var bcLayer=h<0.6?"Low":h<1.8?"Mid":"Tall";
            if(bcLayer===l) reasons.push('Fills missing canopy layer: '+l+' ('+h+'m)');
        });
        CS3.gaps.missingRoots.forEach(function(rd){
            var r=bc.rootD||"";
            if(r.indexOf(rd)>=0) reasons.push('Fills missing root depth: '+rd);
        });
        P3_MF_BIODIVERSITY.forEach(function(mf){
            if((bc.mfp||[]).indexOf(mf)>=0){
                var ml=mf==="pollinator_habitat"?"Pollinator support":
                        mf==="beneficial_insects"?"Beneficial insect habitat":
                        mf==="p_cycling"?"Phosphorus cycling":
                        mf==="ground_cover"?"Ground cover / leaf litter":
                        cs_mfl(mf);
                var r='Produces MF "'+ml+'" — supports system biodiversity';
                if(reasons.indexOf(r)<0) reasons.push(r);
            }
        });
        (bc.cfImprove||[]).forEach(function(cfk){
            var cf=CS_FARM.cf[cfk]; if(!cf||cf.s>3) return;
            reasons.push('Improves weak CF "'+cf.l+'" ('+cf.slab+') via MF');
        });
        if(reasons.length>0) recs.push({crop:bc, reasons:reasons});
    });
    CS3.recommendations=recs;
    // Start with empty selection — user picks manually
    CS3.selected=[];
}

/* ── Phase tabs ──────────────────────────────────────────────── */
function _p3_phaseTabs(){
    var phases=[
        {n:1,l:"Main crop selection",a:false},
        {n:2,l:"Associate crops",a:false},
        {n:3,l:"Biodiversity crops",a:true},
        {n:4,l:"System evaluation",a:false}
    ];
    var d=document.createElement("div"); d.className="cs-ptabs";
    d.innerHTML=phases.map(function(p){
        return'<button class="cs-ptab '+(p.a?"active":"")+(p.n===4?" off":"")+'" onclick="'+(p.n<4?"cs_switchPhase("+p.n+")":"")+'">'+
            '<span class="cs-pnum">'+p.n+'</span>Phase '+p.n+': '+p.l+'</button>';
    }).join("");
    return d;
}

/* ── Sidebar & routing ───────────────────────────────────────── */
var CS3_STEPS=[
    {n:1,name:"Biodiversity gap analysis"},
    {n:2,name:"Functional group coverage"},
    {n:3,name:"MF biodiversity crops"},
    {n:4,name:"CF improvement crops"},
    {n:5,name:"Select & confirm"}
];

function p3_renderSidebar(){
    var sb=document.getElementById("cs-sbar"); if(!sb)return;
    var h='<div class="cs-sbar-hd">Phase 3 — steps</div>';
    CS3_STEPS.forEach(function(s){
        var done=s.n<CS3.step,cur=s.n===CS3.step;
        h+='<div class="cs-si '+(done?"done":cur?"cur":"")+'" '+(done?'onclick="p3_goto('+s.n+')"':'')+'>'+
           '<div class="cs-si-n">'+(done?"✓":s.n)+'</div>'+
           '<div class="cs-si-nm">'+s.name+'</div></div>';
    });
    // Selected crops box — below steps
    var selHtml=(typeof cs_selBoxSidebarHtml==="function")?cs_selBoxSidebarHtml():"";
    h+='<div style="margin-top:16px;padding-top:12px;border-top:2px solid var(--green-pale)">'+
       '<div style="font-size:9px;font-weight:700;color:var(--text-mid);text-transform:uppercase;letter-spacing:0.6px;margin-bottom:8px;padding:0 2px">✔ Selected Crops</div>'+
       '<div id="cs-selbox">'+selHtml+'</div>'+
       '</div>';
    sb.innerHTML=h;
}

function p3_renderStep(n){
    var el=document.getElementById("cs-content");if(!el)return;
    el.innerHTML=p3_buildStep(n);
    p3_renderSidebar();
    if(typeof cs_updateSelBox==="function") cs_updateSelBox();
}
function p3_goto(n){if(n<=CS3.step){CS3.step=n;p3_renderStep(n);}}
function p3_invalidateStepData(step){
    if(step===1 || step===2){
        CS3.step1Step2Data = null;
        CS3.step2BackendRecs = [];
        CS3.gaps = {};
        return;
    }
    if(step===3){
        CS3.step3Data = null;
        return;
    }
    if(step===4){
        CS3.step4Data = null;
    }
}
function p3_next(){
    var nextStep=CS3.step+1;
    p3_invalidateStepData(nextStep);
    CS3.step=nextStep;
    p3_renderStep(CS3.step);
}

function p3_hd(n,title,desc){
    return'<div class="cs-bdg"><span class="cs-bdg-n">Step '+n+'</span><span class="cs-bdg-t">Phase 3 — biodiversity crop selection</span></div>'+
        '<div class="cs-ttl">'+title+'</div>'+
        (desc?'<div class="cs-dsc">'+desc+'</div>':'')+
        '<hr class="cs-hr">';
}
function p3_buildStep(n){
    var fns=[p3_s1,p3_s2,p3_s3,p3_s4,p3_s5];
    return fns[n-1]?fns[n-1]():"";
}

/* ── Crop card for P3 ────────────────────────────────────────── */
function p3_sortByScoredesc(arr){
    return arr.slice().sort(function(a,b){
        var sa=a.crop&&a.crop.step1_score!=null?Number(a.crop.step1_score):-Infinity;
        var sb=b.crop&&b.crop.step1_score!=null?Number(b.crop.step1_score):-Infinity;
        return sb-sa;
    });
}
function p3_cropCard(entry){
    var bc=entry.crop, sel=CS3.selected.indexOf(bc.id)>=0;
    var tags=(bc.mfp||[]).slice(0,4).map(function(m){return'<span class="cs-t cs-t-p">'+cs_mfl(m)+'</span>';}).join("");
    var reasons=entry.reasons.map(function(r){return'<li style="margin-bottom:3px">'+r+'</li>';}).join("");
    var sc2=bc.step1_score!=null?Math.min(100,Math.max(0,Math.round(Number(bc.step1_score)*20))):null;
    var pc2=sc2!=null?(sc2>=85?'cs-p-hi':sc2<70?'cs-p-lo':'cs-p-md'):'';
    var fc2=sc2!=null?(sc2>=85?'cs-sf-hi':sc2<70?'cs-sf-lo':'cs-sf-md'):'';
    return'<div style="background:var(--green-bg);border:1.5px solid '+(sel?"var(--green-mid)":"var(--border)")+';border-radius:10px;padding:12px;margin-bottom:8px">'+
        '<div style="display:flex;align-items:flex-start;gap:10px">'+
        '<input type="checkbox" id="p3_'+bc.id+'" '+(sel?"checked":"")+
            ' style="margin-top:3px;width:16px;height:16px;flex-shrink:0"'+
            ' onchange="p3_toggleSel(\''+bc.id+'\',this.checked)">'+
        '<div style="flex:1">'+
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px">'+
        '<div style="font-size:13px;font-weight:700;color:var(--text-dark)">'+bc.name+'</div>'+
        (sc2!=null?'<span class="cs-pill '+pc2+'">'+sc2+'</span>':'')+
        '</div>'+
        '<div style="font-size:11px;color:#3a4a2a;margin-bottom:5px">'+bc.family+' · '+bc.group+' · Height: '+bc.h+' · Root: '+(bc.rootD||bc.rd||"N/A")+'</div>'+
        '<div style="font-size:11px;color:#3a4a2a;margin-bottom:5px">'+bc.desc+'</div>'+
        '<div style="margin-bottom:6px">'+tags+'</div>'+
        '<div style="background:white;border-radius:6px;padding:7px 10px">'+
        '<div style="font-size:10px;font-weight:700;color:#2a3a1a;text-transform:uppercase;letter-spacing:0.4px;margin-bottom:4px">Why recommended:</div>'+
        '<ul style="font-size:11px;color:#2a3a1a;padding-left:16px;margin:0">'+reasons+'</ul>'+
        '</div></div></div></div>';
}

function p3_toggleSel(id,checked){
    if(checked){if(CS3.selected.indexOf(id)<0)CS3.selected.push(id);}
    else{var i=CS3.selected.indexOf(id);if(i>=0)CS3.selected.splice(i,1);}
    // Update sidebar live
    if(typeof cs_updateSelBox==="function") cs_updateSelBox();
}

/* ── Step 1: Gap Analysis ────────────────────────────────────── */
function p3_s1(){
    var g=CS3.gaps;
    if((!g || !g.allGroups) && !CS3.p3s12Loading){
        cs_fetchPhase3Step1Step2();
    }

    if(CS3.p3s12Loading && (!g || !Array.isArray(g.allGroups) || !g.allGroups.length)){
        return p3_hd(1,"Biodiversity gap analysis",
            "Loading biodiversity coverage from backend...")+
            '<div class="cs-empty">Loading gap analysis for functional groups, families, canopy layers and root depth classes...</div>'+
            '<div class="cs-sf"><span class="cs-fn">Fetching current coverage.</span>'+
            '<button class="cs-btn pri" disabled>Functional group coverage →</button></div>';
    }

    var groupLabels = (g && Array.isArray(g.allGroups) && g.allGroups.length) ? g.allGroups : P3_GROUPS;
    var layerLabels = (g && Array.isArray(g.allLayers) && g.allLayers.length) ? g.allLayers : ["Low","Mid","Tall"];
    var rootLabels = (g && Array.isArray(g.allRoots) && g.allRoots.length) ? g.allRoots : ["Shallow","Medium","Deep"];
    var familyCoverage = (CS3.step1Step2Data && CS3.step1Step2Data.coverage && CS3.step1Step2Data.coverage.family) ? CS3.step1Step2Data.coverage.family : {};
    var familyAll = Array.isArray(familyCoverage.all_values) ? familyCoverage.all_values : Object.keys(g.families||{});
    var familyCoveredSet = {};
    (Array.isArray(familyCoverage.covered) ? familyCoverage.covered : Object.keys(g.families||{})).forEach(function(f){ familyCoveredSet[f]=true; });
    var familyMissing = Array.isArray(familyCoverage.not_covered)
        ? familyCoverage.not_covered
        : familyAll.filter(function(f){ return !familyCoveredSet[f]; });

    function statusBadge(ok){
        return ok?'<span style="background:var(--csg100);color:var(--csg800);font-size:11px;font-weight:700;padding:2px 9px;border-radius:8px">Covered ✓</span>':
                  '<span style="background:var(--csr50);color:var(--csr600);font-size:11px;font-weight:700;padding:2px 9px;border-radius:8px">Gap ✗</span>';
    }
    var groupRows=groupLabels.map(function(grp){
        var covered=!!g.coveredGroups[grp];
        return'<tr><td style="font-weight:700;color:var(--text-dark)">'+grp+'</td><td>'+statusBadge(covered)+'</td></tr>';
    }).join("");
    var layerRows=layerLabels.map(function(layerLabel){
        var covered=g.missingLayers.indexOf(layerLabel)<0;
        return'<tr><td style="color:var(--text-dark)">'+layerLabel+'</td><td>'+statusBadge(covered)+'</td></tr>';
    }).join("");
    var rootRows=rootLabels.map(function(rootLabel){
        var covered=g.missingRoots.indexOf(rootLabel)<0;
        return'<tr><td style="color:var(--text-dark)">'+rootLabel+'</td><td>'+statusBadge(covered)+'</td></tr>';
    }).join("");
    var familyRows=familyAll.map(function(familyLabel){
        var covered=!!familyCoveredSet[familyLabel];
        return'<tr><td style="color:var(--text-dark)">'+familyLabel+'</td><td>'+statusBadge(covered)+'</td></tr>';
    }).join("");
    var famCount=Object.keys(g.families||{}).length;
    var totalGaps=(g.missingGroups.length+g.missingLayers.length+g.missingRoots.length+familyMissing.length);
    return p3_hd(1,"Biodiversity gap analysis",
        "Evaluates crop diversity across functions, families, and growth layers and suggests suitable crops to enhance it.")+
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">'+
        '<div class="cs-fcrd"><div class="cs-fcht">Functional groups</div>'+
        '<table class="cs-dtbl"><thead><tr><th>Group</th><th>Status</th></tr></thead><tbody>'+groupRows+'</tbody></table>'+
        '<div style="font-size:11px;color:var(--csr600);margin-top:6px">Missing: '+(g.missingGroups.length?g.missingGroups.join(", "):"None ✓")+'</div></div>'+
        '<div class="cs-fcrd"><div class="cs-fcht">Family groups</div>'+
        '<table class="cs-dtbl"><thead><tr><th>Family</th><th>Status</th></tr></thead><tbody>'+familyRows+'</tbody></table>'+
        '<div style="font-size:11px;color:var(--csr600);margin-top:6px">Missing: '+(familyMissing.length?familyMissing.join(", "):"None ✓")+'</div>'+
        '<div style="font-size:11px;color:var(--csg600);margin-top:4px">Families covered: '+famCount+'</div></div>'+
        '<div class="cs-fcrd"><div class="cs-fcht">Canopy layers</div>'+
        '<table class="cs-dtbl"><thead><tr><th>Layer</th><th>Status</th></tr></thead><tbody>'+layerRows+'</tbody></table>'+
        '<div style="font-size:11px;color:var(--csr600);margin-top:6px">Missing: '+(g.missingLayers.length?g.missingLayers.join(", "):"None ✓")+'</div></div>'+
        '<div class="cs-fcrd"><div class="cs-fcht">Root depths</div>'+
        '<table class="cs-dtbl"><thead><tr><th>Depth</th><th>Status</th></tr></thead><tbody>'+rootRows+'</tbody></table>'+
        '<div style="font-size:11px;color:var(--csg600);margin-top:6px">Root-depth classes covered: '+(rootLabels.length-g.missingRoots.length)+'</div></div></div>'+
        '<div class="cs-sf"><span class="cs-fn">'+totalGaps+' gap(s) detected in biodiversity coverage.</span>'+
        '<button class="cs-btn pri" onclick="p3_next()">Functional group coverage →</button></div>';
}

/* ── Step 2: Functional Group Coverage ──────────────────────── */
function p3_s2(){
    if((!CS3.gaps || !CS3.gaps.allGroups) && !CS3.p3s12Loading){
        cs_fetchPhase3Step1Step2();
    }
    var g=CS3.gaps;
    var groupLabels = (g && Array.isArray(g.allGroups) && g.allGroups.length) ? g.allGroups : P3_GROUPS;

    if(CS3.p3s12Loading && (!g || !Array.isArray(g.allGroups) || !g.allGroups.length)){
        return p3_hd(2,"Functional group coverage",
            "Loading functional group labels and coverage from backend...")+
            '<div class="cs-empty">Loading backend recommendations...</div>'+
            '<div class="cs-sf"><span class="cs-fn">Fetching missing functional groups.</span>'+
            '<button class="cs-btn sec" onclick="p3_goto(1)">← Back</button>'+
            '<button class="cs-btn pri" disabled>MF biodiversity crops →</button></div>';
    }

    var recs=CS3.recommendations.filter(function(r){
        return r.reasons.some(function(x){return x.toLowerCase().indexOf("functional group")>=0;});
    });
    if(CS3.step2BackendRecs && CS3.step2BackendRecs.length){
        recs = CS3.step2BackendRecs.filter(function(r){
            return r.reasons.some(function(x){return x.toLowerCase().indexOf("functional group")>=0;});
        });
    }
    var html=recs.length?p3_sortByScoredesc(recs).map(p3_cropCard).join(""):
        '<div class="cs-empty">All functional groups are already covered by your current crop system. ✓</div>';
    return p3_hd(2,"Functional group coverage",
        "Ensuring at least one species is represented from each functional group.")+
        '<div style="font-size:11px;color:#3a4a2a;margin-bottom:8px">Functional groups in current metadata: '+groupLabels.join(", ")+'</div>'+
        (g.missingGroups.length?
            '<div class="cs-vcrd cs-vc-warn"><div class="cs-vci cs-vci-warn">!</div><div>'+
            '<div class="cs-vttl">Missing functional groups: '+g.missingGroups.join(", ")+'</div>'+
            '<div class="cs-vmsg">Select at least one crop from each missing group below to improve functional biodiversity.</div>'+
            '</div></div>':'<div class="cs-vcrd cs-vc-ok"><div class="cs-vci cs-vci-ok">✓</div><div><div class="cs-vttl">All functional groups covered</div></div></div>')+
        html+
        '<div class="cs-sf"><span class="cs-fn">'+recs.length+' crop(s) suggested.</span>'+
        '<button class="cs-btn sec" onclick="p3_goto(1)">← Back</button>'+
        '<button class="cs-btn pri" onclick="p3_next()">MF biodiversity crops →</button></div>';
}

/* ── Step 3: MF Biodiversity Crops ──────────────────────────── */
function p3_s3(){
    if(!CS3.step3Data && !CS3.p3s3Loading){
        cs_fetchPhase3Step3();
    }

    if(CS3.p3s3Loading && !CS3.step3Data){
        return p3_hd(3,"MF biodiversity crops",
            "Loading biodiversity MF-producing crops from backend...")+
            '<div class="cs-empty">Loading backend recommendations for MF18, MF19, MF20, MF24 and MF29...</div>'+
            '<div class="cs-sf"><span class="cs-fn">Fetching biodiversity MF recommendations.</span>'+
            '<button class="cs-btn sec" onclick="p3_goto(2)">← Back</button>'+
            '<button class="cs-btn pri" disabled>CF improvement crops →</button></div>';
    }

    var recs=CS3.recommendations.filter(function(r){
        return r.reasons.some(function(x){return x.indexOf("biodiversity")>=0||x.indexOf("Pollinator")>=0||x.indexOf("Phosphorus")>=0||x.indexOf("leaf litter")>=0;});
    });
    var mfCoverageData = (CS3.step3Data && Array.isArray(CS3.step3Data.mf_coverage))
        ? CS3.step3Data.mf_coverage : [];
    var mfCoverage = mfCoverageData.map(function(m){
        var label = m.mf_label || m.mf_code || "";
        var coveredBy = Array.isArray(m.covered_by) && m.covered_by.length
            ? " (by " + m.covered_by.join(", ") + ")" : "";
        return '<div class="cs-fcr"><span class="cs-fcrl">'+label+'</span>'+
            '<span style="font-size:11px;font-weight:700;color:'+(m.covered?"var(--csg600)":"var(--csr600)")+'">'+
            (m.covered?"Covered ✓"+coveredBy:"Not covered ✗")+
            '</span></div>';
    }).join("");
    var html=recs.length?p3_sortByScoredesc(recs).map(p3_cropCard).join(""):
        '<div class="cs-empty">All key biodiversity MFs are covered by current selection.</div>';
    return p3_hd(3,"MF biodiversity crops",
        "Suggests crops that improve ecological balance, beneficial insects, and soil life.")+
        '<div class="cs-fcrd" style="margin-bottom:10px"><div class="cs-fcht">Biodiversity MF coverage in current selection</div>'+mfCoverage+'</div>'+
        html+
        '<div class="cs-sf"><span class="cs-fn">'+recs.length+' crop(s) suggested.</span>'+
        '<button class="cs-btn sec" onclick="p3_goto(2)">← Back</button>'+
        '<button class="cs-btn pri" onclick="p3_next()">CF improvement crops →</button></div>';
}

/* ── Step 4: CF Improvement Crops ────────────────────────────── */
function p3_s4(){
    if(!CS3.step4Data && !CS3.p3s4Loading){
        cs_fetchPhase3Step4();
    }

    if(CS3.p3s4Loading && !CS3.step4Data){
        return p3_hd(4,"CF improvement crops",
            "Loading weak/very-weak context-feature support from backend...")+
            '<div class="cs-empty">Checking selected crops against weak context features and fetching gap-filling crops...</div>'+
            '<div class="cs-sf"><span class="cs-fn">Fetching CF support analysis.</span>'+
            '<button class="cs-btn sec" onclick="p3_goto(3)">← Back</button>'+
            '<button class="cs-btn pri" disabled>Review & confirm →</button></div>';
    }

    var recs=CS3.recommendations.filter(function(r){
        return r.reasons.some(function(x){return (x||"").toLowerCase().indexOf("weak cf")>=0;});
    });
    var cfAnalysis = (CS3.step4Data && Array.isArray(CS3.step4Data.cf_analysis)) ? CS3.step4Data.cf_analysis : [];
    var cfRows=cfAnalysis.map(function(item){
        var cf = item.cf || {};
        var helpingList = (item.selected_crops_helping || []).map(function(c){
            return c.crop_name || c.crop_id;
        });
        var helpingText = helpingList.length ? helpingList.join(", ") : "None selected yet";
        return'<tr><td style="font-weight:700;color:var(--text-dark)">'+(cf.cf_label || cf.cf_code || "")+'</td>'+
            '<td><span style="font-size:11px;padding:2px 8px;border-radius:8px;background:#fff3cd;color:#7a4400">'+(item.status || "")+'</span></td>'+
            '<td style="font-size:11px;color:'+(helpingList.length?"var(--csg600)":"var(--csr600)")+'">'+helpingText+'</td></tr>';
    }).join("");
    if(!cfRows){
        cfRows = '<tr><td colspan="3" style="font-size:11px;color:var(--text-mid)">No weak/very-weak context features detected.</td></tr>';
    }
    var html=recs.length?p3_sortByScoredesc(recs).map(p3_cropCard).join(""):
        '<div class="cs-empty">No additional CF-improvement crops found for current farm profile.</div>';
    return p3_hd(4,"CF improvement crops",
        "Suggests crops that help improve weak soil, water, or biological conditions on the farm.")+
        '<div class="cs-fcrd" style="margin-bottom:10px"><div class="cs-fcht">Weak / Very Weak CFs and which selected crops help them</div>'+
        '<table class="cs-dtbl"><thead><tr><th>Context Feature</th><th>Status</th><th>Helped by</th></tr></thead><tbody>'+cfRows+'</tbody></table></div>'+
        html+
        '<div class="cs-sf"><span class="cs-fn">'+recs.length+' crop(s) suggested.</span>'+
        '<button class="cs-btn sec" onclick="p3_goto(3)">← Back</button>'+
        '<button class="cs-btn pri" onclick="p3_next()">Review & confirm →</button></div>';
}

/* ── Step 5: Final Selection ─────────────────────────────────── */
function p3_s5(){
    var selRecs=CS3.recommendations.filter(function(r){return CS3.selected.indexOf(r.crop.id)>=0;});
    var rows=selRecs.map(function(r){
        var bc=r.crop;
        return'<tr><td style="font-weight:700;color:var(--text-dark)">'+bc.name+'</td>'+
            '<td style="color:#3a4a2a">'+bc.group+'</td>'+
            '<td>'+bc.family+'</td>'+
            '<td>'+bc.h+'</td>'+
            '<td>'+(bc.rootD||bc.rd||"—")+'</td>'+
            '<td style="font-size:10px">'+(bc.mfp||[]).map(cs_mfl).join(", ")+'</td></tr>';
    }).join("");
    return p3_hd(5,"Review & confirm — biodiversity crop selection",
        "Your selected biodiversity crops. Review and confirm, then proceed to Phase 4: System Evaluation.")+
        (selRecs.length?
            '<div style="overflow-x:auto;margin-bottom:12px"><table class="cs-dtbl"><thead><tr>'+
            '<th>Crop</th><th>Group</th><th>Family</th><th>Height</th><th>Root depth</th><th>Key MFs</th>'+
            '</tr></thead><tbody>'+rows+'</tbody></table></div>':
            '<div class="cs-empty" style="margin-bottom:12px">No biodiversity crops selected yet. Go back to select crops.</div>')+
        '<div class="cs-scards">'+
        '<div class="cs-sc2"><div class="cs-sc2-n sn-g">'+selRecs.length+'</div><div class="cs-sc2-l">biodiversity crops</div></div>'+
        '<div class="cs-sc2"><div class="cs-sc2-n '+(CS3.gaps.missingGroups.filter(function(g){return!selRecs.some(function(r){return r.crop.group===g;});}).length===0?"sn-g":"sn-r")+'">'+
        (CS3.gaps.missingGroups.filter(function(g){return!selRecs.some(function(r){return r.crop.group===g;});}).length===0?"All":"Some")+'</div>'+
        '<div class="cs-sc2-l">functional groups</div></div>'+
        '<div class="cs-sc2"><div class="cs-sc2-n sn-g">'+selRecs.reduce(function(t,r){return t+(r.crop.mfp||[]).length;},0)+'</div><div class="cs-sc2-l">total MFs added</div></div>'+
        '</div>'+
        '<div class="cs-vcrd cs-vc-ok" style="margin-bottom:12px"><div class="cs-vci cs-vci-ok">✓</div>'+
        '<div><div class="cs-vttl">Biodiversity crop selection complete</div>'+
        '<div class="cs-vmsg">Proceed to Phase 4 for system evaluation scores and layout transfer.</div>'+
        '</div></div>'+
        '<div style="display:flex;gap:8px;flex-wrap:wrap">'+
        '<button class="cs-btn sec" onclick="p3_goto(1)">← Revisit selections</button>'+
        '<button class="cs-btn pri" onclick="cs_switchPhase(4)">Proceed to Phase 4 →</button>'+
        '</div>';
}