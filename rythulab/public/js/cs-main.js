/* ═══ RythuLab Crop Selection — Main Orchestrator ═════════════ */
var CS_ACTIVE_PHASE = 1;

function initCropSelection(){
    CS_ACTIVE_PHASE = 1;
    CS.step = 1;
    cs_initFarmSelection();
}

function cs_resetWorkflowState(){
    if(typeof CS !== "undefined" && CS){
        CS.step = 1;
        CS.farmOpen = false;
        CS.sel = [];
        CS.wc = null;
        CS.an = null;
        CS.s5Data = null;
        CS.s5Loading = false;
        CS.phase1Loaded = false;
        CS.phase1Loading = false;
        CS.s6Loading = false;
        CS.s6Error = null;
        CS.s7Loading = false;
        CS.s7Error = null;
        CS.s8Loading = false;
        CS.s8Error = null;
        CS.s9Loading = false;
        CS.s9Error = null;
        CS.s10Loading = false;
        CS.s10Error = null;
    }

    if(typeof CS2 !== "undefined" && CS2){
        CS2.step = 1;
        CS2.mainCrops = [];
        CS2.missingMF = [];
        CS2.step1Data = null;
        CS2.step2Data = null;
        CS2.step3Data = null;
        CS2.step4Data = null;
        CS2.step5Data = null;
        CS2.step6Data = null;
        CS2.step7Data = null;
        CS2.associateList = [];
        CS2.borderList = [];
        CS2.trapList = [];
        CS2.selectedAssoc = [];
        CS2.selectedBorder = [];
        CS2.selectedTrap = [];
        CS2.p2s1Loading = false;
        CS2.p2s2Loading = false;
        CS2.p2s3Loading = false;
        CS2.p2s4Loading = false;
        CS2.p2s5Loading = false;
        CS2.p2s6Loading = false;
        CS2.p2s7Loading = false;
    }

    if(typeof CS3 !== "undefined" && CS3){
        CS3.step = 1;
        CS3.selected = [];
        CS3.gaps = {};
        CS3.recommendations = [];
        CS3.step2BackendRecs = [];
        CS3.step1Step2Data = null;
        CS3.p3s12Loading = false;
        CS3.step3Data = null;
        CS3.p3s3Loading = false;
        CS3.step4Data = null;
        CS3.p3s4Loading = false;
    }
}

function cs_renderFarmSelector(){
    var host = document.getElementById("cs-farm-picker");
    if(!host){
        var root = document.getElementById("cs-root");
        if(root && root.parentNode){
            host = document.createElement("div");
            host.id = "cs-farm-picker";
            host.style.marginBottom = "10px";
            root.parentNode.insertBefore(host, root);
        }
    }
    if(!host) return;

    if(!CS_FARM_OPTIONS || !CS_FARM_OPTIONS.length){
        host.innerHTML = '<span style="font-size:12px;color:#5a6a4a">Farm: Default</span>';
        return;
    }

    var selectedId = CS_FARM_ID || "";
    var optionsHtml = CS_FARM_OPTIONS.map(function(f){
        var id = f.id || "";
        var label = f.label || id;
        return '<option value="'+id+'" '+(id===selectedId?"selected":"")+'>'+label+'</option>';
    }).join("");

    host.innerHTML =
        '<label for="cs-farm-select" style="font-size:12px;font-weight:700;color:var(--green-dark);margin-right:8px;">Farm:</label>'+
        '<select id="cs-farm-select" onchange="cs_onFarmChange(this.value)" style="font-size:12px;padding:4px 8px;border:1px solid var(--border);border-radius:6px;min-width:300px;max-width:520px">'+
        '<option value="" '+(!selectedId?"selected":"")+' disabled>Select a farm</option>'+
        optionsHtml+
        '</select>';

        
}

