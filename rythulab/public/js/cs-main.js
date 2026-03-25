/* ═══ RythuLab Crop Selection — Main Orchestrator ═════════════ */
var CS_ACTIVE_PHASE = 1;

function initCropSelection(){
    CS_ACTIVE_PHASE = 1;
    CS.step = 1;
    cs_phase1_init();
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
