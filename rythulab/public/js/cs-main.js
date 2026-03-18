/* ═══ RythuLab Crop Selection — Main Orchestrator ═════════════ */
var CS_ACTIVE_PHASE = 1;

function initCropSelection(){
    CS_ACTIVE_PHASE = 1;
    CS.step = 1;
    cs_phase1_init();
}

function cs_switchPhase(n){
    CS_ACTIVE_PHASE = n;
    if(n===1) cs_phase1_init();
    else if(n===2) cs_phase2_init();
    else if(n===3) cs_phase3_init();
    else if(n===4) cs_phase4_init();
}