function cs_renderAwaitingFarmSelection(){
    var root = document.getElementById("cs-root");
    if(!root) return;
    root.innerHTML =
        '<div style="padding:28px;text-align:center;background:white;border-radius:12px;border:1.5px solid var(--green-pale)">'+
            '<div style="font-size:16px;font-weight:700;color:var(--green-dark);margin-bottom:8px">Select a farm to begin</div>'+
            '<div style="font-size:13px;color:#3a4a2a">Choose one of the available farms from the dropdown above to load crop selection data.</div>'+
        '</div>';
}

function cs_fetchFarmOptions(){
    return fetch("/api/method/rythulab.api.get_crop_selection_farms", {
        method: "GET"
    })
    .then(function(r){ return r.json(); })
    .then(function(res){
        var msg = res && res.message ? res.message : {};
        CS_FARM_OPTIONS = Array.isArray(msg.farms) ? msg.farms : [];
        cs_renderFarmSelector();
    })
    .catch(function(err){
        console.warn("Failed to load farm options:", err);
        CS_FARM_OPTIONS = [];
        cs_renderFarmSelector();
    });
}

function cs_loadFarmProfile(farmId){
    return fetch("/api/method/rythulab.api.get_crop_selection_farm_profile", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({farm_id: farmId})
    })
    .then(function(r){ return r.json(); })
    .then(function(res){
        var msg = res && res.message ? res.message : {};
        if(msg && msg.ok && msg.farm){
            cs_applyFarmProfile(msg.farm);
            CS_FARM_ID = msg.farm.id || farmId;
        }
        cs_renderFarmSelector();
    });
}

function cs_initFarmSelection(){
    cs_fetchFarmOptions()
    .then(function(){
        cs_resetWorkflowState();
        CS_ACTIVE_PHASE = 1;

        if(!CS_FARM_OPTIONS || !CS_FARM_OPTIONS.length){
            cs_phase1_init();
            return;
        }

        CS_FARM_ID = null;
        cs_renderFarmSelector();
        cs_renderAwaitingFarmSelection();
    })
    .catch(function(){
        cs_resetWorkflowState();
        CS_ACTIVE_PHASE = 1;
        cs_phase1_init();
    });
}

function cs_onFarmChange(farmId){
    if(!farmId || farmId===CS_FARM_ID) return;

    cs_loadFarmProfile(farmId)
    .then(function(){
        cs_resetWorkflowState();
        CS_ACTIVE_PHASE = 1;
        cs_phase1_init();
    })
    .catch(function(err){
        console.warn("Failed to switch farm profile:", err);
        if(typeof showToast === "function") showToast("❌ Failed to load selected farm");
    });
}

function cs_switchPhase(n, forceReload){
    CS_ACTIVE_PHASE = n;
    if(n===1) cs_phase1_init();
    else if(n===2){
        if(forceReload && typeof CS2 !== "undefined" && CS2){
            CS2.step = 1;
            CS2.mainCrops = [];
            CS2.missingMF = [];
            CS2.step1Data = null;
            CS2.step2Data = null;
            CS2.step3Data = null;
            CS2.step4Data = null;
            CS2.step5Data = null;
            CS2.step6Data = null;
            CS2.step7Data = null;
            CS2.associateList = [];
            CS2.borderList = [];
            CS2.trapList = [];
            CS2.selectedAssoc = [];
            CS2.selectedBorder = [];
            CS2.selectedTrap = [];
            CS2.p2s1Loading = false;
            CS2.p2s2Loading = false;
            CS2.p2s3Loading = false;
            CS2.p2s4Loading = false;
            CS2.p2s5Loading = false;
            CS2.p2s6Loading = false;
            CS2.p2s7Loading = false;
        }
        cs_phase2_init();
    }
    else if(n===3){
        if(forceReload && typeof CS3 !== "undefined" && CS3){
            CS3.step = 1;
            CS3.selected = [];
            CS3.gaps = {};
            CS3.recommendations = [];
            CS3.step2BackendRecs = [];
            CS3.step1Step2Data = null;
            CS3.p3s12Loading = false;
            CS3.step3Data = null;
            CS3.p3s3Loading = false;
            CS3.step4Data = null;
            CS3.p3s4Loading = false;
        }
        cs_phase3_init();
    }
    else if(n===4) cs_phase4_init();
}
